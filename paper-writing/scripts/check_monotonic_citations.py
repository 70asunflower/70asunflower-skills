#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_monotonic_citations.py
Tool to audit LaTeX and Markdown manuscripts for strict monotonic citation order.
Ensures:
1. Every reference [1]..[N] appears in strictly increasing order on first mention.
2. No orphan bibliography items (all \bibitem or reference list items are cited).
3. No missing or skipped citation keys.
"""

import re
import sys
import argparse

def check_latex(tex_path):
    with open(tex_path, 'r', encoding='utf-8') as f:
        text = f.read()

    bib_pos = text.find(r'\begin{thebibliography}')
    if bib_pos == -1:
        print(f"[!] Warning: No \\begin{{thebibliography}} found in {tex_path}")
        body = text
        bib_items = []
    else:
        body = text[:bib_pos]
        bib_text = text[bib_pos:]
        bib_items = re.findall(r'\\bibitem\{([^}]+)\}', bib_text)

    matches = []
    for m in re.finditer(r'\\cite\{([^}]+)\}', body):
        for k in m.group(1).split(','):
            k = k.strip()
            matches.append((m.start(), k))

    first_seen = {}
    for pos, k in matches:
        if k not in first_seen:
            first_seen[k] = pos

    sorted_keys = sorted(first_seen.keys(), key=lambda x: first_seen[x])
    
    # Try parsing b1, b2, ... or digits
    parsed_nums = []
    key_to_num = {}
    for k in sorted_keys:
        m = re.search(r'\d+', k)
        if m:
            val = int(m.group(0))
            parsed_nums.append(val)
            key_to_num[k] = val
        else:
            parsed_nums.append(k)

    expected = list(range(1, len(parsed_nums) + 1))
    is_strictly_monotonic = (parsed_nums == expected)

    print(f"=== LaTeX Citation Audit: {tex_path} ===")
    print(f"Total in-text citation calls: {len(matches)}")
    print(f"Unique citation keys: {len(sorted_keys)}")
    print(f"Total bibliography items: {len(bib_items)}")
    print(f"First-appearance sequence: {parsed_nums}")
    print(f"Strict monotonic order [1..{len(parsed_nums)}]: {is_strictly_monotonic}")

    # Check for missing bibitems
    uncited_bib = [b for b in bib_items if b not in first_seen]
    if uncited_bib:
        print(f"[ERROR] Unreferenced bibliography items (orphans): {uncited_bib}")
    else:
        print("[OK] Zero orphan bibliography items.")

    # Check for citations not in bibliography
    if bib_items:
        unresolved_cites = [k for k in first_seen if k not in bib_items]
        if unresolved_cites:
            print(f"[ERROR] In-text citations missing from \\bibitem: {unresolved_cites}")
        else:
            print("[OK] All in-text citations exist in bibliography.")

    if not is_strictly_monotonic:
        print("[ERROR] Citation order violation! Out-of-order details:")
        for idx, (k, num) in enumerate(zip(sorted_keys, parsed_nums)):
            expected_num = idx + 1
            if num != expected_num:
                print(f"  Slot #{expected_num}: found key '{k}' (index {num})")
    else:
        print("[SUCCESS] All citations satisfy strict monotonic order!")

    return is_strictly_monotonic and (len(uncited_bib) == 0)

def check_markdown(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        text = f.read()

    bib_pos = text.find('## References')
    if bib_pos == -1:
        bib_pos = text.find('## 参考文献')
    body = text[:bib_pos] if bib_pos != -1 else text
    bib_text = text[bib_pos:] if bib_pos != -1 else ""

    matches = list(re.finditer(r'\[(\d+(?:[–\-,]\s*\d+)*)\]', body))
    first_seen = {}
    for m in matches:
        for part in re.split(r'[,–\-]', m.group(1)):
            part = part.strip()
            if part.isdigit():
                val = int(part)
                if val not in first_seen:
                    first_seen[val] = m.start()

    sorted_nums = sorted(first_seen.keys(), key=lambda x: first_seen[x])
    bib_items = [int(x) for x in re.findall(r'\[(\d+)\]\s+[A-Z\u4e00-\u9fa5]', bib_text)]

    expected = list(range(1, len(sorted_nums) + 1))
    is_strictly_monotonic = (sorted_nums == expected)

    print(f"=== Markdown Citation Audit: {md_path} ===")
    print(f"Unique cited numbers: {len(sorted_nums)}")
    print(f"Total reference items in list: {len(bib_items)}")
    print(f"First-appearance sequence: {sorted_nums}")
    print(f"Strict monotonic order [1..{len(sorted_nums)}]: {is_strictly_monotonic}")

    uncited = [b for b in bib_items if b not in first_seen]
    if uncited:
        print(f"[ERROR] Unreferenced reference items: {uncited}")
    else:
        print("[OK] Zero orphan reference items.")

    return is_strictly_monotonic

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Check monotonic citation order in LaTeX/Markdown manuscripts.")
    parser.add_argument("files", nargs="*", help="Files to check (.tex or .md)")
    parser.add_argument("-t", "--tex", nargs="*", default=[], help="LaTeX file(s) to check")
    parser.add_argument("-c", "--checklist", "--md", nargs="*", default=[], help="Markdown file(s) to check")
    args = parser.parse_args()

    target_files = list(args.files) + list(args.tex) + list(args.checklist)
    if not target_files:
        parser.print_help()
        sys.exit(1)

    all_pass = True
    for f in target_files:
        if f.endswith('.tex'):
            res = check_latex(f)
        elif f.endswith('.md'):
            res = check_markdown(f)
        else:
            print(f"Skipping unsupported file extension: {f}")
            continue
        all_pass = all_pass and res
        print("-" * 50)

    sys.exit(0 if all_pass else 1)
