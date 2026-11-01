# WorkBuddy / ZCode Custom Skills

把个人经验和工作流沉淀成技能：做过的事、踩过的坑、验证过的流程，写成一个可复用的技能，
下次直接调用，不用重新想一遍。

同时解决一个工程问题：这些技能要给 **Claude / Codex / ZCode / Gemini / WorkBuddy** 五个 agent
共用，但不能靠"每个目录放一份"——那样必然漂移。做法和理由见下方「设计思路」。

## 设计思路

技能本身是内容，真正的设计在**怎么分发给多个 agent**：

| 做法 | 后果 |
|---|---|
| 每个 agent 目录各放一份副本 | 改了一处忘另一处，两周后 6 份内容各不相同，且分不清哪份是对的 |
| 一个仓库 + 目录联结（junction） | 只有一份文件，改哪里都是改这一份 |

所以：**仓库是唯一真相源，各 agent 的 skills 目录里放的是指向仓库子目录的联结，不是副本。**
Antigravity 不支持 junction，走 `~/.gemini/config/skills.json` 原生声明式直挂主库。

由此推出三条硬规矩：

1. **不复制、不另存、不"先备份一份"**——副本会立刻漂移，旧版本靠 git 历史取回
2. **新增技能建在仓库里** `<skill>/SKILL.md`，不在 agent 目录下新建真实目录（会脱离仓库）
3. **删技能必须同步清理联结**——主库删了目录，各 agent 里那条 junction 会变成指向空路径的空壳，
   不报错但行为不可预期（一次删 7 个技能会在 6 个 agent 目录里留下 42 条断链）

第三方技能是例外，**按渠道各自保留、不入库**：它们渠道参数不同，不是版本差异。

## 依赖

共享机制依赖 [`agent-skills-sync`](./agent-skills-sync/) 这一个技能：

- **分发**：把仓库子目录挂成各 agent 的 junction
- **体检**：`skillsync.py doctor` 查断链 / 链式嵌套 / 主库含链接
- **漂移**：`scan` 找多副本差异，`prune` 清断链
- **设计理由**：这套机制为什么这么定，写在它的 `SKILL.md` 里

没有它，这个仓库只是一堆文件夹；换机器、加新 agent 时按它的说明重建。

## Skills 列表

按**用途**分组。标 `personal` 的绑了个人路径 / 账号 / 登录态，别人装了要改；
其余可以直接拿去用（个别技能含本机解释器路径，按需改一行）。

### 学术与论文 — 写、审、画图、调研报告

| 技能 | 说明 |
|---|---|
| [paper-writing](./paper-writing/) | 工程论文写作：六个可执行模式（audit / rewrite / causal-chain / forensic / cite-lint / budget-control）+ 十项铁律 + 反模式库 + IEEE 会议模板 + 引用升序与投稿打包脚本；审阅归 paper-review、画图归 paper-figures |
| [paper-review](./paper-review/) | LaTeX/IEEEtran 论文投稿前审阅与修改：本机编译环境、静态健康、句级审阅、术语与引用、图表与陈述强度一致性 |
| [paper-figures](./paper-figures/) | 学术图表统一入口：matplotlib 投稿矢量图 / Origin 可编辑直通 / python-pptx 示意图三条管线按用途路由；含期刊海报与图文摘要模板、色盲安全检查、视觉一致性校验 |
| [deep-research-report-pipeline](./deep-research-report-pipeline/) | 工程决策类深度调研报告流水线：全网调研 → 分章撰写 → 独立审稿（数字比对 + 独立重算）→ 跨章对齐 → 语言优化 → 整合交付 |

### 图与视觉 — 把内容做成图、检查图有没有毛病

| 技能 | 说明 |
|---|---|
| [visual-diagrams](./visual-diagrams/) | 把内容做成图：信息卡长图（HTML/CSS + Playwright）、示意图流程图（手写 SVG → Chrome → 思源）、技术架构图（调用外部 fireworks 风格库）。按输出类型路由，含命名/导出/校验约定；论文数据图与海报归 paper-figures |
| [snap](./snap/) | 零依赖页面截图/体检/像素对比 CLI：无头 Chrome 一条命令截图（整页/元素/区域/高清），--audit 程序化检坏图溢出裁切，--diff 视觉回归；agent 确认页面渲染效果首选 |
| [layoutfix](./layoutfix/) | 矢量图版面体检与人工微调：查字压图/文字被盖/超画布/箭头悬空/标签偏心，输出毫米级违例清单（--strict 可做交付门禁）；tune 起本地界面人拖即存盘，改动落成可重放的 delta 清单 |

### 文档与写作 — 格式转换、排版规范、教程生成

| 技能 | 说明 |
|---|---|
| [md-to-70asunflower-latex](./md-to-70asunflower-latex/) | 将 Markdown 技术博客转换为 70asunflower 风格的 LaTeX 文档，适配 Overleaf XeLaTeX 编译 |
| [md2docx-formal](./md2docx-formal/) | 将 Markdown 中文工程文档转换为规范排版的 Word（A4、篇/章/节标题层级、1.5 倍行距、自动目录、页眉页脚、GB/T 7714 引用上标），并支持源文档一致性审查 |
| [strict-docx-audit](./strict-docx-audit/) | docx 转换后的质量闸：12 项结构与排版检查 |
| [doc-plain-zh](./doc-plain-zh/) | 中文文档可读性转换：拗口 → 通顺，只改表达、不改逻辑与事实，保持书面正式 |
| [tutorial-writer](./tutorial-writer/) | 为初学者生成详细、正确、图文并茂的学习文档/教程：调研核验 → 依赖排序大纲 → 写作 → 配图（svg-diagram-pipeline）→ 润色（humanizer-zh）→ 三道门自查 → 交付（本地 md，可选思源） |
| [ai-tutorial-pipeline](./ai-tutorial-pipeline/) | 用网页版 AI 按大纲逐章生成高质量教程并自动入库思源笔记，含浏览器接管、表格/公式格式校验 |

### 笔记与知识库 — 思源 / Notion 的读写、排版与备份

| 技能 | 说明 |
|---|---|
| [siyuan-kernel-ops](./siyuan-kernel-ops/) | 通过思源内核 HTTP API 安全检索/读写/批量处理笔记库，含端口漂移、上传、索引滞后等坑位手册 |
| [siyuan-backup-sync](./siyuan-backup-sync/) | 思源笔记数据仓库的 Git 备份/同步工作流 |
| [siyuan-markdown-formula-formatter](./siyuan-markdown-formula-formatter/) | 思源专用 Markdown/LaTeX 公式排版规范，彻底解决公式渲染失败 |
| [notion-im-helper](./notion-im-helper/) | 通过 IM 向 Notion 添加内容，支持闪念速记、待办清单、标题、引用、列表等多种格式 |

### 工程与项目 — 项目脚手架、代码修改、CAD、工具链维护

| 技能 | 说明 |
|---|---|
| [agent-skills-sync](./agent-skills-sync/) | 多 agent（WorkBuddy/Claude/Codex/ZCode/Gemini）共享用户级技能的单一真相源：junction 分发、状态矩阵、漂移分类与冲突保护 |
| [project-init](./project-init/) | 项目初始化 + 多 agent 规范生成（AGENTS.md + 7 个 agent 入口）+ 巡检修复器 |
| [project-review](./project-review/) | 项目六维审查评分 + 审计报告，与 project-init 互补 |
| [notebook-patching](./notebook-patching/) | Jupyter Notebook (.ipynb) 与 IDE 打开状态下的受限文件快速安全修改工作流，规避内联转义与 Auto-Save 内存覆盖冲突 |
| [3d-printing-cad-design](./3d-printing-cad-design/) | 3D 打印机械 CAD 全流程：build123d / CadQuery 参数化建模、水密性网格校验、STEP→GLB 离线预览、制造交付打包 |
| [feishu-bot-config](./feishu-bot-config/) | 飞书机器人配置管理工具，自动化添加、管理和排查飞书机器人集成 |

### 个人工作流 — 绑了个人路径 / 账号 / 登录态，别人装了要改

| 技能 | 说明 |
|---|---|
| [investment-analysis](./investment-analysis/) | `personal` · 个人投资分析方法论与操作规程（林奇六分类 + 预测档案系统），含个人工作区路径 |
| [captain-resource](./captain-resource/) | `personal` · 资源入库助手，将 URL/文章/工具等添加到 ai-learning-journey、embodied-ai-learning、ic-chip-design-learning 三个学习仓库 |
| [xhs-pipeline](./xhs-pipeline/) | `personal` · 小红书信息收集流水线（profile 驱动：搜索/抓取/审读/合并入库），依赖本机浏览器登录态 |
| [trek-mcp-ops](./trek-mcp-ops/) | `personal` · 自部署 TREK 旅行规划器（Docker + 内置 MCP 135 工具）的启停/建行程/排障手册，含本机端口与代理配置 |

## 标签说明

- **分组**（学术与论文 / 图与视觉 / 文档与写作 / 笔记与知识库 / 工程与项目 / 个人工作流）按**用途**划分，方便找。
- **`personal` 标记**：绑了个人路径、账号或登录态，别人装了需要改配置才能用。没标的可以直接用。

## 使用方式

把 skill 文件夹复制到对应 agent 的 skills 目录即可使用（本机改用目录联结，做法见「管理本仓库」一节）。

- WorkBuddy：`~/.workbuddy/skills/`
- Claude Code：`~/.claude/skills/`
- Codex：`~/.codex/skills/`
- ZCode：`~/.zcode/skills/`
- Gemini CLI：`~/.gemini/config/skills/`
- Antigravity：`~/.gemini/config/skills.json`（原生声明式直挂主库，避开 Windows Junction 限制）

## 外部技能

除上表收录的自制技能外，本机还统一管理着一批外部技能——包括 `humanizer-zh`（去 AI 味润色，MIT，来自 op7418/Humanizer-zh）、`kimi-webbridge`（浏览器接管）、`mcporter`（MCP 调度）、`fireworks-tech-graph`（SVG 图形）等。它们以完全相同的 junction 方式分发到各 agent，但**不纳入本仓库版本控制**（见 `.gitignore` 的 `skillsync` 标记区块），只随目录存在于本机。

其中 `humanizer-zh` 已被定为**写长文时的固定动作**：报告、方案、论文、正式文档、README、汇报材料等长文本，产出草稿后过一遍该技能再交付。

这些技能在主库里的位置示意：

```
70asunflower-skills/
├── agent-skills-sync/     自制
├── siyuan-kernel-ops/     自制
├── humanizer-zh/          外部 · 去 AI 味润色（写长文必过）
├── kimi-webbridge/        外部 · 浏览器接管
└── mcporter/              外部 · MCP 调度
```

## 管理本仓库

以下命令都在仓库根目录执行。

### 常用命令

```bash
python scripts/skillsync.py status          # 每个 agent 每个技能的链接状态矩阵
python scripts/skillsync.py doctor          # 断链 / 链式嵌套 / 主库含链接；应为「问题数: 0」
python scripts/skillsync.py scan            # 多副本漂移报告
python scripts/skillsync.py prune           # 清理断链（默认 dry-run，加 --apply 才删）
python scripts/lint_skills.py               # 技能规范检查（frontmatter / 描述长度 / 引用 / BOM）
python scripts/check_consistency.py         # README 与技能目录双向一致
```

### 三种改动的完整流程

| 做什么 | 动手 | 收尾（缺一步都算没做完） |
|---|---|---|
| **改**已有技能 | 直接编辑 | `lint_skills.py` 无 error |
| **加**新技能 | 建 `<skill>/SKILL.md` + 在 README 加一行 | `link --apply` → `doctor` 回 0 |
| **删**技能 | `git rm -r <skill>` + 从 README 删行 | `prune --apply` → `doctor` 回 0 |

**`doctor` 不返回「问题数: 0」就不要说已完成。** 删技能尤其容易漏：主库删了目录，各 agent
里那条 junction 变成指向空路径的空壳，不报错但行为不可预期。一次删 7 个技能会在 6 个 agent
目录里留下 42 条断链。

提交时 `.git/hooks/pre-commit` 会自动跑**一致性 + 技能规范 + 结构**三道闸门，有 error 直接拒绝。

### 第三方技能

本仓库是公开仓库，只收录自制技能。第三方技能（Wind/Kimi 官方、Academic pack、FBSir、
fireworks-tech-graph 等）由 skillsync 收编到本机，在 `.gitignore` 的 `skillsync` 标记区块中排除——
随目录存在但不入库，也不参与 README 校验。判定为第三方的不能只看「git 未跟踪」，那和「刚建的
新技能」无法区分；区块现在**只减不增**，要排除新目录得显式 `skillsync.py gitignore --add <name>`。

### 规范与约定

技能怎么写、提交怎么署名、维护时该删什么，统一记在 [`AGENTS.md`](./AGENTS.md)——那是唯一权威源，
改完跑 `python scripts/skillsync.py rules --apply` 分发到各 agent 的全局指令文件。
细节展开见 [`agent-skills-sync`](./agent-skills-sync/) 技能。

`scripts/sync_zcode_skills.py` 已废弃并内置拒绝执行的保护——旧逻辑是「先删除仓库目录、再从
agent 目录复制」，在 junction 布局下方向相反，会把仓库内容覆盖掉。
