#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_mirror_and_pack.py
Automates dual-directory hot mirroring and Overleaf-ready LaTeX submission packaging.
"""

import os
import shutil
import zipfile
import argparse

def sync_and_pack(src_dir, mirror_dir, files_to_sync, files_to_pack, zip_name='manuscript_latex.zip'):
    print(f"[*] Source directory: {src_dir}")
    print(f"[*] Mirror directory: {mirror_dir}")
    
    # 1. Hot Mirroring
    if os.path.exists(mirror_dir):
        for item in files_to_sync:
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(mirror_dir, item)
            if os.path.exists(src_path):
                dst_parent = os.path.dirname(dst_path)
                if dst_parent and not os.path.exists(dst_parent):
                    os.makedirs(dst_parent, exist_ok=True)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f"  [+] Synced file: {item} -> {dst_path}")
                elif os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                    print(f"  [+] Synced dir:  {item} -> {dst_path}")
    else:
        print(f"[!] Warning: Mirror directory does not exist: {mirror_dir}")

    # 2. Package Zip
    for target in [src_dir, mirror_dir]:
        if os.path.exists(target):
            out_zip = os.path.join(target, zip_name)
            with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files_to_pack:
                    p = os.path.join(src_dir, f)
                    if os.path.exists(p):
                        zf.write(p, arcname=f)
                        print(f"  [ZIP] Added {f} to {out_zip}")
                    else:
                        print(f"  [!] Missing file to pack: {p}")
            print(f"[SUCCESS] Packaged: {out_zip} ({os.path.getsize(out_zip)} bytes)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Sync files to mirror directory and package manuscript zip.")
    parser.add_argument("--src", default=".", help="Source working directory")
    parser.add_argument("--mirror", required=True, help="Target mirror directory")
    parser.add_argument("--zip-name", default="manuscript_latex.zip", help="Output zip filename")
    args = parser.parse_args()

    default_sync = [
        'paper_satellite2026.tex',
        'paper_satellite2026_zh.tex',
        '论文初稿_IEEE_Satellite2026_中文.md',
        '_文献回填清单.md',
        'figures'
    ]

    default_pack = [
        'paper_satellite2026.tex',
        'paper_satellite2026_zh.tex',
        'figures/fig1_composite_setup.pdf',
        'figures/fig3_meter_timeline.pdf',
        'figures/fig4_elimination_tree.pdf',
        'figures/fig1_composite_setup.png',
        'figures/fig3_meter_timeline.png',
        'figures/fig4_elimination_tree.png'
    ]

    sync_and_pack(args.src, args.mirror, default_sync, default_pack, args.zip_name)
