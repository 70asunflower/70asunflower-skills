# -*- coding: utf-8 -*-
"""
STEP/IGES -> GLB 转换（cascadio / OpenCASCADE 并行网格化）
用法: python step_to_glb.py <input.step> [output.glb] [tol_linear_mm]

实战要点:
  - OCCT 无法写非 ASCII 输出路径（Windows 中文路径必报 "Cannot open output file"，
    且报错发生在整场转换结束、全部工时已耗尽时）。本脚本先输出到 ASCII 临时文件，
    成功后再 shutil.move 回目标位置（Python 自己move不受此限制）。
  - tol_linear 默认 0.1mm：板卡/机构级预览足够精细；251MB STEP 实测约 205s 转 44MB GLB。
  - include_materials=True 保留零件颜色（外观色随 STEP 走）。
"""
import os
import shutil
import sys
import tempfile
import time


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = os.path.abspath(sys.argv[1])
    dst = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".glb"
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1

    if not os.path.exists(src):
        print(f"[FAIL] 输入不存在: {src}")
        return 2

    from cascadio import step_to_glb  # miniconda 环境

    # ASCII 临时输出路径（仅文件名部分也需 ASCII）
    tmp = os.path.join(tempfile.gettempdir(), f"cascadio_{os.getpid()}.glb")
    if os.path.exists(tmp):
        os.remove(tmp)

    print(f"[RUN ] {os.path.getsize(src) / 1e6:.0f} MB STEP -> GLB (tol_linear={tol}mm, 并行)")
    t0 = time.time()
    rc = step_to_glb(src, tmp, tol_linear=tol, tol_angular=0.5, include_materials=True)
    el = time.time() - t0

    if rc != 0 or not os.path.exists(tmp):
        print(f"[FAIL] rc={rc} elapsed={el:.0f}s（若为 Cannot open output file，多为非 ASCII 路径）")
        return 1

    shutil.move(tmp, dst)
    print(f"[OK  ] rc=0 elapsed={el:.0f}s -> {dst}")
    print(f"[OK  ] GLB 大小: {os.path.getsize(dst) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
