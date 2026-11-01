#!/usr/bin/env python3
"""project-init: 给项目立底线（git + 规范 + 项目记忆/日志），结构按 profile 声明，不搞一刀切。

用法:
    python init_project.py [目标目录] [选项]                建立底线（默认 profile=minimal）
    python init_project.py [目标目录] --adopt [--apply]     接管已有项目：补底线 + 输出/执行迁移建议
    python init_project.py [目标目录] --upgrade             规范模板升级：打印 diff，新模板写入 tmp/

选项:
    --profile NAME  minimal(默认) | docs | software   目录结构预设
    --dirs "a:用途,b:用途"                            追加自定义顶层目录（可反复给）
    --type DESC     项目类型：软件 | 文档 | 混合（默认由 profile 推断，含「软件」才启用开发流程）
    --model ID      当前 agent 的模型官方名，写入首条日志与首次提交署名（强烈建议传）
    --name NAME     项目名，默认取目录名
    --stack DESC    技术栈，写入 AGENTS.md
    --for SPEC      agent 入口：none(默认，按需由各 agent 自建) | all | claude,gemini,...
    --force         覆盖已存在的规范文件
    --no-git        跳过 git init（违反底线，仅极特殊场景）
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VERSION = "2.1.0"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "AGENTS.template.md"
SOFTWARE_TPL_DIR = SKILL_DIR / "assets" / "software"
SECTION_SOFTWARE = SKILL_DIR / "assets" / "sections" / "software.md"
SECTION_PLAIN = SKILL_DIR / "assets" / "sections" / "plain.md"

# 结构预设：只声明「项目实际有什么」，不假装所有项目都长一样
PROFILES: dict[str, dict] = {
    "minimal": {"type": "文档", "dirs": []},
    "docs": {"type": "文档", "dirs": [
        ("docs/", "正式文档与交付物", "是"),
        ("tmp/", "临时区：一次性脚本、草稿、原始数据、中间输出", "否"),
    ]},
    "software": {"type": "软件", "dirs": [
        ("docs/", "正式文档：顶层文档、功能文档、交付快照", "是"),
        ("code/", "项目正式代码与测试", "是"),
        ("tmp/", "临时区：一次性脚本、草稿、原始数据、中间输出", "否"),
    ]},
}
MEMORY_ROW = ("memory/", "项目记忆与日志：MEMORY.md + 当日日志", "是")

# 各 agent 入口（默认不预建；AGENTS.md 第 7 节给了对照表，agent 自己按需建）
POINTER_BODY = (
    "# 项目规范入口\n\n"
    "开始本项目任何工作前，先完整阅读项目根目录的 `AGENTS.md`——"
    "它是本项目全部协作规范的唯一来源，必须严格遵守。\n"
)
ADAPTERS: dict[str, dict[str, str]] = {
    "claude": {"path": "CLAUDE.md",
               "body": "# 项目规范入口\n\n@AGENTS.md\n\n> 上一行是 Claude Code 的导入语法。若未生效，请完整阅读 AGENTS.md 并严格遵守。\n"},
    "gemini": {"path": "GEMINI.md", "body": POINTER_BODY},
    "qwen": {"path": "QWEN.md", "body": POINTER_BODY},
    "cursor": {"path": ".cursor/rules/project-rules.mdc",
               "body": "---\nalwaysApply: true\n---\n\n" + POINTER_BODY},
    "windsurf": {"path": ".windsurfrules", "body": POINTER_BODY},
    "cline": {"path": ".clinerules", "body": POINTER_BODY},
    "copilot": {"path": ".github/copilot-instructions.md", "body": POINTER_BODY},
}

# --adopt 迁移建议的启发式表
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git", ".idea", ".vscode"}
KEEP_ROOT = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md", "MEMORY.md", "README.md",
    ".gitignore", ".gitattributes", ".editorconfig", ".env", ".env.example",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "requirements-dev.txt",
    "poetry.lock", "uv.lock", "Pipfile", "Pipfile.lock", "environment.yml", "MANIFEST.in",
}
KEEP_PREFIX = ("README", "LICENSE", "CHANGELOG")
DOC_EXTS = {".md", ".docx", ".doc", ".pdf", ".pptx", ".ppt", ".xlsx", ".xls", ".epub", ".tex", ".bib", ".txt"}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cc",
             ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".lua", ".r",
             ".sh", ".ps1", ".bat", ".sql", ".ipynb", ".vue", ".dart", ".m"}
TMP_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".csv", ".tsv", ".log", ".parquet",
            ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".mp4", ".mov", ".wav", ".mp3"}

README_TPL = """# {name}

> 待补充：一句话说明本项目是什么、给谁用。

## 结构

见 [AGENTS.md](AGENTS.md) 第 1 节（结构的唯一来源，改结构就改那张表）。

## 协作

任何 AI Agent 与协作者开始工作前，必须阅读 [AGENTS.md](AGENTS.md) 并遵守。
项目长期记忆在 `memory/MEMORY.md`；每个正式文件旁边都有一份同名 `.log.md` 记录修改人与模型。
"""

MEMORY_TPL = """# {name} — 项目记忆

> 长期记忆：项目是什么、关键决策、约定与坑。日常改动记在各文件的 `.log.md`，不要写这里。
> 过时的条目直接删掉，别标记作废——历史在 git 里。

## 项目是什么

（待补充：给谁用、解决什么问题、边界是什么。）

## 关键决策

| 日期 | 决策 | 理由 | 模型 |
|------|------|------|------|
| {today} | 采用 `{profile}` 结构预设 | 项目初始化时的判断，后续可改本节与 AGENTS.md 结构表 | {model} |

## 约定与坑

（踩过的坑、必须遵守的隐式约定。没有就留空。）
"""


def gitignore_text(untracked: list[str]) -> str:
    head = ""
    if untracked:
        head = "# 临时区不入库（随时可清空）\n" + "".join(f"{d}/\n" for d in untracked)
    return head + """# 操作系统垃圾
Thumbs.db
desktop.ini
.DS_Store
# Office 锁文件
~$*
# 常见运行产物
__pycache__/
*.pyc
.venv/
node_modules/
dist/
build/
"""


# 这些目录默认视为临时区（入库=否，并写进 .gitignore）
UNTRACKED_DIRS = {"tmp", "temp", "inbox"}


def parse_structure_rows(text: str) -> list[tuple[str, str, str]] | None:
    """从 AGENTS.md 的 structure 区块解析结构表；无该区块返回 None（1.x 老规范）。"""
    m = re.search(r"<!--\s*structure:begin\s*-->(.*?)<!--\s*structure:end\s*-->", text, re.S)
    if not m:
        return None
    rows: list[tuple[str, str, str]] = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        path = cells[0].strip("`").strip()
        if not path or path in ("路径", "位置"):
            continue
        rows.append((path, cells[1], cells[2]))
    return rows


def render_template(project_name: str, ptype: str, stack: str,
                    rows: list[tuple[str, str, str]]) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else \
        "# 项目协作规范\n\n（模板缺失，请补全 assets/AGENTS.template.md）\n"
    table = "\n".join(f"| `{p}` | {u} | {t} |" for p, u, t in rows)
    sec = SECTION_SOFTWARE if "软件" in ptype else SECTION_PLAIN
    software_section = sec.read_text(encoding="utf-8").rstrip() if sec.exists() else "## 5. 开发流程\n\n（缺失）\n"
    return (tpl.replace("{{PROJECT_NAME}}", project_name)
               .replace("{{PROJECT_TYPE}}", ptype)
               .replace("{{TECH_STACK}}", stack)
               .replace("{{VERSION}}", VERSION)
               .replace("{{STRUCTURE_ROWS}}", table)
               .replace("{{SOFTWARE_SECTION}}", software_section))


def run_git(repo: Path, *args: str, author: str | None = None) -> tuple[int, str]:
    cmd = ["git"] + ([f"-c", f"user.name={author}"] if author else []) + list(args)
    p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout + p.stderr).strip()


def iter_entries(base: Path):
    """遍历目录产出文件（跳过 SKIP_DIRS 与隐藏目录）。"""
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield Path(dirpath) / fn


def adopt_plan(root: Path, rows: list[tuple[str, str, str]]) -> list[dict]:
    """对根目录散落文件给出迁移建议：落到结构表声明的目录，或标「需人工判断」。"""
    dirs = [p.rstrip("/") for p, _, _ in rows if p.endswith("/")]
    doc_dir = next((d for d in dirs if d in ("docs", "doc", "文档")), None)
    code_dir = next((d for d in dirs if d in ("code", "src")), None)
    tmp_dir = next((d for d in dirs if d in ("tmp", "temp")), None)
    plan: list[dict] = []
    for entry in sorted(root.iterdir()):
        nm = entry.name
        if entry.is_dir():
            if nm in dirs or nm.startswith(".") or nm in SKIP_DIRS:
                continue
            n = sum(1 for _ in iter_entries(entry))
            plan.append({"path": nm + "/", "dest": "?", "reason": f"未知目录（含 {n} 个文件），归属需人工判断"})
            continue
        if nm.startswith(".") or nm in KEEP_ROOT or nm.startswith(KEEP_PREFIX):
            continue
        ext = entry.suffix.lower()
        if ext in DOC_EXTS and doc_dir:
            plan.append({"path": nm, "dest": doc_dir + "/", "reason": "文档类扩展名"})
        elif ext in CODE_EXTS and code_dir:
            plan.append({"path": nm, "dest": code_dir + "/", "reason": "代码类扩展名"})
        elif ext in TMP_EXTS and tmp_dir:
            plan.append({"path": nm, "dest": tmp_dir + "/", "reason": "数据/媒体/临时产物"})
        else:
            plan.append({"path": nm, "dest": "?", "reason": "无法判断（或结构表未声明对应目录），需人工分类"})
    return plan


def apply_plan(root: Path, plan: list[dict]) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    problems: list[str] = []
    for item in plan:
        if item["dest"] == "?":
            continue
        src = root / item["path"]
        if not src.is_file():
            continue
        dest_dir = root / item["dest"]
        dest_dir.mkdir(exist_ok=True)
        target = dest_dir / src.name
        if target.exists():
            problems.append(f"目标已存在，跳过: {item['dest']}{src.name}")
            continue
        if (root / ".git").is_dir():
            rc, _ = run_git(root, "mv", str(src), str(target))
            if rc == 0:
                actions.append(f"{src.name} -> {item['dest']}")
                continue
        shutil.move(str(src), str(target))
        actions.append(f"{src.name} -> {item['dest']}")
    return actions, problems


def print_adopt_report(root: Path, plan: list[dict], applied: bool) -> None:
    print("\n=== 接管分析 ===")
    n = 0
    for it in plan:
        label = "需人工判断" if it["dest"] == "?" else f"建议 {it['dest']}"
        print(f"  {label:12s} {it['path']:42s} {it['reason']}")
        n += 1
    if n == 0:
        print("  未发现需要迁移的散落文件")
    if applied:
        actions, problems = apply_plan(root, plan)
        print(f"\n=== 已移动 {len(actions)} 项 ===")
        for a in actions:
            print("  " + a)
        for p in problems:
            print("  [跳过] " + p)
        print("提醒: 移动后 git add -A 提交，并在当日日志记一笔迁移。")
    else:
        print("\n以上仅为建议，未移动任何文件。确认后加 --apply 执行（只动结构表声明过的目录，「需人工判断」项不动）。")


def do_upgrade(root: Path, model: str) -> int:
    agents = root / "AGENTS.md"
    if not agents.exists():
        print(f"[升级] {root} 下没有 AGENTS.md，无规范可升级（如需初始化请去掉 --upgrade）")
        return 1
    cur = agents.read_text(encoding="utf-8", errors="replace")

    def field(pat: str, default: str) -> str:
        m = re.search(pat, cur, re.M)
        v = m.group(1).strip() if m else ""
        return v if v and not v.startswith("（") else default

    name = field(r"^-\s*项目名称[：:]\s*(.+)$", root.name)
    stack = field(r"^-\s*技术栈[：:]\s*(.+)$", "（未填写；可编辑本行或用 --stack 指定）")
    ptype = field(r"^-\s*项目类型[：:]\s*(.+)$", "")
    mver = re.search(r"规范版本[：:]\s*(\S+)", cur)
    curver = mver.group(1) if mver else "未知"

    rows = parse_structure_rows(cur)
    if rows is None:  # 1.x：按实际存在的经典目录推断
        rows = [MEMORY_ROW]
        for d, u, t in PROFILES["software"]["dirs"]:
            if (root / d.rstrip("/")).is_dir():
                rows.append((d, u, t))
        if not ptype:
            ptype = "软件"
    if not ptype:
        ptype = "软件" if any(p.startswith(("code/", "src/")) for p, _, _ in rows) else "文档"

    new = render_template(name, ptype, stack, rows)
    if cur == new:
        print(f"[升级] 已是最新规范版本 {VERSION}，无需操作")
        return 0

    diff = list(difflib.unified_diff(cur.splitlines(), new.splitlines(),
                                     fromfile=f"AGENTS.md（当前 {curver}）",
                                     tofile=f"AGENTS.md（新模板 {VERSION}）", lineterm=""))
    print("\n".join(diff[:200]))
    if len(diff) > 200:
        print(f"…（diff 共 {len(diff)} 行，已截断，完整新模板见 tmp/AGENTS.new.md）")
    out = root / "tmp" / "AGENTS.new.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(new, encoding="utf-8", newline="\n")
    print(f"\n[升级] 当前版本 {curver} → 新模板 {VERSION}")
    print(f"[升级] 新模板已写入 {out.relative_to(root).as_posix()}；逐段核对后手动合并到 AGENTS.md"
          f"（规范文件修改须经所有者确认），合并后删除该临时文件并提交。")
    if curver != "未知" and not curver.startswith(VERSION[:2]):
        print("[升级] 要点：结构表取代固定的 docs/code/tmp；新增 memory/MEMORY.md 项目记忆；"
              "每个正式文件必须配同名 .log.md 且条目带「模型：」；agent 入口改为按需自建。"
              "合并后用 check_project.py --fix 补建缺失的日志与记忆文件。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="项目初始化/接管/升级：立底线（git + 规范 + 记忆日志），结构按 profile 声明")
    ap.add_argument("target", nargs="?", default=".", help="目标项目目录，默认当前目录")
    ap.add_argument("--profile", default=None, choices=sorted(PROFILES), help="结构预设（默认 minimal；--adopt 时默认 software）")
    ap.add_argument("--dirs", action="append", default=[], metavar="NAME[:用途]",
                    help="追加自定义顶层目录，可反复给，如 --dirs 'assets:图片素材'")
    ap.add_argument("--type", dest="ptype", default=None, help="项目类型：软件 | 文档 | 混合")
    ap.add_argument("--model", default=None, help="当前 agent 的模型官方名，写入首条日志与首次提交署名")
    ap.add_argument("--name", default=None, help="项目名，默认取目录名")
    ap.add_argument("--stack", default=None, help="技术栈描述，写入 AGENTS.md")
    ap.add_argument("--for", dest="agents", default="none",
                    help="none(默认，由各 agent 按需自建) | all | claude,gemini,qwen,cursor,windsurf,cline,copilot")
    ap.add_argument("--adopt", action="store_true", help="接管已有项目：补底线并输出迁移建议")
    ap.add_argument("--apply", action="store_true", help="与 --adopt 连用：执行无争议的文件移动")
    ap.add_argument("--upgrade", action="store_true", help="比对规范模板版本，生成 diff 与新模板")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的规范文件")
    ap.add_argument("--no-git", action="store_true", help="跳过 git 初始化（违反底线，仅极特殊场景）")
    args = ap.parse_args()

    root = Path(args.target).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.upgrade:
        return do_upgrade(root, args.model or "")

    profile = args.profile or ("software" if args.adopt else "minimal")
    preset = PROFILES[profile]
    rows: list[tuple[str, str, str]] = [MEMORY_ROW] + list(preset["dirs"])
    for spec in args.dirs:
        nm, _, purpose = spec.partition(":")
        nm = nm.strip().rstrip("/")
        if not nm:
            continue
        tracked = "否" if nm in UNTRACKED_DIRS else "是"
        rows.append((nm + "/", purpose.strip() or "（待补充职责）", tracked))
    dirs = [p.rstrip("/") for p, _, _ in rows if p.endswith("/")]
    untracked_dirs = [p.rstrip("/") for p, _, t in rows if p.endswith("/") and t == "否"]

    ptype = args.ptype or preset["type"]
    project_name = args.name or root.name
    stack = args.stack or "（未填写；可编辑本行或用 --stack 指定）"
    model = (args.model or "").strip()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%d %H:%M")
    who = model or "未声明（初始化脚本未收到 --model）"
    created: list[str] = []
    skipped: list[str] = []
    had_preexisting = any(root.iterdir())

    def write(rel: str, content: str, label: str, log_purpose: str = "") -> None:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if f.exists() and not args.force:
            skipped.append(label)
        else:
            f.write_text(content, encoding="utf-8", newline="\n")
            created.append(label)
        if not log_purpose:
            return
        lg = f.parent / (f.stem + ".log.md")
        if lg.exists():
            return
        lg.write_text(f"## {stamp} — 创建\n- 模型：{who}\n- 摘要：{log_purpose}\n- 原因：项目初始化\n",
                      encoding="utf-8", newline="\n")
        created.append(lg.relative_to(root).as_posix())

    # 1) 底线：git
    new_repo = False
    if args.no_git:
        print("[git] 已按 --no-git 跳过——这违反规范底线，仅限极特殊场景")
    elif (root / ".git").exists():
        print("[git] 已是 git 仓库，跳过 init")
    else:
        rc, out = run_git(root, "init", "-b", "main")
        if rc != 0:
            rc, out = run_git(root, "init")
        print(f"[git] init: {out.splitlines()[0] if out else 'done'}")
        new_repo = True

    # 2) 结构目录（按声明建，不硬塞）
    for d in dirs:
        (root / d).mkdir(exist_ok=True)
    if "docs" in dirs:
        (root / "docs" / "assets").mkdir(exist_ok=True)
        write("docs/assets/.gitkeep", "", "docs/assets/")
    if "code" in dirs:
        write("code/.gitkeep", "", "code/")
    if "docs" in dirs:
        write("docs/.gitkeep", "", "docs/")
    print(f"[目录] {', '.join(d + '/' for d in dirs)} 就绪（profile={profile}）")

    # 3) .gitignore
    write(".gitignore", gitignore_text(untracked_dirs), ".gitignore")

    # 4) AGENTS.md —— 唯一规范来源
    write("AGENTS.md", render_template(project_name, ptype, stack, rows), "AGENTS.md")

    # 5) 底线：项目长期记忆 + 项目日日志
    write("memory/MEMORY.md",
          MEMORY_TPL.format(name=project_name, today=today, profile=profile, model=model or "未声明"),
          "memory/MEMORY.md")
    write(f"memory/{today}.md",
          f"## {stamp} — 项目初始化\n"
          f"- 模型：{who}\n"
          f"- 摘要：建立 git 仓库、AGENTS.md（v{VERSION}）、项目记忆与日日志；结构 profile={profile}"
          f"（{', '.join(d + '/' for d in dirs) or '仅根目录'}）\n"
          f"- 原因：项目初始化\n",
          f"memory/{today}.md")

    # 6) 程序项目脚手架（仅 software 预设）；正式文件一律配同名 .log.md
    if profile == "software":
        for nm in ("PRD.md", "Design.md", "TDD.md", "开发进度.md"):
            tpl = SOFTWARE_TPL_DIR / nm
            content = tpl.read_text(encoding="utf-8") if tpl.exists() else \
                f"# {nm}\n\n（模板缺失，请补全 skill 的 assets/software/{nm}）\n"
            purpose = {"PRD.md": "产品需求文档：做什么、为什么做",
                       "Design.md": "设计文档：整体怎么做",
                       "TDD.md": "技术设计文档：选型、架构、测试策略",
                       "开发进度.md": "开发进度台账：功能状态、缺陷记录、审核结论"}.get(nm, "顶层文档")
            write(f"docs/{nm}", content, f"docs/{nm}", log_purpose=purpose)
        (root / "docs" / "features").mkdir(exist_ok=True)
        write("docs/features/.gitkeep", "", "docs/features/")
        print("[软件] docs/ 顶层文档（PRD/Design/TDD/开发进度）与 features/ 就绪（均已配 .log.md）")

    # 7) agent 入口：默认一个都不建，交给各 agent 首次进入时自建
    sel = args.agents.strip().lower()
    if sel == "none":
        print("[入口] 未预建 agent 入口文件（按需自建，对照表见 AGENTS.md 第 7 节）")
    else:
        chosen = list(ADAPTERS) if sel == "all" else [a.strip() for a in sel.split(",") if a.strip()]
        unknown = [a for a in chosen if a not in ADAPTERS]
        if unknown:
            print(f"[警告] 未知的 agent: {', '.join(unknown)}（可选: {', '.join(ADAPTERS)}）")
        for a in chosen:
            if a in ADAPTERS:
                write(ADAPTERS[a]["path"], ADAPTERS[a]["body"], a)

    # 8) README
    write("README.md", README_TPL.format(name=project_name), "README.md")

    # 8.5) 空的自定义目录补 .gitkeep，否则 git 不跟踪、结构表声明了却看不见
    for p, _, t in rows:
        if not p.endswith("/") or t != "是":
            continue
        base = root / p.rstrip("/")
        if base.is_dir() and not any(base.iterdir()):
            write(f"{p.rstrip('/')}/.gitkeep", "", p)

    # 9) 接管分析（不自动提交用户已有文件）
    if args.adopt:
        print_adopt_report(root, adopt_plan(root, rows), args.apply)
        return 0

    # 10) 首次提交（署名用模型名，不写进仓库配置；接管有存量文件时不自动提交）
    if new_repo:
        _, uname = run_git(root, "config", "user.name")
        _, mail = run_git(root, "config", "user.email")
        if had_preexisting:
            print("[git] 目录原有文件，跳过自动首提（迁移确认后一并提交）")
        elif not (uname.strip() and mail.strip()):
            print("[git] 未配置 user.email，跳过首次提交（配置后手动 git add -A && git commit）")
        else:
            run_git(root, "add", "-A")
            rc, out = run_git(root, "commit", "-m", "chore: 项目初始化（git + 规范 + 项目记忆与日志）",
                              author=model or None)
            print(f"[git] 首次提交: {'完成' if rc == 0 else '失败：' + out.splitlines()[0]}")

    # 11) 汇总
    print("\n=== 初始化完成 ===")
    print(f"项目: {project_name}    类型: {ptype}    profile: {profile}    规范版本: {VERSION}")
    print(f"目录: {root}")
    if created:
        print("已创建: " + ", ".join(created))
    if skipped:
        print("已存在而跳过（--force 可覆盖）: " + ", ".join(skipped))
    if not model:
        print("提醒: 未传 --model，日志条目记为「未声明」。开工时把模型官方名补进 .log.md 条目。")
    print("提示: 本会话后续工作请遵守项目内 AGENTS.md；可用 check_project.py 做规范巡检。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
