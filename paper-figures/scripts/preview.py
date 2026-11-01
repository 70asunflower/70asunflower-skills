# -*- coding: utf-8 -*-
"""preview.py — 把图渲成 PNG，供 agent「看一眼」。

为什么需要它：`layoutfix check` 只能断言几何问题（压字、越界、悬空），
审美、配色、整体观感仍需要真的看一眼。而整图截图既贵又看不清细节——
正确做法是**只渲违例区域**，把 200×120 的小图丢进视觉通道。

SVG / PDF 直接用 PyMuPDF 渲染，不需要 Node、不需要 Chrome（layoutfix 已经依赖 PyMuPDF）。
HTML 页面（海报、演示页）用同目录的 `snap/snap.mjs`。

用法:
    python preview.py fig.svg
    python preview.py fig.pdf -o out/fig.png --dpi 200
    python preview.py fig.svg --clip 100,200,500,380 --scale 3
    python preview.py fig.svg --violations          # 自动渲 check 报出的每个区域

退出码：0 成功；2 输入错误。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import os
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent


def render(src: Path, out: Path, dpi: float = 150.0,
           clip: tuple[float, float, float, float] | None = None) -> Path:
    doc = pymupdf.open(str(src))
    try:
        if doc.page_count < 1:
            raise ValueError("文档没有页面")
        page = doc[0]
        rect = None
        if clip:
            rect = pymupdf.Rect(*clip) & page.rect   # 与页面求交，防止越界报错
            if rect.is_empty:
                raise ValueError(f"裁剪区域落在页面外: {clip}")
        out.parent.mkdir(parents=True, exist_ok=True)
        pm = page.get_pixmap(dpi=int(round(dpi)), clip=rect)  # dpi 必须是 int
        pm.save(str(out))
        print(f"{out}  {pm.width}×{pm.height}px"
              + (f"  clip={[round(v) for v in rect]}" if rect else ""))
        return out
    finally:
        doc.close()


def find_layoutfix() -> Path | None:
    """找 layoutfix 的可执行入口。它是**独立技能**，不一定和本脚本装在一起。

    按可能性从近到远试：同仓库的兄弟技能目录 → 旧版嵌在 scripts/ 下的位置
    → 环境变量指定。都找不到就返回 None，调用方静默降级。
    """
    cands = [
        HERE.parent.parent / "layoutfix" / "layoutfix.py",   # my-skills/layoutfix/
        HERE / "layoutfix" / "layoutfix.py",                 # 旧位置，兼容
    ]
    env = os.environ.get("LAYOUTFIX_CLI")
    if env:
        cands.insert(0, Path(env))
    for c in cands:
        if c.is_file():
            return c
    return None


def probe_regions(src: Path) -> list[dict]:
    """调用 layoutfix 拿违例区域。没装就返回空，不影响单纯渲染。"""
    cli = find_layoutfix()
    if cli is None:
        return []
    try:
        r = subprocess.run([sys.executable, str(cli), "check", str(src), "--json"],
                           capture_output=True, text=True, timeout=120)
        data = json.loads(r.stdout or "{}")
    except (ValueError, subprocess.SubprocessError):
        return []
    return [v for v in data.get("violations", []) if v.get("region")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="preview", description="图渲染成 PNG")
    ap.add_argument("file")
    ap.add_argument("-o", "--out", default=None, help="输出路径，默认 <图名>.preview.png")
    ap.add_argument("--dpi", type=float, default=150.0)
    ap.add_argument("--scale", type=float, default=1.0, help="dpi 倍率，等价于 --dpi×N")
    ap.add_argument("--clip", default=None, help="裁剪区域 x0,y0,x1,y1（图坐标）")
    ap.add_argument("--violations", action="store_true",
                    help="逐个渲染 layoutfix 报出的违例区域")
    a = ap.parse_args(argv)

    src = Path(a.file)
    if not src.exists():
        print(f"文件不存在: {src}", file=sys.stderr)
        return 2
    if src.suffix.lower() not in (".svg", ".pdf"):
        print(f"只支持 .svg / .pdf，收到 {src.suffix}；"
              f"HTML 页面请用 scripts/snap/snap.mjs", file=sys.stderr)
        return 2

    dpi = a.dpi * a.scale
    stem = src.with_suffix("")

    if a.violations:
        items = probe_regions(src)
        if not items:
            print("没有带 region 的违例，或找不到 layoutfix。", file=sys.stderr)
            return 2
        for i, v in enumerate(items, 1):
            x0, y0, x1, y1 = v["region"]
            pad = max(x1 - x0, y1 - y0) * 0.12 + 6
            out = stem.parent / f"{stem.name}.v{i}.png"
            render(src, out, dpi,
                   (x0 - pad, y0 - pad, x1 + pad, y1 + pad))
            print(f"    [{v['code']}] {v['msg']}")
        return 0

    clip = None
    if a.clip:
        try:
            clip = tuple(float(v) for v in a.clip.split(","))
            if len(clip) != 4:
                raise ValueError
        except ValueError:
            print("--clip 需要 4 个数：x0,y0,x1,y1", file=sys.stderr)
            return 2

    out = Path(a.out) if a.out else stem.parent / f"{stem.name}.preview.png"
    render(src, out, dpi, clip)
    return 0


if __name__ == "__main__":
    sys.exit(main())
