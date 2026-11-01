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
    tune.serve(Path(a.file), port=a.port, open_browser=not a.no_browser)
    return 0


def cmd_nudge(a) -> int:
    fig = Path(a.file)
    op = edit.move(fig, a.id, a.dx, a.dy, note=a.note or "cli")
    k = probe.run(fig)["unit_mm"]
    print(f"已移动 {op['id']}  dx={op['dx']} dy={op['dy']} 单位"
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


def cmd_ls(a) -> int:
    fig = Path(a.file)
    for el in edit.inventory(fig.read_text(encoding="utf-8")):
        print(f"{el['eid']:<14}{el['tag']:<9}{el['hint']}")
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
    p.set_defaults(fn=cmd_tune)

    p = sub.add_parser("nudge", help="命令行微调一个元素")
    p.add_argument("file")
    p.add_argument("--id", required=True, help="元素句柄，如 text:3（用 ls 查）")
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
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

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
