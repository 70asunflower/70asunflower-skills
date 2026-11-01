#!/usr/bin/env python3
"""把「新建项目必须走 project-init」这条规则写进各 agent 的全局记忆（幂等）。

规则正文的唯一来源是同目录上级的 assets/global-rule.md；本脚本只负责把它
按标记区块写进每个 agent 的全局指令/记忆文件，已有同内容则跳过，内容变了则就地替换。

用法:
    python ensure_rule.py            # 只检查，报告哪些 agent 已登记、哪些没登记
    python ensure_rule.py --apply    # 写入/刷新标记区块
    python ensure_rule.py --apply --only claude,codex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_DIR = Path(__file__).resolve().parent.parent
RULE_SRC = SKILL_DIR / "assets" / "global-rule.md"

BEGIN = "<!-- BEGIN project-init-rule -->"
END = "<!-- END project-init-rule -->"

HOME = Path.home()


def targets() -> list[tuple[str, Path]]:
    """各 agent 的全局指令/记忆文件。只列存在的 agent 目录，避免凭空造文件。"""
    out: list[tuple[str, Path]] = []
    cands = [
        ("claude", HOME / ".claude", "CLAUDE.md"),
        ("codex", HOME / ".codex", "AGENTS.md"),
        ("zcode", HOME / ".zcode", "AGENTS.md"),
        ("gemini", HOME / ".gemini", "GEMINI.md"),
        ("workbuddy", HOME / ".workbuddy", "MEMORY.md"),
    ]
    for name, base, fn in cands:
        if base.is_dir():
            out.append((name, base / fn))
    # WorkBuddy 海外版：用户级记忆在 ~/.workbuddy-ai/user-<uuid>-personal/MEMORY.md
    for p in sorted((HOME / ".workbuddy-ai").glob("user-*/MEMORY.md")):
        out.append(("workbuddy-ai", p))
    return out


def rule_block() -> str:
    body = RULE_SRC.read_text(encoding="utf-8").strip() if RULE_SRC.exists() else ""
    if not body:
        raise SystemExit(f"[错误] 规则源文件缺失或为空: {RULE_SRC}")
    return f"{BEGIN}\n{body}\n{END}\n"


def current_block(text: str) -> str | None:
    i, j = text.find(BEGIN), text.find(END)
    if i < 0 or j < 0:
        return None
    return text[i:j + len(END)] + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="把新建项目规则写进各 agent 全局记忆（幂等）")
    ap.add_argument("--apply", action="store_true", help="实际写入（默认只检查）")
    ap.add_argument("--only", default="", help="只处理指定 agent，逗号分隔")
    args = ap.parse_args()

    block = rule_block()
    want = {a.strip() for a in args.only.split(",") if a.strip()}
    rows = [(n, p) for n, p in targets() if not want or n in want]
    if not rows:
        print("[错误] 没找到任何 agent 全局文件（--only 过滤后为空）")
        return 1

    added, updated, ok = [], [], []
    for name, path in rows:
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        cur = current_block(text)
        if cur is not None and cur.strip() == block.strip():
            ok.append(name)
            continue
        if not args.apply:
            (updated if cur is not None else added).append(name)
            continue
        if cur is not None:
            new = text[:text.find(BEGIN)] + block + text[text.find(END) + len(END):].lstrip("\n")
            action = "刷新"
        else:
            sep = "" if not text else ("\n" if text.endswith("\n") else "\n\n")
            new = text + sep + ("\n" if text.strip() else "") + block
            action = "写入"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8", newline="\n")
        print(f"  [{action}] {name}: {path}")
        (updated if cur is not None else added).append(name)

    if args.apply:
        print(f"\n完成：新写入 {len(added)} 个、刷新 {len(updated)} 个、已是最新 {len(ok)} 个")
    else:
        print(f"检查：待写入 {len(added)} 个（{', '.join(added) or '无'}）、"
              f"待刷新 {len(updated)} 个（{', '.join(updated) or '无'}）、已登记 {len(ok)} 个（{', '.join(ok) or '无'}）")
        if added or updated:
            print("加 --apply 写入。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
