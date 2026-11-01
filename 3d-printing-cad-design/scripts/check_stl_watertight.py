# -*- coding: utf-8 -*-
"""
自动化 3D 打印 STL 模型水密性与几何尺寸质检脚本
使用方法: python check_stl_watertight.py <stl_folder_or_file>
"""
import os
import sys
import trimesh

def check_stl_file(file_path):
    filename = os.path.basename(file_path)
    try:
        mesh = trimesh.load(file_path)
    except Exception as e:
        print(f"[FAIL] {filename}: 无法读取 ({e})")
        return False
        
    is_wt = mesh.is_watertight
    is_empty = len(mesh.faces) == 0
    bounds = mesh.bounds
    dims = (bounds[1] - bounds[0]).round(2)
    
    status = "[PASS]" if is_wt and not is_empty else "[FAIL]"
    print(f"{status} {filename}")
    print(f"       水密流形: {is_wt} | 面数: {len(mesh.faces)} | 顶点数: {len(mesh.vertices)}")
    print(f"       包围尺寸 (X, Y, Z): {dims.tolist()} mm")
    print(f"       高程跨度 (Z_min, Z_max): [{bounds[0][2]:.2f}, {bounds[1][2]:.2f}] mm")
    
    if not is_wt:
        print(f"       [!] 警告: 该零件存在非闭合边或破面，3D 打印切片可能报错！")
        return False
    return True

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = [os.path.join(target, f) for f in os.listdir(target) if f.lower().endswith(".stl")]
    else:
        print(f"Target not found: {target}")
        sys.exit(1)
        
    print(f"=== 开始执行 STL 水密性与几何质检 (共 {len(files)} 个文件) ===")
    all_ok = True
    for f in sorted(files):
        if not check_stl_file(f):
            all_ok = False
            
    print("=" * 60)
    if all_ok:
        print("[SUCCESS] 全部 STL 模型 100% 封闭水密，完全符合 3D 打印切片标准！")
        sys.exit(0)
    else:
        print("[ERROR] 部分模型未通过水密性检测，请排查布尔运算或封顶操作！")
        sys.exit(1)

if __name__ == "__main__":
    main()
