---
name: project-init
description: 项目底线与规范生成器。当用户说"项目初始化、建个新项目、立规矩、规范 agent 行为、生成 AGENTS.md、接管旧项目、整理项目、规范升级、检查项目、项目是不是乱了"时使用，即使没明说"初始化"；agent 进入已初始化项目收工前也可触发自检。只立四条不可协商的底线——git 管理、AGENTS.md 唯一规范来源、三层留痕（memory/MEMORY.md 项目记忆 + memory/日期的项目日日志 + 每个正式文件的同名 .log.md，条目必须带模型 id）、正式产出无 AI 痕迹；其余全部交给项目自己声明。结构不搞一刀切：minimal / docs / software 三种预设，或用 --dirs 自定义目录，根目录文件也能登记。agent 入口文件默认一个都不预建，各 agent 首次进入时按 AGENTS.md 里的对照表自建自己的那一份。含 adopt 接管散乱项目（先出迁移建议，--apply 才动）、upgrade 规范模板升级（只出 diff 不覆盖）、check 只读巡检（--fix 修无争议项、--scan 批量）。
---

# project-init —— 立底线，不立模板

给项目装上四条底线，其余让项目自己长。

| 底线 | 落地物 |
|------|--------|
| 必须 git 管理 | `git init` + `.gitignore`；正式产出必须入库 |
| 唯一规范来源 | `AGENTS.md`（各 agent 入口只指向它，不另写一套） |
| 必须留痕 | 三层：`memory/MEMORY.md`（项目记忆）、`memory/<日期>.md`（项目日日志）、**每个正式文件配同名 `.log.md`**；每条都带 `模型：` |
| 正式产出无 AI 痕迹 | 交付内容与代码注释禁对话腔、emoji、AI 声明、正文修订历史 |

**不立**的部分：目录结构（项目自己声明）、要不要建 PRD/Design/TDD（只有 software 预设才要）、agent 入口文件（谁用谁建）。

**三层留痕各管一段，别混**：项目记忆放长期结论（是什么/决策/坑），日日志放「今天整个项目做了什么」，逐文件日志放「这个文件被谁改过」。三者都强制，巡检缺一即报 E。

## 何时必须触发（硬规则，不靠用户开口）

只要出现下列动作，**第一件事是跑本 skill，不要先建目录、先写文件**：

- 新建项目 / 新建仓库 / 「帮我起个项目」/ 在一个空目录里开工
- 接管、整理、规范化一个已有项目
- 用户问「项目是不是乱了 / 有没有 AI 痕迹 / 该建的文档建了吗」

跑完**立即用 `project-review` 跑一次基线审查**，把起始分数记进当日日日志，此后阶段性复查。两个技能是配套的：init 立规矩，review 给分数和整改清单。

## 首次使用：把这条规则写进全局记忆

本 skill 第一次被使用时（或换了一台机器、新装了一个 agent），**必须先把这条规则登记进该 agent 的全局记忆**，否则下次开新项目时没有任何东西提醒你触发它：

```bash
python "<本skill>/scripts/ensure_rule.py"          # 先看哪些 agent 没登记
python "<本skill>/scripts/ensure_rule.py" --apply  # 写入
```

规则正文的唯一来源是 `assets/global-rule.md`；脚本把它按 `<!-- BEGIN project-init-rule -->` 标记块写进各 agent 的全局文件（Claude `~/.claude/CLAUDE.md`、Codex `~/.codex/AGENTS.md`、ZCode `~/.zcode/AGENTS.md`、Gemini `~/.gemini/GEMINI.md`、WorkBuddy 国内版 `~/.workbuddy/MEMORY.md`、海外版 `~/.workbuddy-ai/user-*/MEMORY.md`）。**幂等**：同内容跳过，规则改了就地替换标记块，不碰文件其他内容。只处理已存在的 agent 目录，不凭空造文件。

跑完向用户说一句「已把新建项目规则写进 N 个 agent 的全局记忆」，不要静默。

## 结构预设：先判断项目是什么，再选

| profile | 建的目录 | 适用 |
|---------|----------|------|
| `minimal`（默认） | 仅 `memory/` | 笔记、调研、单文件小工具、还没定型的项目 |
| `docs` | `memory/ docs/ tmp/` | 文档/报告/论文/方案类项目 |
| `software` | `memory/ docs/ code/ tmp/` + PRD/Design/TDD/开发进度 + `docs/features/` | 正经写代码的项目 |

都不合适就 `--dirs "assets:图片素材"` 追加，反复给几次即可；根目录文件（如 `index.html`）也能在结构表里登记一行。**拿不准就用 `minimal`**——目录随时能加，加完在结构表补一行职责即可。

## 用法

脚本只用 Python 标准库。**务必传 `--model`**（你的模型官方名），它写进首条日志与首次提交署名。

### 场景一：新项目

```bash
python "<本skill>/scripts/init_project.py" "<项目目录>" --model "DeepSeek-V4.1-Flash"
#   --profile minimal|docs|software   结构预设
#   --dirs "a:用途"                   追加顶层目录（可反复）
#   --type 软件|文档|混合              默认由 profile 推断；含「软件」才启用开发流程
#   --stack "Python 3.12 + FastAPI"   技术栈写入 AGENTS.md
#   --for all|claude,cursor           预建 agent 入口（默认 none，交给各 agent 自建）
#   --force / --no-git
```

做的事：git init（main）→ 按预设建目录 → `.gitignore` → `AGENTS.md`（结构表已按实际目录渲染）→ `memory/MEMORY.md` + 当日日日志 → software 预设额外生成四份顶层文档（**各配 `.log.md`**）→ `README.md` → 首次提交（署名用 `--model`，不写进仓库配置）。已存在的文件默认跳过。

### 场景二：接管已有散乱项目

```bash
python init_project.py "<目录>" --adopt --model "..."        # 补底线 + 出迁移建议，不动文件
python init_project.py "<目录>" --adopt --apply --model "..." # 执行无争议移动
```

`--adopt` 默认按 `software` 预设（老项目多半有 docs/code）。建议按扩展名启发式给出，只落到结构表声明过的目录；**「需人工判断」项一律不动**，必须与用户逐个确认。

### 场景三：规范模板升级

```bash
python init_project.py "<目录>" --upgrade
```

只打印 diff 并把新模板写到 `tmp/AGENTS.new.md`，**不覆盖**——规范文件改不改由所有者定。会保留原有的项目名、类型与结构表。1.x 老项目（无结构表）按实际存在的 docs/code/tmp 推断后升级。

### 场景四：巡检

```bash
python check_project.py "<目录>"                        # 只读
python check_project.py "<目录>" --fix --model "..."    # + 无争议修复
python check_project.py --scan "<工作区根>" --depth 2   # 批量
```

检查依据是项目自己的 `AGENTS.md`：结构表决定「什么该在哪」，头部 `项目类型` 决定要不要开发流程。

- **[E] 底线级**：不是 git 仓库；缺 `AGENTS.md`；缺 `memory/MEMORY.md` 或缺项目日日志；任一日志条目缺 `模型：`；正式文件缺同名 `.log.md`；版本副本增殖（`_v2`/`final`/`最终`）；命名硬伤（占位名、空格与特殊字符、`(1)` 副本）；正式产出 AI 痕迹；台账与功能文档状态不一致。有 E 退出码 1。
- **[W] 建议**：结构表声明了却没建的目录；根目录出现未登记条目；文件名含日期；software 项目缺顶层文档；非 UTF-8；tmp 被 git 跟踪；未跟踪正式文件；日日志 14 天没更新。
- **[I] 提示**：未提交变更；临时区积压；日日志超过 60 份。
- **--fix 只做无争议的**：补声明过的目录、`MEMORY.md`、当日日日志、缺失的 `.log.md`、顶层文档与功能文档骨架（含各自日志）。AI 痕迹、版本副本、命名硬伤、状态冲突须人工。

## 初始化之后（触发本 skill 的 agent 必做）

1. 读项目内生成的 `AGENTS.md` 全文，本会话后续工作严格遵守。
2. **按需建自己的入口**：项目里没有你所用工具的入口文件时，照 `AGENTS.md` 第 7 节的对照表建一个只指向 `AGENTS.md` 的薄入口，提交后继续。只建你自己那一个，不代建别的 agent 的。
3. 向用户简报：选了哪个 profile、建了哪些目录与文件、四条底线各一句话、当前哪些地方还是空的（如 `MEMORY.md` 的「项目是什么」待填）。

## 为什么这样设计

- **结构交给项目声明，不交给脚本**：真实项目差别很大（论文、数据、单页应用、笔记库），一刀切只会逼人绕过规则。现在唯一的硬约束是「表里写的就得照做」。
- **入口文件不预建**：预建 7 个只会制造 7 份要么过时要么没人读的指针。谁进来谁建自己那份，成本更低也更准。
- **底线必须硬**：git 与三层留痕是「事后还能查」的唯一保障，模型 id 是「谁改的」的唯一线索——这几样松了，规范再漂亮也没用。
- **三层留痕不是重复**：项目记忆是结论，日日志是过程，逐文件日志是归属。少一层就有一类问题查不到——只记日日志时，问「这份文件谁动过」要翻遍所有日日志。
- **命名硬伤按 E 卡**：占位名、空格、`(1)` 副本这类问题一旦入库，后面每个工具都要为它做兼容。日期留给 W，因为数据文件的日期可能真是内容。

## 自定义

- 规范正文：`assets/AGENTS.template.md`（占位符 `{{PROJECT_NAME}} {{PROJECT_TYPE}} {{TECH_STACK}} {{VERSION}} {{STRUCTURE_ROWS}} {{SOFTWARE_SECTION}}`）。改后递增 `init_project.py` 的 `VERSION`，老项目用 `--upgrade` 同步。
- 全局触发规则：`assets/global-rule.md`（改这里，然后 `ensure_rule.py --apply` 分发到各 agent）。
- 开发流程段落：`assets/sections/software.md`（程序项目）与 `assets/sections/plain.md`（非程序项目）。
- 程序项目文档模板：`assets/software/`。
- 结构预设：`init_project.py` 的 `PROFILES`；agent 入口：`ADAPTERS`；接管启发式：`KEEP_ROOT / DOC_EXTS / CODE_EXTS / TMP_EXTS`。
- 检查规则与词表：`check_project.py` 顶部常量（`ALLOWED_ROOT`、`VERSIONISH`、`AI_PHRASES_*`、`REQUIRED_SW_DOCS`、`LOG_STALE_DAYS`）。

## 自测

```bash
python scripts/init_project.py %TEMP%\pi-min --model T && python scripts/check_project.py %TEMP%\pi-min   # 应 0E 0W
python scripts/init_project.py %TEMP%\pi-sw --profile software --model T                                 # 四份顶层文档 + 各自 .log.md
python scripts/check_project.py %TEMP%\pi-sw --fix --model T                                             # 补记忆/日志
python scripts/check_project.py --scan %TEMP% --depth 1                                                  # 批量
python scripts/init_project.py %TEMP%\pi-min --upgrade                                                   # 同版本应报「已是最新」
python scripts/ensure_rule.py                                                                            # 再跑一次应全部「已登记」
```

违规样例：`docs/报告_v2.md`（含「作为一个AI」）应报 E 副本 + E 痕迹；`docs/方案.md` 没有 `方案.log.md` 应报 E 缺日志；日志条目缺 `模型：` 应报 E；`docs/数据 (1).md` 应报 E 命名（特殊字符 + 副本）；`docs/20260928-记录.md` 报 W 含日期；根目录放未登记的 `index.html` 应报 W 并在结构表补一行后消失。
