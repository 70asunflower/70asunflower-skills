# -*- coding: utf-8 -*-
"""layoutfix.probe — 几何体检：把「看着不对」变成可断言的违例清单。

设计要点（都是踩过坑才定的）：

1. 底座用 MuPDF 统一吃 .svg / .pdf。MuPDF 原生支持 SVG，转成页面后
   get_texttrace() 给出精确文字包围盒（含字号、方向、绘制序号），
   get_drawings() 给出矢量形状与填充色。一套代码通吃 matplotlib 出的 PDF、
   Illustrator 的 PDF、agent 直出的 SVG。

2. z-order 必须用 seqno 交错排序，不能只比 bbox。否则背景 rect 会把整张图
   的文字都判成「被覆盖」——实测 112 个全是误报。

3. 身份（id）只能从 SVG 源码层拿，MuPDF 不保留 id。所以是
   「MuPDF 给几何，SVG 给身份」，两边按文字内容优先、位置兜底对齐。

4. 文字合并必须先聚「行」再按 x 左到右拼，否则同一行会被拆成碎片、
   文字顺序还会颠倒（MuPDF 的 span 顺序不保证是阅读顺序）。

用法:
    python probe.py fig.svg
    python probe.py fig.svg --json --strict
    python probe.py fig.svg --width-mm 160     # 声明成品物理宽度
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf

PT2MM = 25.4 / 72.0
DEFAULT_UNIT_MM = 25.4 / 96.0  # SVG 无物理宽度时按 CSS 96dpi 折算


# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------
@dataclass
class Item:
    kind: str                 # text | shape
    seq: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str = ""
    size: float = 0.0
    fill: tuple | None = None
    opacity: float = 1.0
    eid: str = ""
    line: int = -1

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Violation:
    code: str
    severity: str             # error | warn
    msg: str
    eids: list[str] = field(default_factory=list)
    region: tuple | None = None   # 违例区域，可直接喂给 snap --clip
    ffids: list[str] = field(default_factory=list)   # 浏览器可选中句柄

    def to_dict(self):
        d = {"code": self.code, "severity": self.severity,
             "msg": self.msg, "eids": self.eids, "ffids": self.ffids}
        if self.region:
            d["region"] = [round(v, 2) for v in self.region]
        return d


# --------------------------------------------------------------------------
# SVG 源码层：身份与语义
# --------------------------------------------------------------------------
NS = "{http://www.w3.org/2000/svg}"
MOVABLE_TAGS = ("rect", "text", "polyline", "line", "path", "g",
                "circle", "ellipse", "image", "polygon")


def _strip_ns(tag: str) -> str:
    return tag.replace(NS, "") if tag.startswith(NS) else tag


def _slug(s: str, n: int = 14) -> str:
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "", s)
    return s[:n] or "x"


def parse_svg(path: Path) -> dict[str, Any]:
    import xml.etree.ElementTree as ET

    raw = path.read_text(encoding="utf-8")
    root = ET.fromstring(raw)

    vb = root.get("viewBox", "")
    vb_w = vb_h = 0.0
    if vb:
        parts = [float(p) for p in re.split(r"[,\s]+", vb.strip()) if p]
        if len(parts) == 4:
            vb_w, vb_h = parts[2], parts[3]
    if not vb_w:
        vb_w = float(re.sub(r"[^\d.]", "", root.get("width", "0")) or 0)
        vb_h = float(re.sub(r"[^\d.]", "", root.get("height", "0")) or 0)

    used: dict[str, int] = {}

    def uid(base: str) -> str:
        base = base or "el"
        n = used.get(base, 0)
        used[base] = n + 1
        return base if n == 0 else f"{base}-{n}"

    rects, texts, arrows = [], [], []
    seq_counter: dict[str, int] = {}
    for el in root.iter():
        tag = _strip_ns(el.tag)
        ffid = ""
        if tag in MOVABLE_TAGS:
            n = seq_counter.get(tag, 0)
            seq_counter[tag] = n + 1
            ffid = f"{tag}:{n}"
        if tag == "rect":
            try:
                w, h = float(el.get("width", 0)), float(el.get("height", 0))
                x, y = float(el.get("x", 0) or 0), float(el.get("y", 0) or 0)
            except ValueError:
                continue
            if w <= 0 or h <= 0:
                continue
            fill = el.get("fill", "")
            if fill in ("none", "") or fill.startswith("url("):
                continue
            rects.append({"eid": el.get("id") or uid("rect"), "ffid": ffid,
                          "x": x, "y": y, "w": w, "h": h, "fill": fill})
        elif tag == "text":
            content = "".join(el.itertext()).strip()
            if not content:
                continue
            try:
                fs = float(el.get("font-size", 12))
            except ValueError:
                fs = 12.0
            texts.append({
                "eid": el.get("id") or uid("t-" + _slug(content)),
                "ffid": ffid,
                "text": content,
                "x": float(el.get("x", 0) or 0),
                "y": float(el.get("y", 0) or 0),
                "size": fs,
                "anchor": el.get("text-anchor", "start"),
            })
        elif tag in ("polyline", "line", "path"):
            if not el.get("marker-end"):
                continue
            pts = _arrow_points(tag, el)
            if len(pts) >= 2:
                arrows.append({"eid": el.get("id") or uid("a"),
                               "ffid": ffid, "pts": pts})

    return {"vb_w": vb_w, "vb_h": vb_h, "rects": rects, "texts": texts,
            "arrows": arrows, "raw": raw}


def _arrow_points(tag: str, el) -> list[tuple[float, float]]:
    if tag == "line":
        try:
            return [(float(el.get("x1", 0)), float(el.get("y1", 0))),
                    (float(el.get("x2", 0)), float(el.get("y2", 0)))]
        except ValueError:
            return []
    raw = el.get("points", "") if tag == "polyline" else el.get("d", "")
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", raw)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


# --------------------------------------------------------------------------
# MuPDF 层：精确几何
# --------------------------------------------------------------------------
def load_geometry(path: Path) -> tuple[tuple[float, float], list[dict], list[Item]]:
    # 用完必须 close：ThreadingHTTPServer 下句柄会随请求次数累积。
    doc = pymupdf.open(str(path))
    page = doc[0]
    page_size = (page.rect.width, page.rect.height)

    spans = []
    for s in page.get_texttrace():
        txt = "".join(chr(c[0]) for c in s.get("chars", []))
        if not txt.strip():
            continue
        b = s["bbox"]
        spans.append({"seq": int(s.get("seqno", 0)),
                      "x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3],
                      "text": txt, "size": float(s.get("size", 0))})

    lines = _merge_lines(spans)
    items = [Item(kind="text", **ln) for ln in lines]

    for d in page.get_drawings():
        r = d["rect"]
        if r.width < 1 or r.height < 1:
            continue
        # 只有「有填充」的形状才可能遮挡文字；描边矩形(面板边框) fill 为 None，
        # 当成不透明覆盖会造出大量假阳性。
        if d.get("fill") is None:
            continue
        items.append(Item(kind="shape", seq=int(d.get("seqno", 0)),
                          x0=r.x0, y0=r.y0, x1=r.x1, y1=r.y1,
                          fill=d.get("fill"),
                          opacity=float(d.get("fill_opacity", 1.0) or 1.0)))
    doc.close()
    return page_size, spans, items


def _merge_lines(spans: list[dict]) -> list[dict]:
    """先把 span 聚成视觉行，再在行内按 x 从左到右拼接。

    三个必须做对的地方（每一个都是踩出来的）：
      1. MuPDF 的 span 顺序不是阅读顺序，同一行里 CJK 与拉丁会交错，
         直接按 (y, x) 排序会把一行拆碎、把文字顺序颠倒；
      2. 横向**重叠**的两段字不能并成一行——它们是两段独立的字，
         并起来会让「同一行不算重叠」把真正的压字缺陷全部放过（假阴性）；
      3. 两段字在 x 方向交错时，不能用单指针贪心合并，否则前面的行
         一关闭就再也接不回去，一段字会被拆成好几行。要维护多条「开着的行」。
    """
    if not spans:
        return []

    rows: list[dict] = []
    for s in sorted(spans, key=lambda s: (s["y0"] + s["y1"]) / 2):
        cy = (s["y0"] + s["y1"]) / 2
        for row in rows:
            if abs(cy - row["cy"]) <= max(1.0, 0.35 * row["size"]):
                row["spans"].append(s)
                row["size"] = max(row["size"], s["size"])
                break
        else:
            rows.append({"cy": cy, "size": s["size"], "spans": [s]})

    lines: list[dict] = []
    for row in rows:
        open_lines: list[dict] = []
        for s in sorted(row["spans"], key=lambda s: s["x0"]):
            target = None
            for L in open_lines:
                sz = max(L["size"], 1.0)
                if s["x0"] < L["x1"] - 0.2 * sz:
                    continue                      # 横向重叠：不同行
                if s["x0"] > L["x1"] + 0.6 * sz:
                    continue                      # 间隔过大：不同行
                target = L
                break
            if target is None:
                target = dict(s)
                target["_m"] = [s]
                open_lines.append(target)
            else:
                target["x1"] = max(target["x1"], s["x1"])
                target["x0"] = min(target["x0"], s["x0"])
                target["y0"] = min(target["y0"], s["y0"])
                target["y1"] = max(target["y1"], s["y1"])
                target["text"] += s["text"]
                target["seq"] = min(target["seq"], s["seq"])
                target["_m"].append(s)
        lines.extend(open_lines)

    for i, ln in enumerate(lines):
        for sp in ln.pop("_m"):
            sp["line"] = i
    return lines


def attach_identity(lines: list[dict], svg: dict) -> None:
    """按文字内容精确匹配，未中的按位置就近兜底。每个 eid 只用一次。"""
    norm = lambda s: re.sub(r"\s+", "", s)
    pool = svg["texts"]
    used: set[str] = set()

    for ln in lines:
        key = norm(ln["text"])
        for t in pool:
            if t["eid"] in used:
                continue
            if norm(t["text"]) == key:
                ln["eid"] = t["eid"]
                used.add(t["eid"])
                break

    for ln in lines:
        if ln.get("eid"):
            continue
        best, bd = None, 1e9
        cx = (ln["x0"] + ln["x1"]) / 2
        for t in pool:
            if t["eid"] in used:
                continue
            ref = cx if t["anchor"] == "middle" else ln["x0"]
            d = abs(t["x"] - ref) + abs(t["y"] - ln["y1"])
            if d < bd:
                bd, best = d, t
        if best and bd <= 3.0 * max(best["size"], 8.0):
            ln["eid"] = best["eid"]
            used.add(best["eid"])


# --------------------------------------------------------------------------
# 检查
# --------------------------------------------------------------------------
def _inter(a, b) -> tuple[float, float]:
    return (min(a.x1, b.x1) - max(a.x0, b.x0),
            min(a.y1, b.y1) - max(a.y0, b.y0))


def dedupe_spans(spans: list[dict]) -> list[dict]:
    """同一段文字在同一位置画两遍 = 白色描边遮罩（stroke + paint-order）。

    MuPDF 会把它渲染成两次文字绘制，不去重的话重叠检测会把同一段字
    当成互相压叠，实测一张图能刷出 87 条假阳性。这是合法排版手法，不是缺陷。
    """
    seen, out = set(), []
    for s in spans:
        key = (s["text"].strip(), round(s["x0"], 1), round(s["y0"], 1),
               round(s["x1"], 1))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def check_overlap(spans: list[dict], k: float) -> list[Violation]:
    """两段文字包围盒相交。

    必须用**原始 span**，不能用合并后的行：两段文字一旦真的重叠，
    合并逻辑会把它们并成同一行，重叠就凭空消失了（假阴性）。
    """
    out = []
    texts = [Item(kind="text", seq=s["seq"], x0=s["x0"], y0=s["y0"],
                  x1=s["x1"], y1=s["y1"], text=s["text"], size=s["size"],
                  eid=s.get("eid", ""), line=s.get("line", -1))
             for s in spans]
    best: dict = {}
    for a in range(len(texts)):
        for b in range(a + 1, len(texts)):
            A, B = texts[a], texts[b]
            if A.line >= 0 and A.line == B.line:
                continue          # 同一行内部的相邻 span，不算重叠
            ox, oy = _inter(A, B)
            if ox <= 0.6:
                continue
            # 垂直方向的重叠要拿字号当尺子：文字包围盒含上下留白，
            # 行距偏紧时相邻两行的 bbox 会「假重叠」0.2–0.4mm，肉眼看完全没事。
            # 实测 0.8mm(约字号 25%) 是真挤，0.3mm(约字号 9%) 是噪声。
            if oy <= 0.12 * max(1.0, min(A.size, B.size)):
                continue
            smaller = min(A.w * A.h, B.w * B.h)
            if smaller <= 0 or (ox * oy) / smaller < 0.04:
                continue
            # 一行被切成多个 span 时，同一对行会被命中多次，只留最严重的那次
            key = tuple(sorted([A.line, B.line]))
            if key not in best or ox * oy > best[key][0]:
                best[key] = (ox * oy, ox, oy, A, B)

    for _, ox, oy, A, B in best.values():
        out.append(Violation(
            "text_overlap", "error",
            f"文字重叠 {ox * k:.1f}×{oy * k:.1f}mm"
            f"「{_clip(A.text)}」×「{_clip(B.text)}」",
            [A.eid, B.eid],
            (min(A.x0, B.x0), min(A.y0, B.y0), max(A.x1, B.x1), max(A.y1, B.y1)),
        ))
    return out


def check_occluded(spans: list[dict], items: list[Item], k: float) -> list[Violation]:
    """文字先画、之后被不透明形状盖住 —— 必须看 seqno，不能只比 bbox。

    用原始 span 而不是合并行：span 各自带准确 seqno，合并会污染顺序。
    """
    out = []
    shapes = [i for i in items if i.kind == "shape" and i.opacity > 0.95]
    for s in spans:
        st = Item(kind="text", seq=s["seq"], x0=s["x0"], y0=s["y0"],
                  x1=s["x1"], y1=s["y1"], text=s["text"], size=s["size"])
        for sh in shapes:
            if sh.seq <= st.seq:
                continue
            ox, oy = _inter(st, sh)
            if ox <= 0 or oy <= 0:
                continue
            cover = (ox * oy) / max(1e-6, st.w * st.h)
            if cover < 0.08:
                continue
            out.append(Violation(
                "text_occluded", "error",
                f"文字被后续形状覆盖 {cover * 100:.0f}%「{_clip(st.text)}」",
                [sh.eid],
                (min(st.x0, sh.x0), min(st.y0, sh.y0), max(st.x1, sh.x1), max(st.y1, sh.y1)),
            ))
            break
    return out


def check_bounds(items: list[Item], size: tuple[float, float],
                 k: float) -> list[Violation]:
    out = []
    W, H = size
    tol = 0.6
    for t in items:
        if t.kind != "text":
            continue
        over = []
        if t.x0 < -tol:
            over.append(f"左 {-t.x0 * k:.1f}mm")
        if t.y0 < -tol:
            over.append(f"上 {-t.y0 * k:.1f}mm")
        if t.x1 > W + tol:
            over.append(f"右 {(t.x1 - W) * k:.1f}mm")
        if t.y1 > H + tol:
            over.append(f"下 {(t.y1 - H) * k:.1f}mm")
        if over:
            out.append(Violation(
                "text_out_of_canvas", "error",
                f"文字超出画布 {'/'.join(over)}「{_clip(t.text)}」",
                [t.eid], (t.x0, t.y0, t.x1, t.y1)))
    return out


def _dist_to_rect(px: float, py: float, r: dict) -> float:
    x0, y0 = r["x"], r["y"]
    x1, y1 = x0 + r["w"], y0 + r["h"]
    dx = max(x0 - px, 0.0, px - x1)
    dy = max(y0 - py, 0.0, py - y1)
    return (dx * dx + dy * dy) ** 0.5


def check_dangling(svg: dict, k: float, gap_mm: float = 2.5) -> list[Violation]:
    """箭头端点没接到框上 —— 截图看不出来，人也说不清，几何一算就清楚。

    判据不是「离框远」，而是「只接上了一头」。两端都挨着框 = 正常连接线；
    两端都不挨 = 图例/示意箭头，本来就不连东西，跳过。只有一端接上、
    另一端悬空才是真缺陷——这正是 AI 画的图最常犯的错。
    """
    out = []
    arrows, rects = svg["arrows"], svg["rects"]
    if not arrows or not rects:
        return out
    W, H = svg["vb_w"], svg["vb_h"]
    boxes = [r for r in rects if r["w"] * r["h"] < 0.5 * W * H]
    if not boxes:
        return out
    for a in arrows:
        ends = [("起点", a["pts"][0]), ("端点", a["pts"][-1])]
        dists = [min(_dist_to_rect(px, py, r) for r in boxes) * k for _, (px, py) in ends]
        touching = [d <= gap_mm for d in dists]
        if not any(touching):
            continue  # 图例箭头：两端都不连框
        for (label, (px, py)), d, ok in zip(ends, dists, touching):
            if ok:
                continue
            out.append(Violation(
                "arrow_dangling", "warn",
                f"箭头{label}悬空：距最近框边缘 {d:.1f}mm",
                [a["eid"]], (px - 5, py - 5, px + 5, py + 5)))
    return out


def check_offcenter(svg: dict, k: float, tol_mm: float = 1.2) -> list[Violation]:
    """text-anchor=middle 的文字，其 x 应当落在所在框的水平中心。

    纯 SVG 层计算：不依赖文字宽度，也不受 MuPDF 合并影响。
    两个坑：
      1. 必须排除画布背景 rect，否则每个标签都被判成「偏右半个画布」；
      2. 标签常在框「下方」而不是框内（居中标注），垂直判定要留出下方余量，
         否则会匹配到外层大容器，算出几十毫米的假偏移。
    """
    out = []
    W, H = svg["vb_w"], svg["vb_h"]
    canvas_area = W * H or 1.0

    # 一个框里挤着多个居中文字时（接插件引脚编号、图例项），
    # 「居中」本来就不成立，跳过——否则会刷出几十条假偏移。
    multi: dict[str, int] = {}
    for t in svg["texts"]:
        if t["anchor"] != "middle":
            continue
        pad0 = 2.0 * max(t["size"], 8.0)
        for r in svg["rects"]:
            if r["w"] * r["h"] > 0.5 * canvas_area:
                continue
            if (r["x"] <= t["x"] <= r["x"] + r["w"]
                    and r["y"] - pad0 <= t["y"] <= r["y"] + r["h"] + pad0):
                multi[r["eid"]] = multi.get(r["eid"], 0) + 1

    for t in svg["texts"]:
        if t["anchor"] != "middle":
            continue
        pad = 2.0 * max(t["size"], 8.0)
        host = None
        for r in svg["rects"]:
            if r["w"] * r["h"] > 0.5 * canvas_area:
                continue
            if not (r["x"] <= t["x"] <= r["x"] + r["w"]):
                continue
            if not (r["y"] - pad <= t["y"] <= r["y"] + r["h"] + pad):
                continue
            if host is None or r["w"] * r["h"] < host["w"] * host["h"]:
                host = r
        if not host or multi.get(host["eid"], 0) > 1:
            continue
        off = t["x"] - (host["x"] + host["w"] / 2)
        if abs(off) * k > tol_mm:
            out.append(Violation(
                "label_offcenter", "warn",
                f"居中标签偏{'右' if off > 0 else '左'} {abs(off) * k:.1f}mm"
                f"「{_clip(t['text'])}」",
                [t["eid"], host["eid"]],
                (host["x"], host["y"], host["x"] + host["w"], host["y"] + host["h"])))
    return out


def _clip(s: str, n: int = 18) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "…"


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def run(path: Path, width_mm: float | None = None) -> dict:
    is_svg = path.suffix.lower() == ".svg"
    svg = parse_svg(path) if is_svg else None

    page_size, spans, items = load_geometry(path)
    spans = dedupe_spans(spans)
    lines = [i for i in items if i.kind == "text"]
    if svg:
        ds = [{"seq": i.seq, "x0": i.x0, "y0": i.y0, "x1": i.x1, "y1": i.y1,
               "text": i.text, "size": i.size, "eid": ""} for i in lines]
        attach_identity(ds, svg)
        for it, d in zip(lines, ds):
            it.eid = d.get("eid", "")
        # span -> line 的 eid 回填：重叠检测跑在 span 上，但报告要给人读的名字
        for sp in spans:
            li = sp.get("line", -1)
            if 0 <= li < len(lines):
                sp["eid"] = lines[li].eid

    if width_mm and svg and svg["vb_w"]:
        k = width_mm / svg["vb_w"]
    elif svg and svg["vb_w"]:
        k = DEFAULT_UNIT_MM
    else:
        k = PT2MM

    viol: list[Violation] = []
    viol += check_overlap(spans, k)
    viol += check_occluded(spans, items, k)
    viol += check_bounds(items, page_size, k)
    if svg:
        viol += check_dangling(svg, k)
        viol += check_offcenter(svg, k)
        # 把人类可读的 eid 翻译成浏览器句柄，供拖动界面高亮定位
        eid2ff: dict[str, str] = {}
        for group in ("texts", "rects", "arrows"):
            for el in svg[group]:
                if el.get("ffid"):
                    eid2ff[el["eid"]] = el["ffid"]
        for v in viol:
            v.ffids = [eid2ff[e] for e in v.eids if e in eid2ff]

    return {
        "file": str(path),
        "unit_mm": round(k, 5),
        "canvas": {"w": round(page_size[0], 2), "h": round(page_size[1], 2)},
        "counts": {
            "text": len(lines),
            "shape": sum(1 for i in items if i.kind == "shape"),
            "arrow": len(svg["arrows"]) if svg else 0,
            "violations": len(viol),
            "errors": sum(1 for v in viol if v.severity == "error"),
            "warns": sum(1 for v in viol if v.severity == "warn"),
        },
        "violations": [v.to_dict() for v in viol],
    }


def render(report: dict) -> str:
    c = report["counts"]
    lines = [f"{Path(report['file']).name}  "
             f"文字 {c['text']} · 形状 {c['shape']} · 箭头 {c['arrow']}"]
    if not report["violations"]:
        lines.append("  ✓ 无违例")
        return "\n".join(lines)
    lines.append(f"  ✗ {c['errors']} 处错误 / {c['warns']} 处警告")
    order = {"error": 0, "warn": 1}
    for v in sorted(report["violations"], key=lambda v: order[v["severity"]]):
        mark = "✗" if v["severity"] == "error" else "!"
        ids = ",".join(e for e in v["eids"] if e)
        lines.append(f"    {mark} [{v['code']}] {v['msg']}" + (f"   ({ids})" if ids else ""))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="probe", description="layoutfix 几何体检")
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="有错误即退出码 7")
    ap.add_argument("--width-mm", type=float, default=None,
                    help="成品物理宽度(mm)，用于把用户单位换算成毫米")
    a = ap.parse_args(argv)

    p = Path(a.file)
    if not p.exists():
        print(f"文件不存在: {p}", file=sys.stderr)
        return 2
    rep = run(p, a.width_mm)
    print(json.dumps(rep, ensure_ascii=False, indent=2) if a.json else render(rep))
    return 7 if (a.strict and rep["counts"]["errors"]) else 0


if __name__ == "__main__":
    sys.exit(main())
