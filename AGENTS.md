# 本机技能库使用规则

本文件是**唯一权威源**。修改这里，然后运行 `python scripts/skillsync.py rules --apply`
把下面标记区块的内容分发到各 agent 的全局指令文件。

不要直接去改各 agent 的 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 里的同名区块——下次分发会被覆盖。

<!-- BEGIN skillsync-rules -->
## 用户级技能库

本机所有 AI agent 的用户级技能放在同一处：`D:\Projects\agent\skills\`，分两个根：
`hub\` 是本仓库（自建技能，git 管理），`vendor\` 放第三方技能（不属本仓库，只分发）。
各 agent 的 skills 目录里每一项都是指向这两个根之一的目录联结（junction），不是副本。

- **修改技能**：直接改。改 agent 目录还是改仓库，都是同一份文件。
- **新增技能**：必须建在仓库里（`<skill>/SKILL.md`，frontmatter 需 `name` 与 `description`，`name` 与目录名一致）。不要在你的 skills 目录下新建真实目录——那个父目录是真实的，新建出来的会脱离仓库，其他 agent 看不到。
- **第三方技能**（Kimi/Wind 官方、Academic pack、FBSir 等）放 `vendor\`，不要放进 hub，也不要 `git add`。`.gitignore` 的 `skillsync` 区块仅作历史兼容保留。
- **不要复制技能**。副本会立刻开始漂移。
- WorkBuddy 国内版（`~/.workbuddy`）与海外版（`~/.workbuddy-ai`）是两个独立安装，各有自己的 skills 目录，但都链到同一处 hub/vendor，改一处两边同时生效。其他 agent 同理。

## 维护技能：更新即重构，禁止末尾追加

技能是**每次触发都整篇读进上下文**的，篇幅直接等于成本。所以「更新技能」不等于「在文件末尾再补一段」：

- **默认动作是重构，不是新增。** 新知识先判断归属：替换旧条目 / 合并进既有条目 / 确实开了新主题才允许新增条目。
- **每次更新都要能回答「删了什么」。** 净增而不删，就是没重构。该删的典型：版本变更日志与升级过程、事故经过的叙事（只留规则）、跨技能重复的规则、对执行无帮助的日期与出处标注。
- **同一规则只在一个技能里维护**，其余技能写一行指针（例：公式规则归 `siyuan-markdown-formula-formatter`，`siyuan-kernel-ops` 只留指针）。两处都写，迟早各自漂移。
- **瘦身顺序**：删叙事与变更日志 → 跨技能去重 → 最后才把代码抽到 `scripts/`。反过来先动代码会破坏可用性。
- **长技能（>300 行）**优先把细节拆到 `scripts/` 或子文件，正文只留判断规则、症状索引与指针。

## 改完技能必须同步到所有 agent

**任何技能改动（新增 / 删除 / 改名 / 改 frontmatter）做完，必须立刻跑完这三步，缺一步都算没做完：**

```bash
python scripts/skillsync.py link --apply    # 新增的技能补链接
python scripts/skillsync.py prune --apply   # 删掉的技能清断链
python scripts/skillsync.py doctor          # 必须回到「问题数: 0」
```

为什么强制：各 agent 的 skills 目录里是 **junction**，主库把目录删了，链接就变成空壳。
不清理的话 agent 会看到一个指向空路径的技能条目——不报错，但行为不可预期。

**`doctor` 不返回 0 就不要说「已完成」。** 删技能尤其容易漏，一次删 7 个会在 6 个 agent
目录里留下 42 条断链。

## 技能规范

规范的**唯一可执行定义**是 `scripts/lint_skills.py`，提交闸门会跑它，有 error 直接拒绝提交。
本节只解释为什么，不重复细则——两边写两遍必然漂移。

三条硬要求（error）：

- **frontmatter**：`---` 开头、有 `name` 且与目录名一致、有 `description`
- **description 80–600 字**：它进的是每次对话的技能清单，写长了会被截断还费 token。
  只回答「做什么 + 何时用」，把「里面有什么」留给正文
- **引用必须存在**：正文里写 `scripts/x.py`、`references/y.md` 就必须真有这个文件；
  有 `scripts/` 目录就必须在正文里说怎么用

四条建议（warning）：

- SKILL.md 超 300 行 → 细节拆到 `references/` 或 `scripts/`
- 目录里不留 `__pycache__` / `.DS_Store`
- description 或正文里要有一句「何时用」（`Triggers:` 或「何时使用」段），否则路由不准
- **`references/` 和 `templates/` 里每个文件都要在正文提到**——写了没人读等于白放。
  `scripts/` 不查，因为脚本可以是内部实现（被别的脚本或 `.cmd` 间接调用）

## 提交署名：用当前模型名

提交时用 `-c` **临时**指定作者名，不要写进仓库配置：

```bash
git -c user.name="DeepSeek-V4.1-Flash" commit -m "..."
```

**为什么不设 `git config user.name`**：仓库配置是持久的，Claude 设完走人，Codex 下次提交就会顶着
「Claude Sonnet 4.5」的名字。每个模型都得在提交那一刻报自己的名字，不能留状态。

- 名字用官方写法：`DeepSeek-V4.1-Flash`、`Claude Sonnet 4.5`、`GPT-5`、`Gemini 2.5 Pro`
- **邮箱不动**（`user.email` 保持用户自己的），否则 GitHub 认不出这是他的提交
- 忘了加 `-c` 只会显示用户名——这是有意的失败方向：宁可不署名，不要串到别的模型头上
- 不确定自己叫什么就跳过，不编名字

## 工具

在仓库目录下运行，配置在 `~/.agents/skillsync.json`：

```bash
python scripts/skillsync.py status        # 各 agent 每个技能的链接状态
python scripts/skillsync.py doctor        # 断链、链式嵌套等结构问题
python scripts/skillsync.py scan          # 多副本漂移报告
python scripts/skillsync.py link --apply  # 把仓库技能分发到各 agent
python scripts/skillsync.py prune         # 清理断链（技能删了、junction 还在）
python scripts/skillsync.py adopt --only <skill> --apply   # 从某 agent 吸收技能进仓库
python scripts/skillsync.py rules --apply # 把本规则块分发到各 agent 全局文件

python scripts/lint_skills.py             # 技能规范检查（只查自建技能，--all 连第三方）
python scripts/lint_skills.py --strict    # warning 也算失败
python scripts/check_consistency.py       # README 与目录双向一致
```

`adopt`、`link`、`rules` 默认 dry-run，不加 `--apply` 不会动任何文件。收编或分发时会自动隔离「正文冲突」的技能（某 agent 的副本 SKILL.md 正文与仓库不同），这类既不分发也不回链，须人工定夺版本。

## 排障

- `find -name SKILL.md` 不跟随 junction，会误报技能丢失。要判断技能是否可用，看该目录项的 `SKILL.md` 能否直接读取。
- 判断某项是否已被纳入管理：**不能只看 `os.path.isjunction()`**。链式 junction（`workbuddy/x → zcode/x → 真实目录`）同样返回 True，但它并没有指向主库。也不能用 `os.path.realpath()`——它会把整条链解析到底，两跳和直连看起来一模一样。要比对 `os.readlink()` 返回的**直接目标**是否等于主库路径。`os.path.islink()` 对 junction 返回 False，不能用来判断。
- 提交前检查已自动化：`.git/hooks/pre-commit` 会跑 README↔目录一致性，并拦截**新增**的链式 junction（历史欠账记在 `scripts/skillsync-baseline.json` 豁免）。机制细节与设计理由见 `agent-skills-sync` 技能。

## 写长文

报告、方案、论文、正式文档、README、汇报材料等长文本，产出草稿后必须过一遍 `humanizer-zh` 技能再交付，去掉模板化表达、套话与 AI 腔，同时保留事实、确定程度和作者声音。润色已有文本同样适用。
<!-- END skillsync-rules -->
