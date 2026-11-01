---
name: visual-diagrams
description: "把内容做成一张图：信息卡长图、示意图/流程图、技术架构图。按输出类型路由三条路径——① 信息卡与长图海报走 HTML/CSS + Playwright 出 PNG（深色杂志风设计规范）；② 示意图/流程图/电路图手写 SVG，Chrome 渲染后上传思源；③ 技术架构图调用外部 fireworks 风格库（12 种现成风格）。含命名、导出、校验的通用约定。Triggers: 做一张图, 信息卡, 长图, 示意图, 流程图, 架构图, 画个图解释, 把这段内容做成图, 配图, 技术图, 可视化一段内容."
---

# visual-diagrams：把内容做成图

## 先选路径

| 要什么 | 走哪条 | 关键特征 |
|---|---|---|
| **信息卡 / 长图海报**（文章要点、对比、清单） | ① HTML + CSS | 排版驱动，深色杂志风，导出 PNG |
| **示意图 / 流程图 / 电路图**（每个元素都要精确控制） | ② 手写 SVG | 几何驱动，可交互，插进思源文档 |
| **技术架构图 / 系统图**（要现成风格库，不想从零画） | ③ fireworks | 调用外部库，12 种风格一键切换 |

判断口径：**内容为主、版式为辅 → ①**；**结构为主、要精确到坐标 → ②**；**要好看且不想调细节 → ③**。

## 路径 ①：信息卡与长图

用 HTML/CSS 排版，Playwright 截图成 PNG。适合"把一篇文章/一段话变成一张能发出去的图"。

```bash
python scripts/screenshot.py card.html -o card.png --viewport 900x1200 --scale 2
```

- 设计规范（字体层级、深色配色变量、卡片框架、移动端适配、布局模式）见
  `references/infographic-design.md`
- 文件命名用 kebab-case，英文优先
- 先输出一句分析「信息密度 高/中/低 → 采用 X 栏布局」，再出 HTML

## 路径 ②：手写 SVG 示意图

自己画 SVG，Chrome 渲染成 PNG，上传思源 assets 后插图。

```bash
python scripts/build_mini.py <图名>        # 生成骨架
scripts/shoot.bat <svg> <png>              # 无头 Chrome 渲染
python scripts/upload_swap_asset.py <png>  # 上传思源并替换引用
```

- 完整五步流程（绘制 → 渲染 → 上传 → 插图 → 校验刷新）与 MOSFET 电路符号语法见
  `references/svg-pipeline.md`
- 画完先自检：文字不压线、箭头接到框、标签居中——这些交给 `layoutfix` 技能断言，别靠截图看

## 路径 ③：技术架构图（fireworks）

调用 `fireworks-tech-graph` 技能（第三方，物理在仓、git 不跟踪——见根目录 .gitignore 的 skillsync 区块）生成架构图、数据流、时序图、C4、云部署等。

- 12 种风格清单、命令模板、样式选择见 `references/fireworks-styles.md`
- 质量契约与风格细则见 `references/composition-quality-contract.md`、
  `references/style-1-flat-icon.md`——**风格规则真相源在 `../fireworks-tech-graph/references/`**，
  本目录内同名文件是同步快照，改样式先改那边再同步过来
- 导出 PNG 用 `scripts/png_export.js`

## 通用约定

- **命名**：kebab-case，英文优先，同一批图前缀一致（`fig-`、`card-`、`arch-`）
- **导出**：PNG 至少 2 倍图；要印刷或放大时给 SVG/PDF 而非位图
- **校验**：矢量图交付前跑 `layoutfix check --strict`，查字压图、超画布、箭头悬空
- **入库思源**：图片走 assets 上传再引用，不要用外链

## 与 paper-figures 的边界

本技能做的是**通用图解**（信息卡、流程示意、架构图）。
**论文里的数据图、多子图拼版、Graphical Abstract、学术海报**归 `paper-figures` 技能，
那边有期刊版面预设和色盲质检，别在这里重复造。

## 自检

出图后按序确认：

1. 文字有没有压到线或框上（`layoutfix check`）
2. 导出尺寸够不够（PNG ≥ 2x，印刷要矢量）
3. 文件名与目录符合命名约定
4. 插进文档后引用路径对不对
