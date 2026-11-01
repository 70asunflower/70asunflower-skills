#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""技能规范检查器。

    python scripts/lint_skills.py            # 只查 git 跟踪的自建技能
    python scripts/lint_skills.py --all      # 连第三方一起查
    python scripts/lint_skills.py layoutfix  # 只查一个
    python scripts/lint_skills.py --strict   # 有 warning 也返回非零

第三方技能（.gitignore 排除的）不该按本仓库规范要求，默认跳过。

检查项（全部可机械判定，不涉及内容质量）：

  E1  SKILL.md 存在
  E2  以 --- 开头的 YAML frontmatter，且有结束 ---
  E3  frontmatter 有 name，且与目录名一致
  E4  frontmatter 有 description，长度 80–600 字
  E5  有 scripts/ 目录时，SKILL.md 必须提到 `scripts/`
  E6  正文里 `scripts/…` `references/…` `templates/…` `assets/…` 等引用必须存在
  E7  SKILL.md 无 BOM
  W1  SKILL.md 超过 300 行（该考虑拆到 references/ 或 scripts/）
  W2  目录里有 __pycache__ / .DS_Store / node_modules 等垃圾
  W3  description 和正文都没有说明「何时用」，触发准确率会低
  W4  references/ 或 templates/ 里有文件，正文从没提过（agent 不知道它存在）
      （description 里写了 Triggers/触发词，或正文有「何时使用」段，都算合格）

退出码：0 无 error；1 有 error；--strict 下 warning 也算失败。
"""

import re
import subprocess
import sys
import pathlib

HUB = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {"scripts", "archive", "templates", ".git", ".github", "docs", "node_modules"}
MAX_LINES = 300
DESC_MIN, DESC_MAX = 80, 600
WHEN_RE = re.compile(r"何时使用|when to use|使用场景|触发条件|什么时候用", re.I)
# description 里带这些标记，等于已经写清楚了「何时用」
TRIGGER_RE = re.compile(r"trigger|触发|当用户|use (this|it)( skill)?\s+when|whenever|适用于|用于", re.I)
REF_RE = re.compile(r"`((?:scripts|references|templates|assets|examples|locales)/[^`\s]+)`")
JUNK = {"__pycache__", ".DS_Store", "node_modules", ".pytest_cache", ".venv", "Thumbs.db"}


def parse_frontmatter(text):
    """返回 (dict | None, 错误信息)。支持 | > 块标量与多行续行。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "E2 首行不是 ---"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, "E2 frontmatter 没有结束 ---"
    fm, key = {}, None
    for ln in lines[1:end]:
        if not ln.strip():
            continue
        if ln[:1] in (" ", "\t"):
            if key:
                fm[key] += "\n" + ln.strip()
            continue
        if ":" in ln:
            k, v = ln.split(":", 1)
            key = k.strip()
            v = v.strip()
            fm[key] = "" if v in ("|", ">", "|-", ">-", "|+", ">+") else v.strip('"').strip("'")
    return fm, None


def check_skill(d: pathlib.Path) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    sk = d / "SKILL.md"
    if not sk.is_file():
        return ["E1 没有 SKILL.md"], warns

    raw = sk.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        errs.append("E7 SKILL.md 带 BOM（严格 YAML 解析器会读不到 frontmatter）")
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")

    fm, err = parse_frontmatter(text)
    if err:
        errs.append(err)
        return errs, warns

    name = fm.get("name", "")
    if not name:
        errs.append("E3 frontmatter 缺 name")
    elif name != d.name:
        errs.append(f"E3 name={name} 与目录名 {d.name} 不一致")

    desc = fm.get("description", "")
    if not desc:
        errs.append("E4 frontmatter 缺 description")
    elif not (DESC_MIN <= len(desc) <= DESC_MAX):
        errs.append(f"E4 description {len(desc)} 字，应在 {DESC_MIN}–{DESC_MAX} 之间")

    if (d / "scripts").is_dir() and "scripts/" not in text:
        errs.append("E5 有 scripts/ 目录但正文从未提到 `scripts/`，agent 不会去用")

    for ref in sorted(set(REF_RE.findall(text))):
        if any(c in ref for c in "*<>…") or "..." in ref:
            continue                      # 省略号是行文占位，不是真路径
        if (d / ref).exists():
            continue
        if (HUB / ref).exists():
            continue                      # 引用仓库根的工具（如 scripts/skillsync.py）
        # .json 多半是用户自建的配置文件，缺失属于「尚未创建」而非断链
        if ref.endswith(".json"):
            warns.append(f"E6(降级) 引用的 `{ref}` 不存在——若是运行时配置可忽略")
            continue
        errs.append(f"E6 引用的 `{ref}` 不存在")

    n = len(text.splitlines())
    if n > MAX_LINES:
        warns.append(f"W1 {n} 行，超过 {MAX_LINES} 行，考虑拆到 references/ 或 scripts/")

    junk = [p.name for p in d.rglob("*") if p.name in JUNK]
    if junk:
        warns.append(f"W2 目录里有垃圾：{', '.join(sorted(set(junk))[:4])}")

    if not WHEN_RE.search(text) and not TRIGGER_RE.search(desc):
        warns.append("W3 description 和正文都没写「何时用」，触发准确率会低")

    # W4：只查 references/ 和 templates/，不查 scripts/。
    # 脚本可以是内部实现（被别的脚本调用，或只由某个 .cmd 间接调用），
    # 正文不提是正常的；但参考文档和模板写了没人读，就是白放。
    for sub in ("references", "templates"):
        d = d / sub
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.name.startswith("."):
                continue
            rel = str(f.relative_to(d.parent)).replace("\\", "/")
            if rel in text or f.name in text:
                continue
            warns.append(f"W4 `{rel}` 存在但正文没提，agent 不会去读")

    return errs, warns


def own_skills() -> set[str]:
    """自建技能目录名 = 已跟踪的 + 新建未跟踪但未被 gitignore 的。

    只取 tracked 的话，新建的技能在 git add 之前会被跳过——等于提交前查不到，
    提交后才发现不合规。第三方技能在 .gitignore 里，两个来源都不会带进来。
    """
    def names(args):
        try:
            out = subprocess.run(["git", *args, "--", "*/SKILL.md"],
                                 cwd=str(HUB), capture_output=True, text=True, timeout=60)
            return {line.split("/")[0] for line in out.stdout.splitlines() if "/" in line}
        except (OSError, subprocess.SubprocessError):
            return set()

    return names(["ls-files"]) | names(["ls-files", "--others", "--exclude-standard"])


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    strict = "--strict" in argv
    check_all = "--all" in argv

    if not HUB.is_dir():
        print(f"找不到主库：{HUB}", file=sys.stderr)
        return 2

    dirs = sorted(
        d for d in HUB.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in SKIP_DIRS
    )
    if not check_all and not args:
        keep = own_skills()
        if keep:
            dirs = [d for d in dirs if d.name in keep]

    if args:
        want = set(args)
        dirs = [d for d in dirs if d.name in want]
        missing = want - {d.name for d in dirs}
        for m in sorted(missing):
            print(f"找不到技能：{m}", file=sys.stderr)

    total_e = total_w = 0
    bad = []
    for d in dirs:
        e, w = check_skill(d)
        total_e += len(e)
        total_w += len(w)
        if e or w:
            bad.append((d.name, e, w))

    for name, e, w in bad:
        print(name)
        for x in e:
            print("  ✗ " + x)
        for x in w:
            print("  · " + x)

    print()
    print(f"检查 {len(dirs)} 个技能：{total_e} 个 error，{total_w} 个 warning")
    if total_e:
        return 1
    if strict and total_w:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
