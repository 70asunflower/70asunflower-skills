---
name: layoutfix
description: 给已有 SVG/PDF 图做几何体检和人工微调——把「看着不对」变成可断言的清单，再让人拖两下修掉。当用户说"字压图、文字重叠、文字被挡住了、箭头没接上、标签没居中、超出画布、这张图看着别扭、帮我看看这张图有什么问题、交付前检查一遍、把某个元素挪一下、改图里的文字、文字换行、把箭头接到框上"时使用。适用于论文插图、架构图、流程图、幻灯片导出的 PDF 等任何矢量图；不适用于从零画图（那是 paper-figures 等绘图技能的事），也不适用于位图。
---

# layoutfix：矢量图的版面体检与微调

## 它解决什么

AI 画的示意图常见四类毛病：字压线、文字被盖住、箭头停在半空没接上、标签在框里没居中。
这些用截图看不出来（3px 的重叠在整图里几乎不可见），人也说不清差多少。

layoutfix 不算像素，算**几何**：直接读 SVG/PDF 的矢量数据，输出「哪两个元素、重叠几毫米、差在哪」。

```
$ python layoutfix.py check fig.svg
fig.svg  文字 19 · 形状 6 · 箭头 4
  ✗ 2 处错误 / 0 处警告
    ✗ [text_overlap] 文字重叠 17.6×0.8mm「3.3V CMOS」×「CAN0_DIN G39」
```

## 命令

工具就是本技能目录（各 runtime 的 `skills/layoutfix/`，junction 到仓库
仓库的 `layoutfix/`）。**下面的命令都在该目录下执行**，图可以给绝对路径。

```bash
cd <本技能目录>
PY=python          # 本机装了 pymupdf 的解释器即可

$PY layoutfix.py check  fig.svg              # 体检，人读
$PY layoutfix.py check  fig.svg --json       # 给程序/agent 读
$PY layoutfix.py check  fig.svg --strict     # CI 门禁：有 error 即退出码 7
$PY layoutfix.py tune   fig.svg              # 起本地界面，人拖；顶栏下拉切换同目录其他图
$PY layoutfix.py nudge  fig.svg --id text:4 --dy -4   # 命令行微调（agent 用）
$PY layoutfix.py nudge  fig.svg --id text:4 --dy -4 --expect "DOUT/DIN"   # 带上目标内容，改错就拒绝
$PY layoutfix.py ops    fig.svg              # 看已落地的改动清单
$PY layoutfix.py clean  fig.svg              # 清理清单：剔零位移、合并同元素碎片
$PY layoutfix.py ls     fig.svg              # 列出可拖元素
```

依赖：Python 3.10+ 与 `pymupdf`。零前端依赖、无构建步骤。

> **`text:4` 是位置序号，不是身份证。** 图层置顶/上移会让全图编号前后移，
> 拿着旧编号改不会报错，只会静默改到另一行字上。规则：**动过图层就重新 `ls`**；
> 批量改动时每条都带 `--expect "目标里的几个字"`，对不上它会拒绝并告诉你
> 那个编号现在指着什么。界面没这个坑——`refresh()` 每次重新取带编号的副本。

## 五类检查

| code | 含义 | 判据 |
|---|---|---|
| `text_overlap` | 文字两两重叠 | 重叠高度 > 字号 12%，且面积占比 > 4% |
| `text_occluded` | 文字被后画的不透明形状盖住 | 按绘制顺序（`seqno`）判断，覆盖 > 8% |
| `text_out_of_canvas` | 文字超出画布被裁掉 | 渲染后会**整段消失**，截图看不出来 |
| `arrow_dangling` | 箭头只接上了一头 | 两端都不挨框 = 图例箭头，跳过 |
| `label_offcenter` | `text-anchor=middle` 的标签偏离容器中心 | 偏差 > 1.2mm |

## 三条硬约定（改代码前必读）

1. **存盘只改目标元素，其余字节一个不动。** 字节级读写（`read_bytes`/`write_bytes`），
   属性名正则用 `(?<![\w:.-])`，否则 `\bwidth` 会命中 `stroke-width`。
2. **改文件 + 写清单两者一致。** 每次改动同时写 `<图>.nudge.jsonl`，agent 读尾部几行就知道你动了什么。
3. **撤销必须字节级还原。** `from` 存的是字符串形式的旧值（含 `null`），连续 undo/redo 后文件与原图逐字节相同。

样式类属性（字号/字体/填充）写内联 `style`——CSS 规则优先级高于呈现属性，
图里只要有 `<style>` 块用类定义了 `font-size`，写 `font-size="15"` 就是无效的。

## 界面只管版面

`tune` 打开的面板有：**位置、宽高、字号、对齐、图层**，外加三件 Word 式的：
**图内文字编辑**（双击文字，直接在图上打字，浮层所见即所得）、**折行宽度**
（拖文字右下角手柄，文字按宽度实时重排——CJK 按字折、拉丁按词、超长 URL 硬切）
和**箭头端点**（选中线段出现两个圆点手柄，拖端点自动吸到框边/中心/格点，
悬空箭头一拖就接上）。多行都落在 tspan 上，行距沿用图里已有节奏。

颜色 / 字体 / 加粗**故意不给界面入口**——那是设计决定，归 agent。人在界面上调一个颜色，
就会和整张图的视觉体系脱节。`edit.py` 的接口照样支持这些属性，只是不暴露给人点。
增删元素也不做——内容结构归 agent，人在既有元素上调数值。

## 和其他技能的分工

- **从零画图** → `paper-figures`（matplotlib / PPT / Origin 那几条管线）
- **画完检查版面** → 本技能 `check`
- **要看渲染效果** → `paper-figures/scripts/preview.py`（SVG/PDF 直出 PNG）
  或 `snap`（HTML 海报、演示页）
- **只截违例区域**：`check --json` 里的 `region` 直接喂 `preview.py --clip`

## 文档

- `README.md` — 用法、15 条实现坑、已知边界、谁决定什么
- `DESIGN.md` — 架构、模块契约、阈值、测试矩阵、扩展指南

改内部实现前读 `DESIGN.md`；只调参或加检查项看 `README.md` 的坑列表。
