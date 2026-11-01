#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_layout.py -- layout forensics on a *compiled* PDF. Read-only, no network.

Answers the questions that static source checks cannot:

  * how much blank space is there, and where (per page, per column)
  * which blank gaps are abnormal -- by comparing a gap against the same
    document's own distribution instead of a guessed threshold
  * which figure landed on which page, and whether it is single or full width
  * does the compiled PDF actually correspond to the revision under review

Usage:
    python check_layout.py paper.pdf
    python check_layout.py paper.pdf --gap 18 --verify "[Y5ZDBSZL01]"
    python check_layout.py paper.pdf --pages 4,5

Defaults are IEEEtran conference geometry on US Letter (6.5in x 9.25in text
area, two columns with a 0.25in gutter, top margin 0.75in).
"""

import argparse
import re
import sys

try:  # 输出被重定向到 GBK 管道/文件时，⚠★ 等符号不致崩
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

try:
    import pymupdf
except ImportError:  # pragma: no cover
    try:
        import fitz as pymupdf
    except ImportError:
        sys.exit("需要 PyMuPDF：pip install pymupdf（本机可用 miniconda 的 python）")

# IEEEtran conference, US Letter. Override on the command line for A4 or other classes.
TOP = 51.0        # y of the first text baseline area (top margin 0.75in -> 54pt, minus glyph slack)
BOTTOM = 719.0    # y of the bottom of the text area
COLSPLIT = 306.0  # x that separates left from right column

HEADING = re.compile(r"^[A-Z]\.\s|^[IVX]+\.\s[A-Z]|^REFERENCES|^ACKNOWLEDG")
CAPTION = re.compile(r"^(Fig\.\s*\d+\.|TABLE\s+[IVXL]+|Table\s+[IVXL]+)")
REFITEM = re.compile(r"^\[(\d+)\]")


def lines_of(page):
    """All non-empty text lines on a page: (y_top, y_bottom, x_left, text)."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                out.append((line["bbox"][1], line["bbox"][3], line["bbox"][0], text))
    out.sort()
    return out


def column(x, colsplit):
    return "L" if x < colsplit else "R"


def report_columns(doc, pages, top, bottom, colsplit, gap):
    print("=== 每页每栏：文字范围 / 顶部空 / 底部空 / 内部空隙 > %d pt ===" % gap)
    for i in pages:
        for tag, lo, hi in (("L", 0, colsplit), ("R", colsplit, 1e9)):
            ys = [(y0, y1) for y0, y1, x, _ in lines_of(doc[i]) if lo <= x < hi]
            if not ys:
                print("  p%-3d %s  (空)" % (i + 1, tag))
                continue
            first = min(y0 for y0, _ in ys)
            last = max(y1 for _, y1 in ys)
            gaps, prev = [], ys[0][1]
            for y0, y1 in ys[1:]:
                if y0 - prev > gap:
                    gaps.append((round(prev), round(y0), round(y0 - prev)))
                prev = max(prev, y1)
            print("  p%-3d %s  文字 y=%6.1f..%6.1f   顶部空 %5.1f   底部空 %5.1f   内部空隙 %s"
                  % (i + 1, tag, first, last, max(0.0, first - top),
                     max(0.0, bottom - last), gaps or "无"))


def report_headings(doc, pages, colsplit):
    """A blank gap is abnormal or not only relative to this document's own spread."""
    print("\n=== 标题前间距（同一文档内的正常区间自行给出）===")
    vals = []
    for i in pages:
        ls = lines_of(doc[i])
        for k, (y0, _, x, text) in enumerate(ls):
            if not HEADING.match(text):
                continue
            prev = [l for l in ls[:k] if column(l[2], colsplit) == column(x, colsplit)]
            if not prev:
                continue
            d = y0 - prev[-1][1]
            vals.append((d, i + 1, text[:52]))
    if not vals:
        print("  （未识别到标题行）")
        return
    ds = sorted(v for v, _, _ in vals)
    med = ds[len(ds) // 2]
    print("  共 %d 处；min %.1f  median %.1f  max %.1f pt" % (len(ds), ds[0], med, ds[-1]))
    print("  逐处：")
    for d, p, t in sorted(vals, key=lambda v: -v[0]):
        flag = "  <== 异常" if d > max(3 * med, med + 20) else ""
        print("    p%-3d %5.1f pt  %s%s" % (p, d, t, flag))
    print("  ⚠ 判定口径：同一文档里只有一处的间距显著大于其它（尤其 >3x 中位），")
    print("     就是浮动体造成的孤立空带，不是正常的标题间距。")


def report_floats(doc, pages, colsplit, textwidth=516.0, margin=8.0):
    """通栏与否看 caption 第一行是否"跨过栏间空档"。
    不要用块宽度判：短 caption（如 "TABLE I"）居中后块很窄。
    也不要只按首行 x 与页边的关系判：左栏单栏 caption 的首行 x 恰好等于页边，
    而通栏 caption 的第一行 x 取决于该行文字长度，两者都会骗人。
    可靠判据只有一个——单栏 caption 必然整体落在某一栏之内。"""
    print("\n=== 图/表落位（首行跨过栏间空档者即通栏）===")
    found = False
    for i in pages:
        for y0, _, x, text in lines_of(doc[i]):
            if not CAPTION.match(text):
                continue
            found = True
            # 该行的实际 x 范围
            xs = []
            for block in doc[i].get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    if abs(line["bbox"][1] - y0) < 0.5:
                        xs = [line["bbox"][0], line["bbox"][2]]
            x0, x1 = (xs if xs else (x, x))
            if x0 < colsplit - margin and x1 > colsplit + margin:
                kind, side = "通栏 figure*/table*", "跨栏"
            else:
                kind, side = "单栏", ("左栏" if x1 <= colsplit else "右栏")
            print("    p%-3d y=%6.1f  %-14s %-4s  x=%5.1f..%5.1f  %s"
                  % (i + 1, y0, kind, side, x0, x1, text[:44]))
    if not found:
        print("    （未发现图注）")


def report_refs(doc, pages):
    r"""只在 REFERENCES 标题之后统计。
    正文里换行后落在行首的 \cite 也形如 "[4], [7]"，若全文档扫描会误判成条目。"""
    print("\n=== 参考文献编号（只在 REFERENCES 之后统计）===")
    started = False
    per_page = {}
    for i in pages:
        for _, _, _, text in lines_of(doc[i]):
            if not started:
                started = bool(re.match(r"^REFERENCES\b", text))
                continue
            m = REFITEM.match(text)
            if m:
                per_page.setdefault(i + 1, []).append(int(m.group(1)))
    if not per_page:
        print("    （REFERENCES 之前没找到，或未发现 [n] 条目）")
        return
    allnums = []
    for p in sorted(per_page):
        nums = sorted(set(per_page[p]))
        allnums += nums
        print("    p%-3d 起始条目号 %s" % (p, nums))
    missing = [n for n in range(1, max(allnums) + 1) if n not in allnums]
    print("    合计 %d 条（最大编号 %d）%s"
          % (len(set(allnums)), max(allnums), "  ★缺号 %s" % missing if missing else "  编号连续"))
    pages_used = sorted(per_page)
    print("    分布：%s" % ("、".join("p%d" % p for p in pages_used)))


def main():
    ap = argparse.ArgumentParser(description="编译产物的版面取证（只读）")
    ap.add_argument("pdf")
    ap.add_argument("--top", type=float, default=TOP)
    ap.add_argument("--bottom", type=float, default=BOTTOM)
    ap.add_argument("--colsplit", type=float, default=COLSPLIT)
    ap.add_argument("--gap", type=float, default=18.0, help="多大算一个可疑空隙（pt）")
    ap.add_argument("--pages", default="", help="只分析这些页，逗号分隔，从 1 起")
    ap.add_argument("--verify", default="", help="检查 PDF 里是否含这个字符串（确认版本一致）")
    args = ap.parse_args()

    if not args.pdf:
        sys.exit("用法: python check_layout.py paper.pdf")
    try:
        doc = pymupdf.open(args.pdf)
    except Exception as e:  # 缺文件或损坏，给一行友好报错而非堆栈
        sys.exit("无法打开 %s: %s" % (args.pdf, e))
    pages = ([int(p) - 1 for p in args.pages.split(",") if p.strip()]
             if args.pages else list(range(doc.page_count)))

    print("文件: %s" % args.pdf)
    print("页数: %d   页面: %.0f x %.0f pt   版心 y: %.1f..%.1f"
          % (doc.page_count, doc[0].rect.width, doc[0].rect.height, args.top, args.bottom))
    if doc.page_count > len(pages):
        print("（本次只分析第 %s 页）" % ",".join(str(p + 1) for p in pages))

    report_columns(doc, pages, args.top, args.bottom, args.colsplit, args.gap)
    report_headings(doc, pages, args.colsplit)
    report_floats(doc, pages, args.colsplit)
    report_refs(doc, pages)

    hit = True
    if args.verify:
        hit = any(args.verify in p.get_text() for p in doc)
        print("\n=== 版本一致性 ===")
        print("  查找 %r : %s" % (args.verify, "命中 -> PDF 与当前源一致" if hit else "★未命中 -> PDF 可能是旧版"))
    doc.close()
    return 0 if hit else 1  # verify 未命中可作为构建闸门：产物不是当前版


if __name__ == "__main__":
    sys.exit(main())
