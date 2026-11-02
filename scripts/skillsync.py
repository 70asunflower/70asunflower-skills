#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
skillsync — 多 agent 用户级技能库同步工具

一个主库（hub），所有 agent 的 skills 目录里用 junction 指向它。
改动主库 = 所有 agent 同时生效；agent 专属技能仍留在自己目录，不进主库。

用法：
    python skillsync.py status             # 只读：每个 agent 每个技能的状态
    python skillsync.py scan               # 只读：重复副本的漂移报告
    python skillsync.py doctor             # 只读：结构问题（断链/链式/无主库）
    python skillsync.py adopt  [--apply]   # 收编散落真实副本进主库（默认 dry-run）
    python skillsync.py link   [--apply]   # 为各 agent 建 junction（默认 dry-run）
    python skillsync.py add <path> [--apply]  # 收入一个新技能并分发

安全约定：
    - 任何破坏性动作默认 dry-run，加 --apply 才落盘
    - 已存在的真实目录绝不删除，只移动到 _backup/<时间戳>/
    - 删除 junction 用 os.rmdir，不会动目标内容
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()

# 已知 agent 的 skills 目录（可用 skillsync.json 覆盖）
DEFAULT_AGENTS = {
    "workbuddy": HOME / ".workbuddy" / "skills",
    "claude": HOME / ".claude" / "skills",
    "codex": HOME / ".codex" / "skills",
    "zcode": HOME / ".zcode" / "skills",
    "gemini": HOME / ".gemini" / "config" / "skills",
    "antigravity": HOME / ".gemini" / "antigravity" / "skills",
    "dsh": HOME / ".dsh" / "skills",
}

DEFAULT_HUB = HOME / ".agents" / "skills"
CONFIG_PATH = HOME / ".agents" / "skillsync.json"

SKIP_DIRS = {"_backup", "_dist", ".git", "node_modules", "__pycache__", ".venv", "venv"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}
CORE_EXT = {".md", ".py", ".js", ".ts", ".sh", ".ps1", ".json", ".yaml", ".yml", ".txt"}
MAX_HASH_BYTES = 4 * 1024 * 1024   # 单文件超过 4MB 只记大小不哈希


# ---------------------------------------------------------------- 基础能力

def is_link(p):
    """是否为符号链接或 Windows junction。"""
    p = Path(p)
    if hasattr(os.path, "isjunction") and os.path.isjunction(p):
        return True
    return os.path.islink(p)


def link_target(p):
    """读取链接目标，解析为绝对路径；失败返回 None。

    Windows junction 的 readlink 会带 \\\\?\\ 或 \\??\\ 前缀，必须剥掉，
    否则和普通路径比较永远不相等。
    """
    try:
        raw = os.readlink(p)
    except OSError:
        return None
    for prefix in ("\\\\?\\", "\\??\\", "\\\\??\\"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    t = Path(raw)
    if not t.is_absolute():
        t = (Path(p).parent / t)
    try:
        return Path(os.path.normpath(str(t)))
    except Exception:
        return t


def same_path(a, b):
    """Windows 下稳妥的路径相等判断（大小写、分隔符、. 归一化）。"""
    if a is None or b is None:
        return False
    na = os.path.normcase(os.path.normpath(str(a)))
    nb = os.path.normcase(os.path.normpath(str(b)))
    return na == nb


def make_junction(link_path, target):
    """创建目录 junction（不需要管理员权限）。"""
    link_path = Path(link_path)
    target = Path(target)
    if not target.exists():
        raise FileNotFoundError(f"目标不存在: {target}")
    link_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"mklink 失败: {r.stdout}{r.stderr}")


def remove_junction(link_path):
    """删除 junction 本身，绝不触碰目标内容。"""
    os.rmdir(str(link_path))


def load_config():
    cfg = {
        "hub": str(DEFAULT_HUB),
        "roots": [],     # 技能根目录列表；hub 是其中之一，其余为只分发不入库的目录
        "agents": {k: str(v) for k, v in DEFAULT_AGENTS.items()},
        "exclude": {},   # {agent: [skill, ...]} 该 agent 不接收的技能
        "gitignore_untracked_block": True,
    }
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if "hub" in user:
                cfg["hub"] = user["hub"]
            if isinstance(user.get("roots"), list):
                cfg["roots"] = [str(r) for r in user["roots"]]
            if isinstance(user.get("agents"), dict):
                # 与默认合并，未列出的 agent 保留
                cfg["agents"].update({k: str(v) for k, v in user["agents"].items()})
            if isinstance(user.get("exclude"), dict):
                cfg["exclude"] = user["exclude"]
            if "gitignore_untracked_block" in user:
                cfg["gitignore_untracked_block"] = bool(user["gitignore_untracked_block"])
        except Exception as e:
            print(f"[warn] 读取 {CONFIG_PATH} 失败，用默认配置: {e}")
    cfg["hub"] = Path(cfg["hub"])
    cfg["agents"] = {k: Path(v) for k, v in cfg["agents"].items()}
    cfg["roots"] = normalize_roots(cfg)
    return cfg


def normalize_roots(cfg):
    """把 roots 规范化：hub 始终排第一，去重、转 Path、去掉不存在的项不在这里做。"""
    out = [Path(cfg["hub"])]
    for r in cfg.get("roots") or []:
        p = Path(r)
        if not any(same_path(p, q) for q in out):
            out.append(p)
    return out


# ---------------------------------------------------------------- 指纹

def fingerprint(root):
    """算技能目录的内容指纹，返回 (hash, 文件数, 字节数, 核心文件数, SKILL.md hash)。"""
    root = Path(root)
    entries = []
    nfiles = nbytes = ncore = 0
    skillmd = ""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if fn in SKIP_NAMES:
                continue
            fp = Path(dirpath) / fn
            rel = fp.relative_to(root).as_posix()
            try:
                st = fp.stat()
            except OSError:
                continue
            nfiles += 1
            nbytes += st.st_size
            ext = fp.suffix.lower()
            if ext in CORE_EXT:
                ncore += 1
            if st.st_size > MAX_HASH_BYTES:
                entries.append((rel, f"size:{st.st_size}"))
                continue
            try:
                h = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
            except OSError:
                continue
            entries.append((rel, h))
            if rel == "SKILL.md":
                skillmd = h
    combined = hashlib.sha256(
        "\n".join(f"{r}|{h}" for r, h in entries).encode("utf-8")
    ).hexdigest()[:16]
    return combined, nfiles, nbytes, ncore, skillmd


def describe(root):
    """一个目录的完整描述。"""
    root = Path(root)
    fp, nf, nb, nc, smd = fingerprint(root)
    return {
        "hash": fp, "files": nf, "bytes": nb, "core": nc, "skillmd": smd,
        "exists": root.exists(), "has_skillmd": (root / "SKILL.md").exists(),
    }


# ---------------------------------------------------------------- 采集

def collect(cfg):
    """采集所有 agent 的技能项。返回 {agent: {skill: info}}。"""
    result = {}
    for agent, base in cfg["agents"].items():
        items = {}
        if not base.exists():
            result[agent] = {"__absent__": True, "base": str(base), "skills": items}
            continue
        try:
            children = sorted(base.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            children = []
        for ch in children:
            if ch.name in SKIP_DIRS or ch.name.startswith("."):
                continue
            if not ch.is_dir() and not is_link(ch):
                continue
            if is_link(ch):
                tgt = link_target(ch)
                items[ch.name] = {"kind": "link", "target": str(tgt) if tgt else None,
                                  "target_path": tgt}
            else:
                # 真实目录：只有带 SKILL.md 才算技能
                has = (ch / "SKILL.md").exists()
                items[ch.name] = {"kind": "real", "has_skillmd": has}
                if has:
                    d = describe(ch)
                    items[ch.name].update(d)
        result[agent] = {"__absent__": False, "base": str(base), "skills": items}
    return result


def hub_skills(cfg):
    """所有技能根目录下的技能。非技能目录（README、scripts、.github 等）一律忽略。

    多根：hub 是入库的自建技能，roots 里其余目录（如 vendor）只分发、不入库。
    同名技能先到先得（hub 优先），重名的后来者忽略并提示，避免静默覆盖。
    """
    out = {}
    duplicates = []
    for root in cfg.get("roots") or [cfg["hub"]]:
        if not root.exists():
            continue
        for ch in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not ch.is_dir() or ch.name in SKIP_DIRS or ch.name.startswith("."):
                continue
            if is_link(ch):
                tgt = link_target(ch)
                item = {"kind": "link", "target": str(tgt) if tgt else None,
                        "target_path": tgt, "root": str(root)}
            else:
                if not (ch / "SKILL.md").exists():
                    continue      # 仓库里的 README/scripts 之类，不是技能
                item = {"kind": "real", "has_skillmd": True, "root": str(root)}
                item.update(describe(ch))
            if ch.name in out:
                duplicates.append((ch.name, str(root)))
                continue
            out[ch.name] = item
    for name, root in duplicates:
        print(f"[warn] 技能重名：{root}/{name} 与已收录的同名技能冲突，已忽略前者")
    return out


# ---------------------------------------------------------------- status

def cmd_status(cfg, args):
    col = collect(cfg)
    hub = hub_skills(cfg)
    agents = [a for a in cfg["agents"] if not col[a]["__absent__"]]
    absent = [a for a in cfg["agents"] if col[a]["__absent__"]]

    all_skills = set(hub)
    for a in agents:
        all_skills |= set(col[a]["skills"])
    all_skills = sorted(all_skills, key=str.lower)

    hub_s = " | ".join(str(r) for r in cfg["roots"])
    print(f"技能根 ({len(cfg['roots'])}): {hub_s}  (共 {len(hub)} 项)\n")
    print("状态说明: hub=主库真实目录  ->hub=正确链接  ->other=指向别处  REAL=真实副本(未归集)  . =无  NO-MD=目录无SKILL.md\n")

    widths = {a: max(len(a), 8) for a in agents}
    head = "技能".ljust(38) + " " + " ".join(a.ljust(widths[a]) for a in agents)
    print(head)
    print("-" * len(head))
    rows = []
    for s in all_skills:
        cells = []
        flags = []
        for a in agents:
            it = col[a]["skills"].get(s)
            if it is None:
                cells.append(".".ljust(widths[a]))
                continue
            if it["kind"] == "link":
                tgt = it.get("target_path")
                hit_root = None
                for r in cfg["roots"]:
                    if same_path(tgt, r / s):
                        hit_root = r
                        break
                if hit_root is not None:
                    cells.append("->hub".ljust(widths[a]))
                elif any(same_path(Path(tgt).parent if tgt else None, r) for r in cfg["roots"]):
                    cells.append("->hub?".ljust(widths[a]))
                else:
                    # 指向某个已知 agent 目录 => 链式
                    chained = None
                    if tgt:
                        for a2, base in cfg["agents"].items():
                            if same_path(tgt, Path(base) / s):
                                chained = a2
                                break
                    cells.append((f"->{chained}" if chained else "->oth").ljust(widths[a]))
                    if chained:
                        flags.append(f"{a}链式→{chained}")
            else:
                if not it.get("has_skillmd", True):
                    cells.append("NO-MD".ljust(widths[a]))
                else:
                    cells.append("REAL".ljust(widths[a]))
        rows.append((s, "".join(cells), flags))

    for s, cells, flags in rows:
        mark = " " if s in hub else "!"
        print(f"{mark}{s[:37].ljust(37)} {cells}")
        for f in flags:
            print(f"    └ {f}")

    print()
    n_real = sum(1 for _s, cellstr, _f in rows if "REAL" in cellstr)
    n_linked = sum(1 for _s, cellstr, _f in rows if "->hub" in cellstr)
    print(f"总计 {len(all_skills)} 个技能名；主库 {len(hub)}；"
          f"仍以真实副本存在 {n_real}；已正确回链的 agent 条目 {n_linked}")
    if absent:
        print(f"\n未安装/无 skills 目录的 agent: {', '.join(absent)}")
    return 0


# ---------------------------------------------------------------- scan

def cmd_scan(cfg, args):
    col = collect(cfg)
    hub = hub_skills(cfg)
    agents = [a for a in cfg["agents"] if not col[a]["__absent__"]]

    # 收集所有真实副本（含主库）
    copies = {}   # skill -> [(agent, desc)]
    for name, it in hub.items():
        if it["kind"] == "real" and it.get("hash"):
            copies.setdefault(name, []).append(("hub", it))
    for a in agents:
        for name, it in col[a]["skills"].items():
            if it["kind"] == "real" and it.get("hash"):
                copies.setdefault(name, []).append((a, it))

    multi = {k: v for k, v in copies.items() if len(v) > 1}
    single = {k: v for k, v in copies.items() if len(v) == 1}

    print(f"真实副本总数 {sum(len(v) for v in copies.values())}，覆盖 {len(copies)} 个技能名\n")
    print(f"  · 唯一副本（无重复）  {len(single)}")
    print(f"  · 多处副本            {len(multi)}\n")

    drift_exact, drift_skillmd, same = [], [], []
    for name, lst in sorted(multi.items(), key=lambda kv: kv[0].lower()):
        hashes = {d["hash"] for _, d in lst}
        smds = {d["skillmd"] for _, d in lst}
        if len(hashes) == 1:
            same.append((name, lst))
        elif len(smds) == 1:
            drift_skillmd.append((name, lst))
        else:
            drift_exact.append((name, lst))

    if drift_exact:
        print("=" * 78)
        print("SKILL.md 本身不同 —— 真漂移，必须人工定夺")
        print("=" * 78)
        for name, lst in drift_exact:
            print(f"\n● {name}")
            for a, d in sorted(lst, key=lambda x: -x[1]["bytes"]):
                print(f"    {a:<11} files={d['files']:<4} core={d['core']:<4} "
                      f"bytes={d['bytes']:<8} hash={d['hash']}  SKILL.md={d['skillmd']}")
            print(f"    → 建议主版本: {max(lst, key=lambda x: x[1]['files'])[0]}")

    if drift_skillmd:
        print("\n" + "=" * 78)
        print("SKILL.md 相同、附件不同 —— 轻漂移（多半是一边多了产物/依赖）")
        print("=" * 78)
        for name, lst in drift_skillmd:
            sizes = " / ".join(f"{a}={d['files']}f" for a, d in lst)
            print(f"  · {name:<40} {sizes}")

    if same:
        print(f"\n完全一致的多副本: {len(same)} 个 —— 可安全折叠成 junction")
        names = ", ".join(n for n, _ in same)
        print("  " + (names[:400] + ("..." if len(names) > 400 else "")))

    print("\n" + "=" * 78)
    print("只存在于某一个 agent、尚未进主库的技能")
    print("=" * 78)
    if hub:
        print(f"  主库里已有的: {', '.join(sorted(hub))}")
    for name, lst in sorted(single.items(), key=lambda kv: kv[0].lower()):
        a, d = lst[0]
        if a == "hub":
            continue
        print(f"  · {name:<40} [{a}]  files={d['files']} core={d['core']}")
    return 0


# ---------------------------------------------------------------- doctor

def load_baseline(hub: Path) -> dict:
    """读豁免基线（scripts/skillsync-baseline.json）。

    语义定义在 precommit.py 里：intentional = 设计上就不共享（第三方技能按渠道
    各自保留），chained = 待修欠账。doctor 必须读同一份基线，否则会把设计上
    保留的项当成问题报出来——和提交闸门给出相反的结论。
    """
    path = Path(hub) / "scripts" / "skillsync-baseline.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"intentional": [], "chained": []}
    data.setdefault("intentional", [])
    data.setdefault("chained", [])
    return data


def cmd_doctor(cfg, args):
    col = collect(cfg)
    hub = hub_skills(cfg)
    agents = [a for a in cfg["agents"] if not col[a]["__absent__"]]
    baseline = load_baseline(cfg["hub"])
    exempt = set(baseline["intentional"]) | set(baseline["chained"])
    issues = 0
    broken = 0

    print(f"主库: {cfg['hub']}  exists={cfg['hub'].exists()}")
    for r in cfg["roots"][1:]:
        print(f"附加根: {r}  exists={r.exists()}")
    print()

    # 1 断链
    for a in agents:
        for name, it in col[a]["skills"].items():
            if it["kind"] != "link":
                continue
            tgt = it.get("target_path")
            if tgt is None:
                print(f"[断链] {a}/{name}：读不出目标")
                issues += 1
                broken += 1
            elif not Path(tgt).exists():
                print(f"[断链] {a}/{name} → {tgt}（目标不存在）")
                issues += 1
                broken += 1

    # 2 链式嵌套
    for a in agents:
        for name, it in col[a]["skills"].items():
            if it["kind"] != "link":
                continue
            tgt = it.get("target_path")
            if not tgt:
                continue
            for a2, base in cfg["agents"].items():
                if a2 == a:
                    continue
                if same_path(tgt, Path(base) / name):
                    inner = col[a2]["skills"].get(name)
                    kind = "也指向别处" if inner and inner["kind"] == "link" else "是真实目录"
                    key = f"{a}/{name}"
                    if key in exempt:
                        # 仍打印成 [链式]，precommit 靠这行做「新增才拦截」和
                        # --update-baseline 的统计；只是不计入问题数。
                        print(f"[链式] {a}/{name} → {a2}/{name}（{kind}），"
                              f"基线记为不共享，已豁免")
                    else:
                        print(f"[链式] {a}/{name} → {a2}/{name}（{kind}），应全部指向主库")
                        issues += 1
                    break

    # 3 主库自身含链接
    for name, it in hub.items():
        if it["kind"] == "link":
            print(f"[主库含链接] {name} → {it.get('target')}，主库内不应有链接")
            issues += 1

    # 4 目录下无 SKILL.md 的目录（非技能杂物）
    for a in agents:
        junk = [n for n, it in col[a]["skills"].items()
                if it["kind"] == "real" and not it.get("has_skillmd", True)]
        if junk:
            print(f"[杂物] {a} 下无 SKILL.md 的目录: {', '.join(junk)}")
            issues += 1

    # 5 主库未纳入 git
    gitdir = cfg["hub"] / ".git"
    print(f"\n[提示] 主库 git 管理: {'已初始化' if gitdir.exists() else '未初始化（建议 git init 便于回滚）'}")

    if broken:
        print(f"\n[提示] {broken} 个断链是「技能已删、junction 还留着」，"
              f"跑 `skillsync.py prune --apply` 一次清掉")
    print(f"\n问题数: {issues}")
    return 0 if issues == 0 else 1


def update_gitignore(cfg, add=None):
    """刷新 .gitignore 的第三方技能标记区块。

    主库是公开 git 仓库时，第三方技能不该出现在 git status 里，
    也不该被 git add -A 顺手提交。

    **只减不增**：已有排除项保留（已跟踪的自动移出），但绝不自动新增。
    原来按「目录存在但 git 未跟踪」判定，等于把用户刚建的新技能也当成第三方
    一起排除——那些技能从此进不了 git，直到有人发现。新技能必须先显式
    `gitignore --add <name>` 才会被排除。
    """
    hub = cfg["hub"]
    gi = hub / ".gitignore"
    if not (hub / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "ls-files"], cwd=str(hub),
                           capture_output=True, text=True, timeout=60)
        tracked = set()
        for line in r.stdout.splitlines():
            top = line.strip().split("/", 1)[0]
            if top:
                tracked.add(top)
    except Exception:
        return None

    skills = []
    for ch in hub.iterdir():
        if not ch.is_dir() or ch.name.startswith(".") or ch.name in SKIP_DIRS:
            continue
        if not (ch / "SKILL.md").exists():
            continue
        skills.append(ch.name)
    untracked = sorted(s for s in skills if s not in tracked)

    BEGIN = "# >>> skillsync: 第三方技能，不纳入本仓库版本控制 >>>"
    END = "# <<< skillsync <<<"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    prev = set()
    if BEGIN in text and END in text:
        pre = text.split(BEGIN)[0].rstrip()
        post = text.split(END, 1)[1].lstrip("\n")
        for line in text.split(BEGIN)[1].split(END)[0].splitlines():
            line = line.strip().rstrip("/")
            if line and not line.startswith("#"):
                prev.add(line)
    else:
        pre, post = text.rstrip(), ""

    if add:
        prev |= set(add)
    # 已纳入 git 的自动移出；其余保留。新出现的一律不加，交给 --add 显式决定。
    blocked = sorted(s for s in prev if s in untracked)
    newcomers = sorted(s for s in untracked if s not in prev)

    block_lines = [BEGIN]
    if blocked:
        block_lines += [f"{name}/" for name in blocked]
    else:
        block_lines.append("# （当前所有技能目录都已跟踪）")
    block_lines.append(END)
    new = pre + "\n\n" + "\n".join(block_lines) + "\n"
    if post.strip():
        new += "\n" + post
    gi.write_text(new, encoding="utf-8")
    return {"blocked": blocked, "new": newcomers}


# ---------------------------------------------------------------- adopt

def split_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", text


def body_sig(skill_dir):
    """SKILL.md 正文（去 frontmatter）的指纹。正文相同 = 文档本身没人改过。"""
    sm = Path(skill_dir) / "SKILL.md"
    if not sm.exists():
        return None
    text = sm.read_text(encoding="utf-8", errors="replace")
    _, body = split_frontmatter(text)
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:12]


def copy_tree_clean(src, dst):
    shutil.copytree(src, dst, symlinks=False,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))


def cmd_adopt(cfg, args):
    apply = args.apply
    hub_path = cfg["hub"]
    only = set(args.only.split(",")) if getattr(args, "only", None) else None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    # 备份区放在仓库外面，避免把副本塞进 git 仓库
    backup = hub_path.parent / "_skillsync_backup" / stamp

    # 1. 主库内的链接先实体化（主库必须是真实目录，否则还会链式）
    for name, it in list(hub_skills(cfg).items()):
        if it["kind"] != "link":
            continue
        if only and name not in only:
            continue
        src = it.get("target_path")
        print(f"[hub-link] {name} 是链接 → {src}，实体化为主库真实目录")
        if apply and src and Path(src).exists():
            tmp = hub_path / f".{name}.adopting"
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            copy_tree_clean(src, tmp)
            remove_junction(hub_path / name)
            tmp.rename(hub_path / name)

    # 实体化后重新采集
    col = collect(cfg)

    # 2. 按技能名聚合真实副本
    groups = {}
    for a, data in col.items():
        if data["__absent__"]:
            continue
        for name, it in data["skills"].items():
            if it["kind"] == "real" and it.get("has_skillmd"):
                groups.setdefault(name, []).append((a, cfg["agents"][a] / name, it))

    # 3. 决定每个技能的处理方式
    plan = []
    for name, lst in sorted(groups.items(), key=lambda kv: kv[0].lower()):
        if only and name not in only:
            continue
        hub_dir = hub_path / name
        if hub_dir.exists() and not is_link(hub_dir):
            h_body = body_sig(hub_dir)
            if all(body_sig(p) == h_body for _a, p, _it in lst):
                plan.append(("dedupe", name, None, lst))
            else:
                plan.append(("conflict", name, "主库与副本正文不同", lst))
        else:
            bodies = {body_sig(p) for _a, p, _it in lst}
            if len(bodies) == 1:
                base = max(lst, key=lambda x: x[2]["files"])
                kind = "merge" if len(lst) > 1 else "adopt"
                plan.append((kind, name, base[0], lst))
            else:
                plan.append(("conflict", name, f"副本间正文不同({len(bodies)}种)", lst))

    # 4. 预演输出
    tag = "执行" if apply else "试运行（未落盘，加 --apply 才动文件）"
    print(f"\n{tag} — 备份区 {backup}\n")
    n_ok = n_conf = 0
    for kind, name, base_agent, lst in plan:
        if kind == "conflict":
            continue
        n_ok += 1
        who = ",".join(a for a, _p, _i in lst)
        extra = f"  base={base_agent}" if base_agent else ""
        print(f"  [{kind:<6}] {name:<38} 副本: {who}{extra}")
    print()
    for kind, name, reason, lst in plan:
        if kind != "conflict":
            continue
        n_conf += 1
        print(f"  [跳过  ] {name:<38} {reason}  →  {','.join(a for a,_,_ in lst)}")

    print(f"\n可自动处理 {n_ok} 个；需人工定夺 {n_conf} 个")
    if not apply:
        print("\n没有改动任何文件。")
        return 0

    # 5. 落盘
    for kind, name, _base, lst in plan:
        if kind == "conflict":
            continue
        hub_dir = hub_path / name
        try:
            if kind == "merge":
                base = max(lst, key=lambda x: x[2]["files"])
                if hub_dir.exists():
                    shutil.rmtree(hub_dir)
                copy_tree_clean(base[1], hub_dir)
                # 补齐其他副本独有的文件（文件并集）
                for _a, p, _it in lst:
                    for f in Path(p).rglob("*"):
                        if not f.is_file() or "__pycache__" in f.parts or f.suffix == ".pyc":
                            continue
                        rel = f.relative_to(p)
                        dst = hub_dir / rel
                        if not dst.exists():
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dst)
            elif kind == "adopt":
                src = lst[0][1]
                if hub_dir.exists():
                    shutil.rmtree(hub_dir)
                copy_tree_clean(src, hub_dir)

            # 备份源目录并回链
            for a, p, _it in lst:
                b = backup / a / name
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(b))
                make_junction(p, hub_dir)
            print(f"  ok {kind:<6} {name}  ←  {','.join(a for a,_,_ in lst)}")
        except Exception as e:
            print(f"  !! {name} 失败: {e}")

    print(f"\n完成。原始副本已移入 {backup}（可随时取回）")
    if cfg.get("gitignore_untracked_block"):
        res = update_gitignore(cfg)
        if res and res["new"]:
            names = res["new"]
            print(f"[提示] {len(names)} 个未跟踪技能未被自动排除"
                  f"（可能是你自己新建的）：{', '.join(names[:6])}"
                  f"{' …' if len(names) > 6 else ''}")
            print("       确认是第三方再跑：skillsync.py gitignore --add <名字>")
    print("下一步：跑 link --apply 把主库技能分发到其余 agent。")
    return 0


# ---------------------------------------------------------------- link

def find_conflicts(cfg):
    """主库里存在、但某个 agent 的真实副本正文与主库不同的技能名。

    这类技能既不能分发（会把主库版本塞给别的 agent，制造新分歧），
    也不能回链（会丢掉 agent 侧可能的更新），必须人工定夺。
    """
    col = collect(cfg)
    hub = hub_skills(cfg)
    out = set()
    for name, it in hub.items():
        if it["kind"] != "real":
            continue
        hb = body_sig(Path(it["root"]) / name)
        for a, data in col.items():
            if data["__absent__"]:
                continue
            civ = data["skills"].get(name)
            if civ and civ["kind"] == "real" and civ.get("has_skillmd"):
                if body_sig(cfg["agents"][a] / name) != hb:
                    out.add(name)
                    break
    return out


def cmd_link(cfg, args):
    apply = args.apply
    hub = hub_skills(cfg)
    conflicts = find_conflicts(cfg)
    names = [n for n, it in hub.items()
             if it["kind"] == "real" and it.get("has_skillmd") and n not in conflicts]
    print(f"主库可分发技能 {len(names)} 个")
    if conflicts:
        print(f"冲突保护：{len(conflicts)} 个技能暂不分发（{', '.join(sorted(conflicts))}）")
    print()

    plan = []
    exclude = cfg.get("exclude") or {}
    for a, base in cfg["agents"].items():
        if not base.exists():
            continue
        ex = set(exclude.get(a, []))
        for name in names:
            if name in ex:
                continue
            p = base / name
            target = Path(hub[name]["root"]) / name
            if is_link(p):
                if same_path(link_target(p), target):
                    continue
                plan.append(("relink", a, name))
            elif p.exists():
                plan.append(("skip-real", a, name))
            else:
                plan.append(("link", a, name))

    for action, a, name in plan:
        print(f"  [{action:<10}] {a}/{name}")

    if not apply:
        print("\n加 --apply 才建链接。skip-real 需要先跑 adopt。")
        return 0

    for action, a, name in plan:
        p = cfg["agents"][a] / name
        target = Path(hub[name]["root"]) / name
        if action == "relink":
            remove_junction(p)
            make_junction(p, target)
        elif action == "link":
            make_junction(p, target)
        print(f"  ok {action} {a}/{name}")
    print("\n完成。")
    return 0


# ---------------------------------------------------------------- add

def cmd_add(cfg, args):
    src = Path(args.path).expanduser().resolve()
    if not (src / "SKILL.md").exists():
        print(f"错误: {src} 下没有 SKILL.md，不是合法技能目录")
        return 2
    name = args.name or src.name
    target = cfg["hub"] / name
    if target.exists():
        print(f"错误: 主库已有 {name}")
        return 2
    print(f"收入: {src} → {target}")
    if not args.apply:
        print("加 --apply 才执行。")
        return 0
    shutil.copytree(src, target, symlinks=False)
    print("已收入主库。接着跑 link --apply 分发到各 agent。")
    return 0


def cmd_prune(cfg, args):
    """清理断链：junction 还在，但它指向的目标已经没了。

    典型场景：技能从主库删掉后，各 agent 目录里那条 junction 成了空壳。
    doctor 会报「断链」，但没地方一键清理，只能手工逐个删。
    """
    apply = getattr(args, "apply", False)
    stale = []
    for a, base in cfg["agents"].items():
        base = Path(base)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not is_link(child):
                continue
            tgt = link_target(child)
            # 断链的判定必须用 lexists + 目标存在性，不能用 exists()：
            # 断链本身 exists() 就是 False，分不清「没有这个链接」和「链接坏了」
            if tgt is None or not tgt.exists():
                stale.append((a, child, tgt))

    if not stale:
        print("没有断链，不用清理。")
        return 0

    print(f"发现 {len(stale)} 个断链：")
    for a, p_, tgt in stale:
        print(f"  {a:<14}{p_.name:<34}→ {tgt if tgt else '(读不出目标)'}")

    if not apply:
        print("\n这是 dry-run。确认要删就加 --apply（只删链接本身，不碰目标目录）。")
        return 0

    ok = fail = 0
    for a, p_, tgt in stale:
        try:
            # os.rmdir 对 junction 只摘掉重解析点，不递归、不碰目标
            os.rmdir(p_)
            ok += 1
        except OSError as e:
            print(f"  [失败] {a}/{p_.name}: {e}")
            fail += 1
    print(f"\n已清理 {ok} 个" + (f"，失败 {fail} 个" if fail else ""))
    return 0 if fail == 0 else 1


def cmd_gitignore(cfg, args):
    res = update_gitignore(cfg, add=getattr(args, "add", None))
    if res is None:
        print("主库不是 git 仓库或 git 不可用，跳过")
        return 1
    print(f"已写入 .gitignore 标记区块，排除 {len(res['blocked'])} 个未跟踪目录：")
    for n in res["blocked"]:
        print("  " + n)
    if res["new"]:
        print(f"\n未排除（新出现，未自动加）：{len(res['new'])} 个")
        for n in res["new"]:
            print("  " + n)
        print("\n确认是第三方：skillsync.py gitignore --add <名字> ...")
    return 0


# ---------------------------------------------------------------- rules

RULE_BEGIN = "<!-- BEGIN skillsync-rules -->"
RULE_END = "<!-- END skillsync-rules -->"

DEFAULT_RULE_TARGETS = {
    "claude": HOME / ".claude" / "CLAUDE.md",
    "codex": HOME / ".codex" / "AGENTS.md",
    "zcode": HOME / ".zcode" / "AGENTS.md",
    "gemini": HOME / ".gemini" / "GEMINI.md",
    # WorkBuddy 的记忆文件在 user-<id>-personal/ 下，id 每台机器不同，用通配展开
    "workbuddy": HOME / ".workbuddy" / "user-*-personal" / "MEMORY.md",
    "workbuddy-ai": HOME / ".workbuddy-ai" / "user-*-personal" / "MEMORY.md",
}


def expand_rule_targets(targets):
    """把带 * 的目标展开成具体文件路径；无通配的原样返回单元素列表。"""
    out = {}
    for name, path in targets.items():
        s = str(path)
        if "*" not in s:
            out[name] = [Path(s)]
            continue
        p = Path(s)
        base = p.parent.parent
        if not base.exists():
            out[name] = []
            continue
        out[name] = [hit / p.name for hit in sorted(base.glob(p.parent.name))]
    return out


def read_rule_block(hub):
    """从主库 AGENTS.md 里取出规则区块。"""
    src = Path(hub) / "AGENTS.md"
    if not src.exists():
        return None
    text = src.read_text(encoding="utf-8")
    i, j = text.find(RULE_BEGIN), text.find(RULE_END)
    if i < 0 or j < 0:
        return None
    return text[i:j + len(RULE_END)]


def cmd_rules(cfg, args):
    """把主库 AGENTS.md 的规则区块分发到各 agent 的全局指令文件。

    只维护标记区块，不碰文件里其他内容。旧版（没有标记、整篇都是规则）
    会被整体替换，替换前自动备份。
    """
    apply = args.apply
    block = read_rule_block(cfg["hub"])
    if not block:
        print(f"错误：在 {cfg['hub'] / 'AGENTS.md'} 里找不到规则标记区块")
        return 2

    targets = expand_rule_targets(cfg.get("rules_targets") or DEFAULT_RULE_TARGETS)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    changed = 0

    for name, paths in targets.items():
        if not paths:
            print(f"  [跳过] {name:<12} 未找到目标目录")
            continue

        for path in paths:
            if not path.parent.exists():
                print(f"  [跳过] {name:<12} 目录不存在: {path.parent}")
                continue

            old = path.read_text(encoding="utf-8") if path.exists() else ""

            if RULE_BEGIN in old and RULE_END in old:
                i = old.find(RULE_BEGIN)
                j = old.find(RULE_END) + len(RULE_END)
                new = old[:i] + block + old[j:]
                action = "更新区块"
            elif old.strip() and "用户级技能库" in old:
                # 旧版整篇都是规则，整体替换
                new = "# 本机技能库与写作规则\n\n" + block + "\n"
                action = "替换旧版"
            elif old.strip():
                new = old.rstrip() + "\n\n" + block + "\n"
                action = "追加区块"
            else:
                new = block + "\n"
                action = "新建"

            if new == old:
                print(f"  [无变化] {name:<12} {path}")
                continue

            print(f"  [{action}] {name:<12} {path}")
            changed += 1
            if apply:
                if path.exists() and old.strip():
                    shutil.copy2(path, path.with_name(path.name + f".bak.{stamp}"))
                path.write_text(new, encoding="utf-8")

    if not apply:
        print(f"\n预演：{changed} 个文件待写入。加 --apply 才落盘。")
    else:
        print(f"\n完成：{changed} 个文件已更新。")
    return 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="多 agent 用户级技能库同步")
    ap.add_argument("--hub", help="覆盖主库路径")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="每个 agent 每个技能的状态")
    p.add_argument("--json", action="store_true")

    sub.add_parser("scan", help="重复副本漂移报告")
    sub.add_parser("doctor", help="结构问题检查")

    p = sub.add_parser("adopt", help="收编真实副本进主库")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--only", help="只处理这些技能，逗号分隔")

    p = sub.add_parser("link", help="为各 agent 建 junction")
    p.add_argument("--apply", action="store_true")

    p = sub.add_parser("add", help="收入一个新技能")
    p.add_argument("path")
    p.add_argument("--name")
    p.add_argument("--apply", action="store_true")

    p = sub.add_parser("prune", help="清理断链（技能已删、junction 还留着）")
    p.add_argument("--apply", action="store_true", help="真正删除，默认 dry-run")

    p = sub.add_parser("gitignore", help="刷新 .gitignore 的第三方技能区块（只减不增）")
    p.add_argument("--add", nargs="+", metavar="SKILL",
                   help="显式把技能加入排除名单")

    p = sub.add_parser("rules", help="把主库 AGENTS.md 的规则分发到各 agent 全局文件")
    p.add_argument("--apply", action="store_true")

    args = ap.parse_args()
    cfg = load_config()
    if args.hub:
        cfg["hub"] = Path(args.hub).expanduser()
        cfg["roots"] = [cfg["hub"]]

    fn = {"status": cmd_status, "scan": cmd_scan, "doctor": cmd_doctor,
          "adopt": cmd_adopt, "link": cmd_link, "add": cmd_add,
          "prune": cmd_prune,
          "gitignore": cmd_gitignore, "rules": cmd_rules}[args.cmd]
    return fn(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
