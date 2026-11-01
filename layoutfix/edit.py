# -*- coding: utf-8 -*-
"""layoutfix.edit — 让 SVG 元素可寻址，并把「往左 1.2mm」落成文件里的真实改动。

三条铁律：

1. **只改被拖的那个元素，其余字节一个不动。** 用标签扫描器定位，绝不重新
   序列化整份 XML。读写一律走字节，不走 `read_text/write_text`——后者在
   Windows 上会把 `\\n` 写成 `\\r\\n`，一次拖动就把整份文件的换行全改掉，
   git diff 变成整文件重写，看起来像重写了整个图。

2. **身份用「文档序号」而不是注入 id。** 原始文件保持干净；服务端另出一份
   带 data-ffid 的副本给浏览器用，存盘时按「第 N 个 <text>」回到原文件定位。

3. **样式类属性写内联 style，几何类写呈现属性。** SVG 里 CSS 规则优先级高于
   呈现属性：图里只要有 <style> 用类定义了 font-size，元素上写 font-size="15"
   就会被压回去——文件改了、画面不动。

改动同时落到两处：
  - 图文件本身 —— 人拖完立刻看到效果
  - <图>.nudge.jsonl —— 追加一行，agent 下次重新生成时照着重放
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

MOVABLE = ("rect", "text", "polyline", "line", "path", "g",
           "circle", "ellipse", "image", "polygon")

# 这些属性必须写进内联 style，不能写呈现属性（CSS 会压过呈现属性）
STYLE_PROPS = {"font-size", "font-family", "font-weight", "font-style",
               "fill", "stroke", "stroke-width", "opacity", "text-anchor",
               "letter-spacing", "dominant-baseline"}

# 这几个在 CSS 里不能裸写数值，必须带单位
NEEDS_PX = {"font-size", "letter-spacing"}

QUOTES = "\"'"


# --------------------------------------------------------------------------
# 字节级读写：绝不让 Python 帮忙改换行
# --------------------------------------------------------------------------
def read_raw(fig: Path) -> str:
    return fig.read_bytes().decode("utf-8")


def write_raw(fig: Path, text: str) -> None:
    fig.write_bytes(text.encode("utf-8"))


# --------------------------------------------------------------------------
# 标签扫描（比正则可靠：属性值里可能含 '>'）
# --------------------------------------------------------------------------
def iter_tags(raw: str):
    i, n = 0, len(raw)
    while True:
        i = raw.find("<", i)
        if i < 0:
            return
        if raw.startswith("<!--", i):
            j = raw.find("-->", i)
            i = j + 3 if j >= 0 else n
            continue
        if raw.startswith("<![CDATA[", i):
            j = raw.find("]]>", i)
            i = j + 3 if j >= 0 else n
            continue
        if raw.startswith("<?", i) or raw.startswith("<!", i):
            j = raw.find(">", i)
            i = j + 1 if j >= 0 else n
            continue
        j, quote = i + 1, None
        while j < n:
            c = raw[j]
            if quote:
                if c == quote:
                    quote = None
            elif c in QUOTES:
                quote = c
            elif c == ">":
                break
            j += 1
        text = raw[i:j + 1]
        m = re.match(r"<\s*(/?)\s*([\w:.-]+)", text)
        if m:
            # 去掉命名空间前缀：<svg:rect> 与 <rect> 必须算同一种元素，
            # 否则 annotate 分配的编号和 _locate 的计数会对不上，拖 A 改到 B。
            name = m.group(2).split(":")[-1]
            yield {"start": i, "end": j + 1, "closing": m.group(1) == "/",
                   "name": name, "text": text}
        i = j + 1


# --------------------------------------------------------------------------
# 属性读写
# --------------------------------------------------------------------------
def _attr_pattern(name: str):
    # (?<![\w:.-]) 是关键：\b 会让 "width" 命中 "stroke-width" 里的 "width"，
    # 于是「改宽度」变成「改描边粗细」——框没变宽、边框变粗，用户以为改好了。
    return re.compile(r"(?<![\w:.-])" + re.escape(name) + r"\s*=\s*([" + QUOTES
                      + r"])(.*?)\1", re.S)


def _attr(tag: str, name: str):
    m = _attr_pattern(name).search(tag)
    return m.group(2) if m else None


def _set_attr(tag: str, name: str, value: str) -> str:
    pat = _attr_pattern(name)
    m = pat.search(tag)
    if m:
        q = m.group(1)
        return tag[:m.start()] + f"{name}={q}{value}{q}" + tag[m.end():]
    m2 = re.search(r"\s*/?>$", tag)
    head, tail = tag[:m2.start()], tag[m2.start():]
    return f'{head} {name}="{value}"{tail}'


def _del_attr(tag: str, name: str) -> str:
    """删除属性，连同它前面的空白一起删。

    只删 name="..." 会留下孤立的空格（`transform="..."     >`），
    撤销后字节对不上原文。要求前面必须有空白也顺带挡住了
    stroke-width 里的 width——那里前面是 `-`，不是空白。
    """
    pat = re.compile(r"\s+" + re.escape(name) + r"\s*=\s*([" + QUOTES + r"])(.*?)\1",
                     re.S)
    return pat.sub("", tag, count=1)


def _get_style(tag: str) -> dict:
    d = {}
    raw = _attr(tag, "style") or ""
    for part in raw.split(";"):
        if ":" in part:
            k, _, v = part.partition(":")
            if k.strip():
                d[k.strip()] = v.strip()
    return d


def _write_style(tag: str, d: dict) -> str:
    body = ";".join(f"{k}:{v}" for k, v in d.items() if v not in (None, ""))
    return _set_attr(tag, "style", body) if body else _del_attr(tag, "style")


def _fmt(v) -> str:
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError(f"数值非法: {v}")
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0", "-") else "0"


def _style_value(prop: str, value) -> str:
    if isinstance(value, (int, float)):
        return f"{_fmt(value)}px" if prop in NEEDS_PX else _fmt(value)
    v = str(value)
    if prop in NEEDS_PX and v and v[-1].isdigit():
        return v + "px"
    return v


# --------------------------------------------------------------------------
# 画布与背景板
# --------------------------------------------------------------------------
def canvas_box(raw: str) -> tuple[float, float, float, float]:
    """返回 (min_x, min_y, w, h)。没有 viewBox 时退回 width/height。"""
    m = re.search(r'viewBox\s*=\s*["\']([^"\']*)["\']', raw)
    if m:
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", m.group(1))]
        if len(nums) == 4 and nums[2] > 0 and nums[3] > 0:
            return nums[0], nums[1], nums[2], nums[3]
    m = re.search(r"<svg\b[^>]*>", raw)
    if m:
        try:
            w = float((_attr(m.group(0), "width") or "0").replace("px", ""))
            h = float((_attr(m.group(0), "height") or "0").replace("px", ""))
            if w > 0 and h > 0:
                return 0.0, 0.0, w, h
        except ValueError:
            pass
    return 0.0, 0.0, 0.0, 0.0


def canvas_area(raw: str) -> float:
    _, _, w, h = canvas_box(raw)
    return w * h


def _num(v) -> float:
    if v is None:
        return 0.0
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*(%|px|pt|mm|cm|in)?\s*$", str(v))
    return float(m.group(1)) if m else 0.0


def is_backdrop(tag: dict, box: tuple[float, float, float, float]) -> bool:
    """覆盖半张画布以上的矩形是背景板，不该被拖动。

    不排除的话，人在空白处一拖，整张图的底色就跟着跑——它压在最底层，
    拖走之后所有元素看起来都「错位」了，极难察觉是拖错了东西。
    """
    if tag["name"] not in ("rect", "image"):
        return False
    _, _, cw, ch = box
    if cw <= 0 or ch <= 0:
        return False
    w = _num(_attr(tag["text"], "width"))
    h = _num(_attr(tag["text"], "height"))
    if _attr(tag["text"], "width") and "%" in (_attr(tag["text"], "width") or ""):
        w = cw * w / 100.0
    if _attr(tag["text"], "height") and "%" in (_attr(tag["text"], "height") or ""):
        h = ch * _num(_attr(tag["text"], "height")) / 100.0
    return w > 0 and h > 0 and w * h >= 0.5 * cw * ch


# --------------------------------------------------------------------------
# 元素索引
# --------------------------------------------------------------------------
def annotate(raw: str) -> str:
    """给每个可拖元素加 data-ffid="tag:序号"，供浏览器选中。只用于下发的副本。

    背景板不跳过、只打 data-fflock 标记。**编号必须覆盖全部可拖元素**：
    _locate 是按「第 N 个 <rect>」回原文件定位的，只要这里少算一个，
    两边编号就整体错位，拖 A 会改到 B。
    """
    out, last, counters = [], 0, {}
    box = canvas_box(raw)
    for t in iter_tags(raw):
        if t["closing"] or t["name"] not in MOVABLE:
            continue
        n = counters.get(t["name"], 0)
        counters[t["name"]] = n + 1
        tag = _set_attr(t["text"], "data-ffid", f'{t["name"]}:{n}')
        if is_backdrop(t, box):
            tag = _set_attr(tag, "data-fflock", "1")
        out.append(raw[last:t["start"]])
        out.append(tag)
        last = t["end"]
    out.append(raw[last:])
    return "".join(out)


def inventory(raw: str) -> list[dict]:
    """列出所有可拖元素及其身份，供前端与 CLI 使用。"""
    counters, out = {}, []
    box = canvas_box(raw)
    for t in iter_tags(raw):
        if t["closing"] or t["name"] not in MOVABLE:
            continue
        n = counters.get(t["name"], 0)
        counters[t["name"]] = n + 1
        inner = re.sub(r"<[^>]*>", "", raw[t["end"]:t["end"] + 400])
        inner = inner.split("</text>")[0] if t["name"] == "text" else ""
        out.append({
            "eid": f'{t["name"]}:{n}', "tag": t["name"],
            "locked": is_backdrop(t, box),
            "x": _attr(t["text"], "x"), "y": _attr(t["text"], "y"),
            "hint": (re.sub(r"\s+", " ", inner).strip()[:24] if inner.strip()
                     else f'{_attr(t["text"], "x") or "?"},{_attr(t["text"], "y") or "?"}'),
        })
    return out


# --------------------------------------------------------------------------
# 位移与属性落地
# --------------------------------------------------------------------------
def _locate(raw: str, eid: str):
    tag_name, idx = eid.rsplit(":", 1)
    idx = int(idx)
    n = 0
    for t in iter_tags(raw):
        if t["closing"] or t["name"] != tag_name:
            continue
        if n == idx:
            return t
        n += 1
    raise KeyError(f"找不到元素 {eid}")


def _shift_tag(tag: str, dx: float, dy: float) -> str:
    has_tf = _attr(tag, "transform") is not None
    if not has_tf:
        for ax, ay in (("x", "y"), ("cx", "cy")):
            if _attr(tag, ax) is not None and _attr(tag, ay) is not None:
                try:
                    nx = float(_attr(tag, ax)) + dx
                    ny = float(_attr(tag, ay)) + dy
                except ValueError:
                    break
                tag = _set_attr(tag, ax, _fmt(nx))
                return _set_attr(tag, ay, _fmt(ny))

    # 没有坐标属性（polyline/path/g）或原本带 transform：累加 translate。
    # translate 必须放在**最前面**：transform 列表是右起生效的，
    # 写成 "rotate(...) translate(dx,dy)" 会让位移沿着旋转后的轴走——
    # 旋转过的标签往右拖会往上跑。
    t0 = _attr(tag, "data-fft0")
    if t0 is None:
        t0 = _attr(tag, "transform") or ""
        tag = _set_attr(tag, "data-fft0", t0)
    tx = _num(_attr(tag, "data-fftx")) + dx
    ty = _num(_attr(tag, "data-ffty")) + dy
    if abs(tx) < 1e-6 and abs(ty) < 1e-6:
        # 回到原位时把辅助属性一并清掉，撤销才能还原成原始字节
        tag = _del_attr(tag, "transform")
        tag = _del_attr(tag, "data-fftx")
        tag = _del_attr(tag, "data-ffty")
        tag = _del_attr(tag, "data-fft0")
        if t0:
            tag = _set_attr(tag, "transform", t0)
        return tag
    tag = _set_attr(tag, "data-fftx", _fmt(tx))
    tag = _set_attr(tag, "data-ffty", _fmt(ty))
    tag = _del_attr(tag, "transform")
    return _set_attr(tag, "transform", f"translate({_fmt(tx)},{_fmt(ty)}) {t0}".strip())


def apply_move(raw: str, eid: str, dx: float, dy: float) -> str:
    t = _locate(raw, eid)
    return raw[:t["start"]] + _shift_tag(t["text"], dx, dy) + raw[t["end"]:]


def apply_set(raw: str, eid: str, attrs: dict) -> str:
    """改一组属性。样式类写内联 style，几何类写呈现属性。None/"" 表示删除。"""
    t = _locate(raw, eid)
    tag = t["text"]
    styles = _get_style(tag)
    style_dirty = False
    for attr, value in attrs.items():
        if attr in STYLE_PROPS:
            if value is None or value == "":
                styles.pop(attr, None)
            else:
                styles[attr] = _style_value(attr, value)
            style_dirty = True
        elif value is None or value == "":
            tag = _del_attr(tag, attr)
        else:
            tag = _set_attr(tag, attr, _fmt(value) if isinstance(value, (int, float))
                            else str(value))
    if style_dirty:
        tag = _write_style(tag, styles)
    return raw[:t["start"]] + tag + raw[t["end"]:]



# --------------------------------------------------------------------------
# 图层顺序（z-order）
# --------------------------------------------------------------------------
def _build_tree(raw: str) -> dict:
    """把标签扫成一棵树，记录每个可移动元素的完整范围（含子元素）。

    只靠 iter_tags 的 start/end 只能拿到开标签；搬动图层必须搬整块，
    否则 <text> 的内容或 <g> 的子元素会被留在原地。
    """
    root = {"name": "#root", "start": 0, "end": len(raw), "children": [],
            "eid": None, "path": ""}
    stack = [root]
    counters: dict[str, int] = {}
    for t in iter_tags(raw):
        if t["closing"]:
            if len(stack) > 1 and stack[-1]["name"] == t["name"]:
                stack.pop()["end"] = t["end"]
            continue
        node = {"name": t["name"], "start": t["start"], "end": None,
                "children": [], "eid": None,
                "path": f'{stack[-1]["path"]}.{len(stack[-1]["children"])}'.lstrip(".")}
        if t["name"] in MOVABLE:
            n = counters.get(t["name"], 0)
            counters[t["name"]] = n + 1
            node["eid"] = f'{t["name"]}:{n}'
        stack[-1]["children"].append(node)
        if t["text"].rstrip().endswith("/>"):
            node["end"] = t["end"]
        else:
            stack.append(node)
    return root


def _find_parent(root: dict, eid: str):
    """返回 (父节点, 该元素在父节点里的下标)。"""
    for node in root["children"]:
        if node["eid"] == eid:
            return root, root["children"].index(node)
        got = _find_parent(node, eid)
        if got[0] is not None:
            return got
    return None, -1


def _pieces(raw: str, parent: dict):
    """把父节点的内容切成 [(前导空白, 元素文本)]。

    **前导空白属于位置，不属于元素**：只搬元素本体，空白留在原位。
    如果让空白跟着元素走，第一个元素（前缀为空）一挪到最后，就会把
    后面的元素粘成一行——顺序对了但字节对不上，撤销还原不回去。
    """
    kids = [c for c in parent["children"] if c["end"]]
    if not kids:
        return [], ("", "")
    out, prev = [], parent["start"]
    for c in kids:
        out.append((raw[prev:c["start"]], raw[c["start"]:c["end"]]))
        prev = c["end"]
    tail = raw[prev:parent["end"]]
    return out, ("", tail)


def _move(pieces, i: int, j: int):
    """只重排元素本体，前缀留在原位。"""
    bodies = [b for _, b in pieces]
    bodies.insert(j, bodies.pop(i))
    return [(p, b) for (p, _), b in zip(pieces, bodies)]


def _apply_pieces(raw: str, parent: dict, pieces, head_tail) -> str:
    head, tail = head_tail
    body = "".join(p + b for p, b in pieces)
    return raw[:parent["start"]] + head + body + tail + raw[parent["end"]:]


def _reorder(raw: str, eid: str, target: int) -> tuple[str, int, int]:
    root = _build_tree(raw)
    parent, idx = _find_parent(root, eid)
    if parent is None:
        raise KeyError(f"找不到元素 {eid}")
    pieces, head_tail = _pieces(raw, parent)
    # pieces 的下标与 kids 一一对应；_find_parent 的下标可能含不可移动的兄弟，
    # 这里按 eid 重新定位，避免错位。
    kid_idx = -1
    k = 0
    for c in parent["children"]:
        if not c["end"]:
            continue
        if c["eid"] == eid:
            kid_idx = k
            break
        k += 1
    if kid_idx < 0:
        raise KeyError(f"{eid} 无法定位")
    n = len(pieces)
    target = max(0, min(n - 1, target))
    return (_apply_pieces(raw, parent, _move(pieces, kid_idx, target), head_tail),
            kid_idx, target)


def reorder(raw: str, eid: str, mode: str) -> tuple[str, int, int]:
    """mode: front / back / forward / backward。返回 (新内容, 原下标, 新下标)。"""
    root = _build_tree(raw)
    parent, _ = _find_parent(root, eid)
    if parent is None:
        raise KeyError(f"找不到元素 {eid}")
    pieces, _ = _pieces(raw, parent)
    kid_idx = -1
    k = 0
    for c in parent["children"]:
        if not c["end"]:
            continue
        if c["eid"] == eid:
            kid_idx = k
            break
        k += 1
    if kid_idx < 0:
        raise KeyError(f"{eid} 无法定位")
    n = len(pieces)
    target = {"front": n - 1, "back": 0,
              "forward": min(n - 1, kid_idx + 1),
              "backward": max(0, kid_idx - 1)}.get(mode)
    if target is None:
        raise ValueError(f"未知图层操作 {mode}")
    return _reorder(raw, eid, target)


def move_to_index(raw: str, eid: str, idx: int) -> str:
    return _reorder(raw, eid, idx)[0]


def set_order(fig: Path, eid: str, mode: str) -> dict:
    raw = read_raw(fig)
    _backup(fig, raw)
    root = _build_tree(raw)
    parent, _ = _find_parent(root, eid)
    if parent is None:
        raise KeyError(f"找不到元素 {eid}")
    new, old_i, new_i = reorder(raw, eid, mode)
    if old_i == new_i:
        raise RuntimeError(
            f"{eid} 已在{'最上层' if mode == 'front' else '最下层' if mode == 'back' else '边界'}")
    write_raw(fig, new)
    # 记父节点 + 下标，而不是只记 id。
    # id 是按文档顺序算的，元素一挪位置编号就变了，按 id 撤销会找错元素。
    # 记下方向：to 只是下标，界面上要显示"置顶/上移"得靠 mode
    op = {"id": eid, "op": "order", "mode": mode, "parent": parent.get("path", ""),
          "from": old_i, "to": new_i}
    # 元素编号按文档顺序算，挪完位置全图编号都会前后移。
    # 记下新编号：界面靠它跟上选中，清单里显示它才对得上文件现状。
    op["eid_after"] = _eid_at(fig, op["parent"], new_i)
    append_op(fig, op)
    return op


def _eid_at(fig: Path, parent_path: str, index: int) -> str | None:
    """重排后，按「父节点路径 + 子序号」查出该元素现在的新编号。"""
    root = _build_tree(read_raw(fig))
    parent = _find_by_path(root, parent_path or "")
    if parent is None:
        return None
    kids = [c for c in parent["children"] if c["end"]]
    if not (0 <= index < len(kids)):
        return None
    return kids[index].get("eid")


def _find_by_path(root: dict, path: str):
    """按 "0.2.1" 这样的下标路径找节点。父节点用路径标识而不是 id——
    <svg> 元素本身没有 id，用 id 会跟「根容器」混为一谈。"""
    node = root
    for seg in [p for p in str(path).split(".") if p != ""]:
        i = int(seg)
        if i >= len(node["children"]):
            return None
        node = node["children"][i]
    return node


def _find_node(root: dict, eid: str):
    for node in root["children"]:
        if node.get("eid") == eid:
            return node
        got = _find_node(node, eid)
        if got is not None:
            return got
    return None


def undo_order(raw: str, op: dict) -> str:
    """按「父节点 + 下标」把元素挪回原位。不依赖 id，因此不受重排导致的编号漂移影响。"""
    root = _build_tree(raw)
    parent = _find_by_path(root, op.get("parent") or "")
    if parent is None:
        raise KeyError(f"找不到父节点 {op.get('parent')}")
    pieces, head_tail = _pieces(raw, parent)
    i, j = int(op.get("from", 0)), int(op.get("to", 0))
    if not (0 <= i < len(pieces) and 0 <= j < len(pieces)):
        raise ValueError("图层撤销下标越界")
    return _apply_pieces(raw, parent, _move(pieces, j, i), head_tail)

# --------------------------------------------------------------------------
# 清单
# --------------------------------------------------------------------------
def log_path(fig: Path) -> Path:
    return fig.with_suffix(fig.suffix + ".nudge.jsonl")


def append_op(fig: Path, op: dict) -> Path:
    p = log_path(fig)
    op = dict(op)
    op.setdefault("at", time.strftime("%Y-%m-%dT%H:%M:%S"))
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(op, ensure_ascii=False) + "\n")
    return p


def read_ops(fig: Path) -> list[dict]:
    """读清单。坏行跳过而不是抛异常——否则一行残缺就让整个工具打不开。"""
    p = log_path(fig)
    if not p.exists():
        return []
    ops = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("id"):
                ops.append(obj)
        except (ValueError, TypeError):
            continue
    return ops


def _write_ops(fig: Path, ops: list[dict]) -> None:
    p = log_path(fig)
    body = "\n".join(json.dumps(o, ensure_ascii=False) for o in ops)
    p.write_bytes((body + "\n" if body else "").encode("utf-8"))


def _backup(fig: Path, raw: str) -> None:
    bak = fig.with_suffix(fig.suffix + ".bak")
    if not bak.exists():
        bak.write_bytes(raw.encode("utf-8"))


def _inner_text(raw: str, t: dict) -> str:
    """元素内部的可见文字（去掉 tspan 等标签、压平空白）。"""
    if t["name"] != "text":
        return ""
    s0, e0 = _text_region(raw, t)
    inner = raw[t["end"]:e0 - len("</text>")] if e0 > t["end"] else ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", inner)).strip()


def _text_label(raw: str, eid: str) -> str | None:
    """text 元素的内容摘要（前 16 字）。清单里有了它，AI 才能把 text:11
    对到「某行字」上——重新生成图导致编号漂移时，还能按内容重新对齐。"""
    try:
        t = _locate(raw, eid)
    except KeyError:
        return None
    return _inner_text(raw, t)[:16] or None


def describe(raw: str, eid: str) -> str:
    """这个编号现在到底指着什么。改完/改前打出来，改错元素立刻能看见。"""
    try:
        t = _locate(raw, eid)
    except KeyError:
        return f"{eid}（不存在）"
    txt = _inner_text(raw, t)
    if txt:
        return f"{eid}「{txt[:20]}」"
    return f'{eid} <{t["name"]} {_attr(t["text"], "x") or "?"},{_attr(t["text"], "y") or "?"}>'


def _guard(raw: str, eid: str, expect: str | None) -> None:
    """改之前先核对目标内容。

    编号是**位置序号**（第 N 个 <text>），任何图层调整都会让全图编号前后移。
    拿着旧编号去改，不会报错，只会静默改到另一个元素上——真实事故：
    修一处坏折行，用漂移后的 text:11 把另一整行字换成了这行的内容。
    宁可在这里失败，也不要让改错悄悄落盘。
    """
    if not expect:
        return
    t = _locate(raw, eid)
    if t["name"] != "text":
        raise ValueError(f"{eid} 是 <{t['name']}>，不是文字，--expect 用不上"
                         f"——形状按 {describe(raw, eid)} 认")
    txt = _inner_text(raw, t)
    if expect not in txt:
        raise ValueError(
            f"{eid} 现在是「{txt[:24]}」，不含「{expect}」"
            f"——编号多半已漂移（图层调整会重排编号），先 ls 重新查"
        )


def move(fig: Path, eid: str, dx: float, dy: float, note: str = "",
         expect: str | None = None) -> dict:
    """改文件 + 记一行清单。返回实际落地的位移。"""
    if not (math.isfinite(dx) and math.isfinite(dy)):
        raise ValueError("位移必须是有限数值")
    raw = read_raw(fig)
    _guard(raw, eid, expect)
    _backup(fig, raw)
    new = apply_move(raw, eid, dx, dy)
    if new == raw:
        raise RuntimeError(f"{eid} 位移为 0，未改动")
    write_raw(fig, new)
    op = {"id": eid, "op": "move", "dx": round(dx, 3), "dy": round(dy, 3)}
    lbl = _text_label(raw, eid)
    if lbl:
        op["label"] = lbl
    if note:
        op["note"] = note
    append_op(fig, op)
    return op


def set_values(fig: Path, eid: str, attrs: dict,
               expect: str | None = None) -> dict:
    """改一组属性并记一行清单。旧值一并记下，撤销才可能精确。

    宽高必须一次改完再记一条：拆成两次 /set 会变成两条 op，
    用户按一次撤销只退回一半，比不改还糟。
    """
    raw = read_raw(fig)
    _guard(raw, eid, expect)
    _backup(fig, raw)
    t = _locate(raw, eid)
    cur_style = _get_style(t["text"])
    old = {k: (cur_style.get(k) if k in STYLE_PROPS else _attr(t["text"], k))
           for k in attrs}
    new = apply_set(raw, eid, attrs)
    if new == raw:
        raise RuntimeError(f"{eid} 未变化")
    write_raw(fig, new)
    op = {"id": eid, "op": "set", "to": attrs, "from": old}
    lbl = _text_label(raw, eid)
    if lbl:
        op["label"] = lbl
    append_op(fig, op)
    return op


# --------------------------------------------------------------------------
# 文字内容（含回车分行 → tspan）
# --------------------------------------------------------------------------
def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text_region(raw: str, t: dict) -> tuple[int, int]:
    """<text> 元素全区域的字节范围（开标签 + 内容 + </text>；自闭合则只有标签）。"""
    if t["text"].rstrip().endswith("/>"):
        return t["start"], t["end"]
    close = raw.find("</text>", t["end"])
    if close < 0:
        raise ValueError("找不到 </text>")
    return t["start"], close + len("</text>")


def _build_text_inner(tag: str, text: str, old_inner: str) -> str:
    """把多行文本编成 tspan。行距沿用旧 tspan 的 dy（换行节奏是既有设计，
    不该因为改个字就跳成 1.35em）；全新多行才用 字号×1.35 兜底。"""
    lines = str(text).split("\n")
    if len(lines) == 1:
        return _xml_escape(lines[0])
    fs = _num(_attr(tag, "font-size"))
    if not fs:
        fs = _num(_get_style(tag).get("font-size"))
    fs = fs or 14
    x = _attr(tag, "x")
    dy = None
    tspans = re.findall(r"<tspan\b[^>]*>", old_inner)
    if len(tspans) >= 2:
        dy = _attr(tspans[1], "dy")
        x = _attr(tspans[0], "x") or x
    xattr = f' x="{x}"' if x is not None else ""
    dyattr = dy if dy is not None else _fmt(fs * 1.35)
    parts = []
    for i, ln in enumerate(lines):
        d = "0" if i == 0 else dyattr
        parts.append(f'<tspan{xattr} dy="{d}">{_xml_escape(ln)}</tspan>')
    return "".join(parts)


def _retext_raw(raw: str, eid: str, text: str) -> tuple[str, str]:
    """返回 (新全文, 旧元素整段字节)。旧整段留着，撤销才能字节级还原。"""
    t = _locate(raw, eid)
    if t["name"] != "text":
        raise ValueError(f"{eid} 不是文本元素")
    s0, e0 = _text_region(raw, t)
    old_inner = raw[t["end"]:e0 - len("</text>")] if e0 > t["end"] else ""
    tag = t["text"]
    inner = _build_text_inner(tag, text, old_inner)
    if tag.rstrip().endswith("/>"):
        new_el = tag.rstrip()[:-2].rstrip() + ">" + inner + "</text>"
    else:
        new_el = tag + inner + "</text>"
    return raw[:s0] + new_el + raw[e0:], raw[s0:e0]


def set_text(fig: Path, eid: str, text: str,
             expect: str | None = None) -> dict:
    """改文字内容并记一行清单。from 存整个旧元素字节，撤销按字节拼回。"""
    raw = read_raw(fig)
    _guard(raw, eid, expect)
    _backup(fig, raw)
    new, old_region = _retext_raw(raw, eid, str(text))
    if new == raw:
        raise RuntimeError("文本未变化")
    write_raw(fig, new)
    op = {"id": eid, "op": "set_text", "to": text, "from": old_region}
    append_op(fig, op)
    return op


def clean_ops(fig: Path) -> dict:
    """清理清单（只重写 jsonl，图文件一个字节不动——图已是最终态）：

    - 剔除零位移的 move（手抖落盘的 Δ0.00，纯噪声）；
    - 同元素**连续**同类 op 合并：move 累加位移（合并后净 0 连带剔除）、
      set / set_text 取最后一条的 to（from 保持第一条，撤销仍回到最初）。
    跨元素交错的不合并——合并是为可读，不是为改历史语义。
    """
    ops = read_ops(fig)
    out: list[dict] = []
    stats = {"removed": 0, "merged": 0}
    for op in ops:
        kind = op.get("op")
        if kind == "move":
            dx, dy = float(op.get("dx") or 0), float(op.get("dy") or 0)
            if dx == 0 and dy == 0:
                stats["removed"] += 1
                continue
        prev = out[-1] if out else None
        if (prev is not None and prev.get("id") == op.get("id")
                and prev.get("op") == kind and kind in ("move", "set", "set_text")):
            if kind == "move":
                prev["dx"] = round(float(prev.get("dx") or 0) + float(op.get("dx") or 0), 3)
                prev["dy"] = round(float(prev.get("dy") or 0) + float(op.get("dy") or 0), 3)
                if prev["dx"] == 0 and prev["dy"] == 0:
                    out.pop()
                    stats["removed"] += 1
                else:
                    prev["at"] = op.get("at", prev.get("at"))
                    stats["merged"] += 1
                continue
            # set / set_text：to 取最后一条（最终值），from 留第一条（最初值）
            prev["to"] = op.get("to")
            prev["at"] = op.get("at", prev.get("at"))
            stats["merged"] += 1
            continue
        out.append(op)
    if len(out) != len(ops):
        _write_ops(fig, out)
    return {"removed": stats["removed"], "merged": stats["merged"],
            "before": len(ops), "after": len(out)}


def apply_moves(raw: str, moves: list[dict]) -> str:
    for m in moves:
        raw = apply_move(raw, m["id"], float(m["dx"]), float(m["dy"]))
    return raw


def move_multi(fig: Path, moves: list[dict], note: str = "") -> dict:
    """一次手势移动多个元素：记一条 move_multi op，撤销整体回退。
    拆成 N 条单移 op 的话，Ctrl+Z 只退一个元素——比不改还糟。"""
    moves = [{"id": m["id"], "dx": round(float(m["dx"]), 3),
              "dy": round(float(m["dy"]), 3)} for m in moves]
    if not moves:
        raise ValueError("没有可移动的元素")
    for m in moves:
        if not (math.isfinite(m["dx"]) and math.isfinite(m["dy"])):
            raise ValueError("位移必须是有限数值")
    raw = read_raw(fig)
    _backup(fig, raw)
    new = apply_moves(raw, moves)
    if new == raw:
        raise RuntimeError("位移为 0，未改动")
    write_raw(fig, new)
    op = {"id": moves[0]["id"], "op": "move_multi", "n": len(moves), "moves": moves}
    lbl = _text_label(raw, moves[0]["id"])
    if lbl:
        op["label"] = lbl
    if note:
        op["note"] = note
    append_op(fig, op)
    return op


def redo_op(raw: str, op: dict) -> str:
    """把一条已撤销的 op 重新应用（undo 的严格逆运算）。"""
    kind = op.get("op")
    if kind == "set":
        return apply_set(raw, op["id"], op.get("to") or {})
    if kind == "set_text":
        new, _ = _retext_raw(raw, op["id"], op.get("to") or "")
        return new
    if kind == "move_multi":
        return apply_moves(raw, op.get("moves") or [])
    if kind == "order":
        root = _build_tree(raw)
        parent = _find_by_path(root, op.get("parent") or "")
        if parent is None:
            raise KeyError(f"找不到父节点 {op.get('parent')}")
        pieces, head_tail = _pieces(raw, parent)
        i, j = int(op.get("from", 0)), int(op.get("to", 0))
        if not (0 <= i < len(pieces) and 0 <= j < len(pieces)):
            raise ValueError("图层重做下标越界")
        return _apply_pieces(raw, parent, _move(pieces, i, j), head_tail)
    return apply_move(raw, op["id"],
                      float(op.get("dx") or 0), float(op.get("dy") or 0))


def undo_last(fig: Path) -> dict | None:
    """撤销最后一次改动：反向移动 / 恢复旧属性，并从清单里抹掉那一行。"""
    ops = read_ops(fig)
    if not ops:
        return None
    last = ops.pop()
    raw = read_raw(fig)
    if last.get("op") == "set":
        write_raw(fig, apply_set(raw, last["id"], last.get("from") or {}))
    elif last.get("op") == "set_text":
        # from 是旧元素整段字节：按字节拼回去，连行距节奏和空格都一个不动
        t = _locate(raw, last["id"])
        s0, e0 = _text_region(raw, t)
        write_raw(fig, raw[:s0] + last["from"] + raw[e0:])
    elif last.get("op") == "move_multi":
        # 逆序逐个反向位移，一次手势整体还原
        for m in reversed(last.get("moves") or []):
            raw = apply_move(raw, m["id"], -float(m["dx"]), -float(m["dy"]))
        write_raw(fig, raw)
    elif last.get("op") == "order":
        write_raw(fig, undo_order(raw, last))
    else:
        write_raw(fig, apply_move(raw, last["id"],
                                  -float(last.get("dx") or 0),
                                  -float(last.get("dy") or 0)))
    _write_ops(fig, ops)
    return last
