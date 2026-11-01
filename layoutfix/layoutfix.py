# -*- coding: utf-8 -*-
"""layoutfix — 论文/示意图的几何体检与人工微调。

    layoutfix check  fig.svg              体检：把「看着不对」变成可断言的清单
    layoutfix check  fig.svg --strict     CI 门禁，有错误即退出码 7
    layoutfix tune   fig.svg              浏览器里拖动，改完立刻存盘 + 记清单
    layoutfix nudge  fig.svg --id text:3 --dx -1.2 --dy 0    命令行微调（agent 用）
    layoutfix ops    fig.svg              看已落地的改动清单
    layoutfix clean  fig.svg              清理清单：剔零位移、合并同元素连续同类 op
    layoutfix ls     fig.svg              列出可拖元素

坐标一律以图自身单位计算，同时折算成毫米（默认按 96dpi，可用 --width-mm 声明成品宽度）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import edit
import probe


def cmd_check(a) -> int:
    return probe.main([a.file] + (["--json"] if a.json else [])
                      + (["--strict"] if a.strict else [])
                      + (["--width-mm", str(a.width_mm)] if a.width_mm else []))


def cmd_tune(a) -> int:
    import tune
    tune.serve(Path(a.file), port=a.port, open_browser=not a.no_browser,
               idle_minutes=a.idle_exit)
    return 0


def cmd_nudge(a) -> int:
    fig = Path(a.file)
    raw = edit.read_raw(fig)
    who = edit.describe(raw, a.id)     # 改前先记下这个编号指着谁
    op = edit.move(fig, a.id, a.dx, a.dy, note=a.note or "cli",
                   expect=a.expect)
    k = probe.run(fig)["unit_mm"]
    print(f"已移动 {who}  dx={op['dx']} dy={op['dy']} 单位"
          f"（≈ {op['dx'] * k:+.1f} / {op['dy'] * k:+.1f} mm）")
    print(f"清单已追加: {edit.log_path(fig)}")
    return 0


def cmd_ops(a) -> int:
    fig = Path(a.file)
    ops = edit.read_ops(fig)
    if not ops:
        print("（还没有改动）")
        return 0
    k = probe.run(fig)["unit_mm"]
    for o in ops:
        at = o.get("at", "")
        if o.get("op") == "set":
            # set 没有 dx/dy，按位移格式打印会直接 KeyError
            kv = " ".join(f"{a}={v}" for a, v in (o.get("to") or {}).items())
            print(f"{o['id']:<14}{'set':>9}{'':>9}{kv:<18}  {at}")
            continue
        dx, dy = float(o.get("dx") or 0), float(o.get("dy") or 0)
        print(f"{o['id']:<14}{dx:>9.2f}{dy:>9.2f}"
              f"{dx * k:>9.1f}/{dy * k:<8.1f}  {at}")
    return 0


def cmd_clean(a) -> int:
    fig = Path(a.file)
    st = edit.clean_ops(fig)
    print(f"清单已清理：{st['before']} 条 → {st['after']} 条"
          f"（合并 {st['merged']}，剔除零位移 {st['removed']}）")
    print(f"图文件未动：{fig}")
    return 0


def cmd_replay(a) -> int:
    """把旧清单里的人工调整套到重新生成的图上。

    编号是位置序号，重新生成后必然漂移——靠 label（文字前 16 字）做内容锚点
    映射到新图；映射不上的 op 跳过并列出（不猜）。结构 op（add/group/ungroup）
    不重放。默认 --dry 只打印计划；确认后去掉 --dry 落盘并写新清单。
    """
    new_fig, old_log = Path(a.file), Path(a.log)
    ops = edit.read_ops(old_log)
    raw = edit.read_raw(new_fig)
    # 内容锚点表：text 元素的 hint 就是内容前 24 字（label 是前 16 字，够对齐）
    texts = [(el["eid"], el["hint"])
             for el in edit.inventory(edit.read_raw(new_fig))
             if el["tag"] == "text"]

    def resolve(eid, label):
        if label:
            hits = [e for e, txt in texts if txt.startswith(label)]
            if len(hits) == 1:
                return hits[0]
        return eid if edit._tree_node(raw, eid) else None

    applied, skipped = [], []
    for op in ops:
        kind = op.get("op")
        if kind in ("add", "group", "ungroup", "order"):
            skipped.append((op, "结构 op 不重放"))
            continue
        if kind == "move_multi":
            items2 = []
            for it in op.get("items") or []:
                nid = resolve(it["id"], op.get("label"))
                if nid:
                    it2 = dict(it)
                    it2["id"] = nid
                    items2.append(it2)
                else:
                    skipped.append((op, it["id"] + " 映射不上"))
            if items2:
                applied.append({**op, "items": items2})
            continue
        label = op.get("label") or (op.get("to") or "")[:16] \
            if kind == "set_text" else op.get("label")
        nid = resolve(op["id"], label)
        if not nid:
            skipped.append((op, op["id"] + " 映射不上"))
            continue
        applied.append({**op, "id": nid})

    print(f"旧清单 {len(ops)} 条 → 可重放 {len(applied)}，跳过 {len(skipped)}")
    for op, why in skipped:
        print(f"  跳过: [{op.get('op')}] {op.get('id')} — {why}")
    if a.dry:
        for op in applied:
            print("  计划:", op.get("op"), op.get("id"),
                  op.get("label") or (op.get("to") or ""))
        return 0
    if not applied:
        print("没有可应用的改动，未写盘")
        return 0
    new = raw
    for op in applied:
        kind = op.get("op")
        if kind == "set":
            new = edit.apply_set(new, op["id"], op.get("to") or {})
        elif kind == "set_text":
            new, _ = edit._retext_raw(new, op["id"], op.get("to") or "")
        elif kind == "move_multi":
            for it in op.get("items") or []:
                if "dx" in it:
                    new = edit.apply_move(new, it["id"], it["dx"], it["dy"])
                if "set" in it:
                    new = edit.apply_set(new, it["id"], it["set"])
        else:
            new = edit.apply_move(new, op["id"],
                                  float(op.get("dx") or 0), float(op.get("dy") or 0))
    edit.write_raw(new_fig, new)
    for op in applied:
        edit.append_op(new_fig, op)
    print(f"已套用 {len(applied)} 条到 {new_fig}，清单同步写入")
    return 0


def cmd_ls(a) -> int:
    fig = Path(a.file)
    # 必须按字节读：read_text 在 Windows 会把 \r\n 折成 \n，
    # 而 inventory 是靠字节偏移切内容的，一折就切错位置。
    for el in edit.inventory(edit.read_raw(fig)):
        print(f"{el['eid']:<14}{el['tag']:<9}{el['hint']}")
    print("\n编号是位置序号（第 N 个 <text>）。图层置顶/上移会让全图编号前后移，"
          "\n动过图层就要重新 ls；改动时带 --expect 几个字最稳。")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="layoutfix", description="示意图几何体检与微调")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="几何体检")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--width-mm", type=float, default=None)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("tune", help="浏览器拖动界面")
    p.add_argument("file")
    p.add_argument("--port", type=int, default=8770)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--idle-exit", type=float, default=0.0, dest="idle_exit",
                   help="空闲 N 分钟自动关闭服务（0=不自动）；页面开着即不算空闲")
    p.set_defaults(fn=cmd_tune)

    p = sub.add_parser("nudge", help="命令行微调一个元素")
    p.add_argument("file")
    p.add_argument("--id", required=True, help="元素句柄，如 text:3（用 ls 查）")
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
    p.add_argument("--expect", default=None,
                   help="目标内容里的几个字，对不上就拒绝改（防编号漂移改错元素）")
    p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_nudge)

    p = sub.add_parser("ops", help="查看改动清单")
    p.add_argument("file")
    p.set_defaults(fn=cmd_ops)

    p = sub.add_parser("clean", help="清理改动清单（剔零位移、合并碎片）")
    p.add_argument("file")
    p.set_defaults(fn=cmd_clean)

    p = sub.add_parser("ls", help="列出可拖元素")
    p.add_argument("file")
    p.set_defaults(fn=cmd_ls)

    p = sub.add_parser("replay", help="把旧清单的人工调整套到重新生成的图上")
    p.add_argument("file", help="重新生成的新图")
    p.add_argument("log", help="旧图的 .nudge.jsonl 清单")
    p.add_argument("--dry", action="store_true", help="只打印映射计划，不写盘")
    p.set_defaults(fn=cmd_replay)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        # agent 读的是这一行，不是 traceback：说清哪一步不行、怎么补救。
        print(f"✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
