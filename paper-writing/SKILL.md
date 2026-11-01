---
name: paper-writing
description: "工程类学术论文的写作与打磨：从故事线、大纲、初稿，到引用校验、版面预算、投稿打包。六个可执行模式——audit（严苛审查）、rewrite（精修替换）、causal-chain（物理因果链补齐）、forensic（三维正交排除归因）、cite-lint（引用升序自检）、budget-control（双栏页数预算剪裁）。含十项工程写作铁律、反模式库、IEEE 会议模板与投稿清单。Triggers: 写论文, 起草论文, 论文初稿, 论文结构, 改论文, 润色论文, 论文修改意见, 因果链, 归因分析, 引用升序, 页数超了, 版面预算, 投稿打包, IEEE paper, engineering paper."
---

# paper-writing：工程论文写作

面向 IEEE Transactions / 旗舰会议 / 期刊的工程类论文（实验系统、硬件失效、辐射效应、嵌入式计算、航空航天）。

## 六个可执行模式

| 模式 | 什么时候用 | 产出 |
|---|---|---|
| `audit` | 初稿写完，投稿前严苛自查 | 问题清单（按严重度排序）+ 审计报告 |
| `rewrite` | 某段/某节要精修，要能直接替换 | 即插即用的替换段落 |
| `causal-chain` | 有现象、有结论，中间缺物理因果 | 补全的因果链（机制 → 观测量 → 结论） |
| `forensic` | 故障归因说不清，审稿人会追问 | 三维正交排除表（见下） |
| `cite-lint` | 引用编号乱、有孤儿、跳号 | 单调升序的引用表 + 修正建议 |
| `budget-control` | 页数超了 | 按损失从小到大剪裁后的版本 |

`audit` 的报告模板 `templates/audit_report_template.md`，`rewrite` 的替换模板
`templates/drop_in_replacement_template.md`。

## 从零到投稿

1. **定故事线**：一句话说清「解决什么问题、凭什么解决、证据是什么」。写不出这句话就别开始写正文。
2. **先大纲后成文**：每节先列 3–5 条要点，再扩写。跳过这步的初稿通常要重写。
3. **证据先于结论**：每个结论后面必须挂一个可核验的观测（数字、图表、引用）。
4. **归因用排除法**：见 `references/causal_attribution.md`，模板
   `templates/elimination_framework_template.md`
5. **引用与文献**：找范本/选刊用 `references/find-papers-by-venue.md`（按 venue + 主题查高被引论文）；
   维护回填清单 `templates/literature_checklist_template.md`，跑 `scripts/check_monotonic_citations.py`
6. **版面预算**：`references/submission_packaging.md`，IEEE 模板
   `templates/paper_en_ieee_template.tex`、`templates/paper_zh_template.md`
7. **图**：矢量 PDF 进终稿，`scripts/convert_figures.py --dpi 300` 出预览
8. **打包投稿**：`scripts/sync_mirror_and_pack.py`，清单见 `references/submission_packaging.md`

完整走一遍的范例（卫星边缘计算方向，8 个阶段）见 `references/satellite-case.md`——
那是**案例**，不是模板；卫星专有的遥测/质子束/冷断电阈值别套到别的领域。

## 十条铁律里最常踩的四条

全文见 `references/iron_rules.md`，反模式库见 `references/anti_patterns.md`。

1. **每个数字都要能溯源**——「性能提升 30%」必须写清相对什么基线、什么条件下测的
2. **主张强度要一致**——正文说「显著改善」，摘要不能说「彻底解决」
3. **不要用营销词**——*revolutionary* / *breakthrough* / *unprecedented* 换成可测量的描述
4. **未验证的机制要模糊化**——实验时没启用的功能，不要暗示它参与了结论

会议特有的硬规则见 `references/ieee_conference_iron_rules.md`。

## 常用脚本

```bash
python scripts/check_monotonic_citations.py --tex paper.tex --checklist _文献回填清单.md
python scripts/convert_figures.py --input-dir figures/ --dpi 300
python scripts/sync_mirror_and_pack.py --src . --out submission.zip
```

## 和别的技能怎么分

| 任务 | 归谁 |
|---|---|
| **写 / 改 / 归因 / 引用 / 页数** | 本技能 |
| **审阅已完成的稿子**（句级、术语、图表编号、LaTeX 静态健康） | `paper-review` |
| **画论文图**（数据图、多子图、Graphical Abstract） | `paper-figures` |
| **检查图有没有压字、超画布** | `layoutfix` |

写作过程中会反复用到后三个，但**不要在本技能里重复它们的方法**——那是漂移的起点。

## 自检

投出去之前：

1. 一句话故事线能说清吗
2. 每个结论都有可核验的观测挂着吗
3. `check_monotonic_citations.py` 通过吗
4. 页数在限制内吗
5. 图是矢量、字体嵌入了吗
6. 打包里没有中间文件吗
