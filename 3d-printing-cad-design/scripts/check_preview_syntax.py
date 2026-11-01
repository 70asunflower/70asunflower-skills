# -*- coding: utf-8 -*-
"""
自动化检查 3D 预览 HTML 文件中的内联 JavaScript
用法: python check_preview_syntax.py <html_file>

v1.1 (2026-10-22 实战修订):
  - 带属性的 <script data-lib="..."> 库块与 <script type="text/plain"> 数据块自动跳过
    （旧版对内嵌 three.min.js 里的 isNaN 会误报 NaN，对压缩库的括号/正则误判）
  - 有 node 时对每个应用脚本块跑 node --check 强校验（比括号配对可靠得多）
  - 无 node 时退化为括号配对栈检查（仅应用脚本块）
  - NaN 检查仅针对应用脚本块；应用脚本一律写裸 <script>，库与数据块必须带属性
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPT_RE = re.compile(r"<script(\s[^>]*)?>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def check_html_syntax(file_path):
    print(f"Checking inline JS in {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = []  # (kind, index, code)  kind: "app" | "skip"
    for m in SCRIPT_RE.finditer(content):
        attrs = (m.group(1) or "").strip()
        code = m.group(2)
        # 裸 <script> = 应用脚本；带任何属性 = 库/数据块（约定：库用 data-lib，数据用 type="text/plain"）
        blocks.append(("skip" if attrs else "app", len(blocks), code))

    app_blocks = [b for b in blocks if b[0] == "app"]
    skipped = len(blocks) - len(app_blocks)
    print(f"  共 {len(blocks)} 个内联脚本块: {len(app_blocks)} 个应用脚本待检, {skipped} 个库/数据块跳过")
    if not app_blocks:
        print("  [WARN] 未找到应用脚本块（<script> 必须不带属性才会被检查）")
        return True

    node = shutil.which("node")
    all_passed = True

    for kind, idx, code in app_blocks:
        label = f"Script {idx} ({len(code) / 1024:.0f} KB)"
        if not code.strip():
            print(f"  [SKIP {label}] 空块")
            continue

        # 1) node --check 强校验（可用时）
        if node:
            tmp = os.path.join(tempfile.gettempdir(), f"syntax_check_{os.getpid()}_{idx}.js")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(code)
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            os.remove(tmp)
            if r.returncode == 0:
                print(f"  [PASS {label}] node --check OK")
                continue
            all_passed = False
            print(f"  [FAIL {label}] node --check 语法错误:")
            print("    " + (r.stderr or r.stdout)[:1500].replace("\n", "\n    "))
            continue

        # 2) 无 node 时退化为括号配对栈检查
        stack = []
        pairs = {")": "(", "]": "[", "}": "{"}
        in_s = in_d = in_b = False
        escaped = False
        ok = True
        for i, ch in enumerate(code):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == "'" and not in_d and not in_b:
                in_s = not in_s
                continue
            if ch == '"' and not in_s and not in_b:
                in_d = not in_d
                continue
            if ch == "`" and not in_s and not in_d:
                in_b = not in_b
                continue
            if in_s or in_d or in_b:
                continue
            if ch in "({[":
                stack.append((ch, i))
            elif ch in ")}]":
                if not stack or pairs[ch] != stack[-1][0]:
                    print(f"  [FAIL {label}] 括号不匹配 '{ch}' @ char {i}")
                    ok = False
                    break
                stack.pop()
        if ok and stack:
            print(f"  [FAIL {label}] 未闭合 '{stack[-1][0]}' @ char {stack[-1][1]}")
            ok = False
        if ok:
            print(f"  [PASS {label}] 括号配对平衡（建议安装 node 以启用强校验）")
        else:
            all_passed = False

    # NaN 检查：仅应用脚本块（库代码里的 isNaN 不算）
    for kind, idx, code in app_blocks:
        if re.search(r"\bNaN\b", code):
            print(f"  [FAIL Script {idx}] 应用脚本/数据中出现 NaN！")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "preview.html"
    ok = check_html_syntax(target)
    print("[SUCCESS] 语法检查全部通过" if ok else "[FAILURE] 存在语法问题")
    sys.exit(0 if ok else 1)
