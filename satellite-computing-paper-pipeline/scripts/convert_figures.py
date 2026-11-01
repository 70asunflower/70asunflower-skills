#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_figures.py
Converts vector PDF figures into 300 DPI high-resolution PNG assets for dual-use (LaTeX + Markdown/Web).
"""

import os
import sys
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[ERROR] PyMuPDF (fitz) is not installed. Please run `pip install pymupdf`.")
    sys.exit(1)

def convert_pdf_to_png(pdf_path, png_path=None, dpi=300):
    if not os.path.exists(pdf_path):
        print(f"[ERROR] Source PDF not found: {pdf_path}")
        return False

    if png_path is None:
        png_path = os.path.splitext(pdf_path)[0] + ".png"

    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    pix.save(png_path)
    print(f"[OK] Converted: {pdf_path} ({page.rect.width:.1f}x{page.rect.height:.1f} pt) -> {png_path} ({pix.width}x{pix.height} px @ {dpi} DPI)")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Render PDF vector figure to 300 DPI PNG.")
    parser.add_argument("pdf_files", nargs="*", default=[], help="Input PDF file paths")
    parser.add_argument("-d", "--dir", "--input-dir", default=None, help="Directory containing PDF figures to convert")
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI resolution (default: 300)")
    args = parser.parse_args()

    files = list(args.pdf_files)
    if args.dir and os.path.exists(args.dir):
        for f in os.listdir(args.dir):
            if f.lower().endswith('.pdf'):
                files.append(os.path.join(args.dir, f))

    if not files:
        parser.print_help()
        sys.exit(1)

    for pdf in files:
        convert_pdf_to_png(pdf, dpi=args.dpi)
