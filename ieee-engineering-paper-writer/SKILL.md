---
name: ieee-engineering-paper-writer
description: "IEEE 与工程类论文的起草、结构、审阅与精修（Transactions / 旗舰会议 / 期刊），覆盖实验系统、硬件失效分析、辐射效应、嵌入式计算、航空航天平台。六个可执行模式：audit / rewrite / causal-chain / forensic / cite-lint / budget-control，附十项工程写作铁律、OS-遥测-电源三维正交失效指纹、drop-in 替换生成、IEEE 单调引用检查。Triggers: ieee paper, engineering paper, 审查论文初稿, 论文修改意见, 润色工程论文, 硬件失效分析, 辐射效应, 排除法归因, 物理因果链, drop-in replacement, 改论文, 审稿."
metadata:
  version: "2.1.0"
  last_updated: "2026-09-25"
  status: active
  supported_modes:
    - audit
    - rewrite
    - causal-chain
    - forensic
    - cite-lint
    - budget-control
  related_skills:
    - academic-paper
    - academic-paper-reviewer
    - deep-research
---

# IEEE Engineering & Systems Paper Writer (v2.1)

Universal methodology, quality standard, and agent orchestration system for authoring, reviewing, and iteratively refining high-impact IEEE engineering research papers (e.g., IEEE Transactions, flagship conferences like IEEE Aerospace, IEEE Satellite, NSREC, RADECS, DAC, ITC) focusing on experimental computer systems, hardware reliability, physical failure analysis, and mission-critical embedded platforms.

---

## 快速调用指南 (Quick Start)

当用户输入带有 `/ieee-engineering-paper-writer`、触发词或指定模式时，自动按以下模式流转执行：

```bash
# 模式 1：严苛审查初稿，生成 Blocker/Major 诊断清单与即插即用替换原句
/ieee-engineering-paper-writer audit 审查初稿并给出可直接替换的原句

# 模式 2：针对特定小节或段落进行工程白话与紧凑去机器腔重写
/ieee-engineering-paper-writer rewrite §2.4 电源分配网络机理段落

# 模式 3：补齐断裂的物理因果链（微观物理 -> 电路拓扑 -> 驱动状态机 -> 宏观电气表征）
/ieee-engineering-paper-writer causal-chain 补齐高能粒子电离到存储介质漏电加速的因果链

# 模式 4：构建三维正交排他法故障树与归因矩阵
/ieee-engineering-paper-writer forensic 构建异常低功耗平台的排他归因矩阵

# 模式 5：文献引用完整性与升序自检（消灭占位符，检查 [1]~[N] 单调升序，核验 DOI）
/ieee-engineering-paper-writer cite-lint 检查正文引用顺序与 References 题录一致性
```

---

## 核心执行模式 (Execution Modes)

### 1. `mode: audit`（顶会/顶刊严苛审查模式）
- **目标**：站在资深 IEEE 审稿人视角，对论文草稿进行无死角审查。
- **输出格式**：强制执行 `templates/audit_report_template.md` 规范：
  1. **核心硬伤诊断清单**：按 `[BLOCKER]`、`[MAJOR]`、`[MINOR]`、`[POLISH]` 四级分类；
  2. **逐节深度诊断与即插即用修改方案**：每一处缺陷必须给出【问题机理】、【待替换原文片段】、【推荐即插即用替换原句（Drop-in Replacement）】；
  3. **下游 Agent 指令流**：给出可供其他写文/修文 Agent 直接消费的执行流。

### 2. `mode: rewrite`（即插即用精修替换模式）
- **目标**：消除翻译腔、机器腔与空泛套话，重构为资深硬件测试工程师的紧凑行文风格。
- **准则**：
  - 以功能实体为主语，物理扰动为修饰，工程后果为谓语；
  - 严禁“进行了深入研究”“底层物理微观扰动”等空泛词；
  - 严格保持学术散文段落（Prose over Lists），段内依靠对比连接词对仗推进。

### 3. `mode: causal-chain`（物理因果链补齐模式）
- **目标**：专治“从微观微缩尺寸直接跳跃到系统整体瘫痪”的逻辑断层。
- **四级强制闭环标准**：
  $$\text{微观物理扰动} \xrightarrow{\text{物理载流子/能量沉积}} \text{电路拓扑/敏感电荷响应} \xrightarrow{\text{状态机/时钟协议失锁}} \text{系统级/总线级可观测表征}$$
- 任何一环不得悬空。例如：阈值电压漂移 $\to$ 判决裕量压缩 $\to$ 固件读取乱码/超时 $\to$ 引导死锁。

### 4. `mode: forensic`（三维正交排他法归因模式）
- **目标**：为硬件异常构建无法辩驳的排除法推演。
- **三维正交指纹矩阵**：
  1. **操作系统与软件层**：Kernel Panic? coredump / ramoops? 驱动硬件事件（如 GPU Xid）? 抑或零报错日志猝死？
  2. **总线通信与遥测层**：调试串口（冻结/乱码/正常）? 控制总线心跳（帧序号中断/校验错）? 高速网络（Link Down / 丢包）?
  3. **供电与电气层**：额定满载/待机功耗? 全局断电? 抑或非对称局部供电瘫痪（残余中间功耗平台）？

### 5. `mode: cite-lint`（引用预算与升序自检模式）
- **目标**：杜绝 IEEE 格式不合规导致的 Desk Reject。
- **合规标准**：
  - **单调升序律**：正文首次引用的文献编号必须为 `[1]`, `[2]`, `[3]`, `[4]`... 严格单调递增，严禁跳序或后号先出；
  - **零占位符**：彻底清理全部 `[REF: ...]` 占位符；
  - **MDPI 配额控制**：全篇正文 MDPI 期刊文献数量 $\le 1$（且需在背景章节严格禁用）；
  - **真实有效性**：所有引文必须具备经 Crossref 官方核实的 DOI 或标准规范编号，零伪造。

### 6. `mode: budget-control`（双栏 6 页版面预算剪裁模式）
- **目标**：严格确保中英文转译与排版后符合 IEEE 6 页硬性上限。
- **页面预算折算基准**：
  - 总文字上限：$\approx 4000$ 英文词 $\approx 6400$ 中文字符；
  - P1 组（标题+摘要+图 1+§I）文字 $\le 450$ 词（$\le 720$ 字）；
  - P6 组（图 5+§VI+§VII+References）文字 $\le 450$ 词（$\le 720$ 字）；
  - 裁减优先级：§VI 展开例证 $\to$ §V 重复机理句 $\to$ §I 宏观铺陈 $\to$ 各节结尾过渡句。

---

## 十项通用工程写作铁律 (The 10 Universal Iron Rules)

详见 [`references/iron_rules.md`](file:///C:/Users/qilin/.gemini/config/skills/ieee-engineering-paper-writer/references/iron_rules.md)，核心摘要如下：

1. **先验中立与论证解耦律**：前置机理与分类学章节客观对称，**严禁提前剧透后续章节的实测结果与异常数值**（杜绝审稿人质疑循环论证）。
2. **物理/电气基线判据不变律**：数字逻辑死锁必定保留额定电压与静态漏电（$\ge$ 待机功耗）；**只有供电网络主动关断才会使功耗跌破空闲基准**。
3. **多尺度时空解耦律**：严格区分系统多阶段级联总跨度（宏观时间线）与物理器件瞬态跳变耗时（瞬态时间线），禁止混淆叙述。
4. **实体具象与工程白话律**：以确定实体为主语，物理扰动为修饰，工程后果为谓语，彻底剔除空泛伪学术词。
5. **对象定性与成熟度边界律**：客观界定受试对象的真实成熟度（TRL），严禁将地面实验样机或候选架构虚夸为在轨已部署系统。
6. **引用单调升序律**：正文引用编号严格按首次出现次序单调单向递增，消灭所有占位符与孤儿引用，拒绝教科书常识空引。
7. **排他归因与负向声明边界律**：未测得底层引脚探针证据时，必须给出严谨的负向声明（Negative Claim），明确界定候选边界，不妄下断言。
8. **零概念空降与上下文引桥律**：任何专业电路拓扑、专用寄存器或异常转储机制在作为因果链登场前，必须提供一句话功能引桥。
9. **论述致密性与散文段落律**：复杂因果推演与归因必须写成致密学术散文段，严禁将理论分析碎化为 PPT 汇报提纲式的子弹项。
10. **有限样本推演谦逊律**：面对稀缺高成本机时与单一工程样机，价值定位为“存在性证明与高保真现场取证基准”，严禁盲目外推为通病缺陷。

---

## 典型反模式与修改范例 (Anti-Patterns Library)

详见 [`references/anti_patterns.md`](file:///C:/Users/qilin/.gemini/config/skills/ieee-engineering-paper-writer/references/anti_patterns.md)，涵盖：
- 机理章节剧透实测现象 $\to$ 先验中立重构；
- 混淆系统级联与功率骤降 $\to$ 分立时间尺度精准重构；
- 因果链跳步断裂 $\to$ 补全微观物理至电路响应传导链条；
- 机器翻译腔 $\to$ 紧凑主谓宾工程表述；
- 缺乏物理参数的薄弱对比 $\to$ 补充试验构型、应力穿透与边界条件的本质差异。

---

## 多 Agent 协同交接协议 (Agent Handoff Protocol)

详见 [`templates/drop_in_replacement_template.md`](file:///C:/Users/qilin/.gemini/config/skills/ieee-engineering-paper-writer/templates/drop_in_replacement_template.md)。  
当负责 Review 的 Agent 使用本 Skill 输出结果时，必须生成规范的 **Patch 格式代码块**，确保下游执行 Agent 可以直接使用 `replace_file_content` 工具精准替换，无需进行二次语义猜测。
