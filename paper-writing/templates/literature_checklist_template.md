# 参考文献真实性与引据溯源核查清单模板 (Literature Backfill & Audit Checklist)

> **核查目的**：确保工程研究论文引用的全部文献具备**100% 真实性（杜绝 AI 幻觉）**、**严格单调升序律（Monotonic Citation Order）**、**正文双向引据精准支撑（零错位）**与**零孤儿文献**。

---

## 一、 参考文献速查与单调升序矩阵

| 编号 | 题名简写与权威出版物 | 权威检索号 / DOI | 正文首次引证位置 | 真实性状态 | 支撑论断摘要 |
|:---:|:---|:---:|:---:|:---:|:---|
| **[1]** | Satellite Mobile Edge Computing (IEEE Network 2019) | 10.1109/MNET.2018.1800172 | §I 引言段落 1 | ✅ 真实有效·精准契合 | 天基移动边缘计算架构与带宽压力缓解 |
| **[2]** | In-orbit Computing: An Outlandish thought Experiment? (ACM HotNets 2020) | 10.1145/3422604.3425937 | §I 引言段落 1 | ✅ 真实有效·精准契合 | 太空数据中心与在轨大模型/高通量计算需求 |
| **[3]** | Comparative Analysis with Space Processors (AIAA JAIS 2025) | 10.2514/1.I011421 | §I 引言段落 1 | ✅ 真实有效·精准契合 | 传统抗辐照宇航芯片算力落后商用平台 30 倍以上 |
| **[4]** | COTS Devices for Space Missions in LEO (IEEE Access 2024) | 10.1109/ACCESS.2024.3405373 | §I 引言段落 1, 2; §III-A | ✅ 真实有效·精准契合 | COTS 器件在低轨力学/热控成熟方案及 1.5~2.0 mm 铝屏蔽 |
| **[5]** | Radiation Qualification via SLT (MDPI Electronics 2022) | 10.3390/electronics11030378 | §I 引言段落 2, 3 | ✅ 真实有效·精准契合 | 系统级测试 (SLT) 捕获复杂跨芯片耦合失效的不可替代价值 |
| **[6]** | The Φ-Sat-1 Mission: First On-Board DNN (IEEE TGRS 2022) | 10.1109/TGRS.2021.3125567 | §I 引言段落 3 | ✅ 真实有效·精准契合 | 在轨 AI 加速器验证多偏向算法，缺乏微观电轨遥测 |
| **[7]** | Basic mechanisms and modeling of SEU (IEEE TNS 2003) | 10.1109/TNS.2003.813129 | §I 引言段落 3; §II; §III-A; §VI-A | ✅ 真实有效·精准契合 | 单粒子电荷收集微观机理与泊松随机性 |
| **[8]** | SEE & TID on Jetson Orin AGX SoM (IEEE REDW 2023) | 10.1109/REDW61050.2023.10265818 | §I 引言段落 3; §II; §V-D | ✅ 真实有效·精准契合 | 针对 Orin 模组实测证实外围供电/存储芯片更易发生辐射损坏 |
| **[9]** | Radiation Effects on Embedded GPUs (IEEE TNS 2025) | 10.1109/TNS.2025.3528764 | §I 引言段落 3; §II; §V-D | ✅ 真实有效·精准契合 | 嵌入式异构 GPU 在高能粒子下的 Xid 驱动崩溃与控制流挂起 |
| **[10]** | Scaling Trends of Digital SEE (IEEE TNS 2021) | 10.1109/TNS.2020.3044659 | §II 逻辑功能域; §III-A | ✅ 真实有效·精准契合 | 先进纳米节点临界电荷下降致 SEFI/SET 敏感性剧增 |
| **[11]** | Radiation on Retention of DDR4 (IEEE TNS 2023) | 10.1109/TNS.2023.3288747 | §II 逻辑功能域 | ✅ 真实有效·精准契合 | 辐射诱发高密度内存多位翻转 (MBU) 超出 ECC 纠错窗触发 MCE |
| **[12]** | Effects of Scaling in SEE on NAND Flash (IEEE TNS 2010) | 10.1109/TNS.2010.2084102 | §II 逻辑功能域 | ✅ 真实有效·精准契合 | 闪存控制器 SEFI 诱发读写停摆与块设备 I/O 挂起 |
| **[13]** | Radiation Effects in Power Systems: A Review (IEEE TNS 2013) | 10.1109/TNS.2013.2262235 | §II; §V-C; §VI-B | ✅ 真实有效·精准契合 | 开关调压器 (PMIC/VRM) 控制链路 SEFI 误触发欠压锁定 (UVLO) |
| **[14]** | Design of a Radiation Hardened POR (IEEE TNS 2018) | 10.1109/TNS.2018.2840326 | §II; §V-C; §VI-B | ✅ 真实有效·精准契合 | 残存供电分压高于负向输入阈值 ($V > V_{\text{IT-}}$) 导致 POR 无法激活 |
| **[15]** | Inner radiation belt simulations of SAA (JSWSC 2021) | 10.1051/swsc/2021031 | §III-A 束流选取; §VI-B 带外加固 | ✅ 真实有效·精准契合 | 南大西洋异常区 (SAA) 高倾角低轨数十 MeV 质子能谱与年注量 |
| **[16]** | ESCC Basic Specification No. 25100 (ESA 2014) | ESA ESCC 25100 | §III-A 束流选取; §VI-A 统计分析 | ✅ 真实有效·精准契合 | 欧洲空间局法定单粒子测试规范与注量率控制准则 |
| **[17]** | Test Standard for Proton SEE (JEDEC JESD234 2013) | JEDEC JESD234 | §III-A 束流选取 | ✅ 真实有效·精准契合 | JEDEC 质子单粒子效应测试能量与注量率控制标准 |
| **[18]** | Temperature-Aware Computer Systems (IEEE Micro 2003) | 10.1109/MM.2003.1261387 | §IV-B 功耗特征 | ✅ 真实有效·精准契合 | 芯片停机后结温回落导致静态漏电线性/指数衰减物理机理 |
| **[19]** | Probability model for solar proton fluences (IEEE TNS 2000) | 10.1109/23.856469 | §IV-B 停摆注量与在轨等效 | ✅ 真实有效·精准契合 | 空间高能质子累积注量概率模型与 1~2 年在轨等效换算 |
| **[20]** | Jetson AGX Thor Carrier Board Specification (NVIDIA 2025) | NVIDIA DA-11666-001 | §IV-B 硬件复位尝试 | ✅ 真实有效·精准契合 | 原厂载板工程规范与 `SYS_RESET_N` 硬件复位有效触发电气条件 |

---

## 二、 逐篇双向引证与原文机理核查标准结构

每条文献档案按以下 5 项要素标准化建立：
1. **标准引用题录**：作者、文章名、期刊/会议、卷号、期号、页码、年份、DOI；
2. **正文中文引证句**：在中文稿中的具体段落与上下文；
3. **正文英文引证句**：在英文 LaTeX 中的具体 `\cite{...}` 原文；
4. **参考文献官方原文/摘要摘录**：文献原文中的关键句（摘录 2~4 句核心结论）；
5. **真实性与机理支撑判定**：核查该文献是否完全支撑正文论断，判定通过。
