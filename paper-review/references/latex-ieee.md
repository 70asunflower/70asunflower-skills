# IEEEtran 双栏论文：版面算术与操作

面向 IEEE conference 模板（`IEEEtran.cls`）的双栏论文。数值基于 A4/Letter 双栏、10 pt 正文的常见配置，
**用前按自己模板实测校正一次**。

---

## 1. 长度单位与换算

| 量 | 典型值 | 说明 |
|---|---|---|
| `\columnwidth` | 252 pt ≈ 3.50 in | 单栏宽 |
| `\textwidth` | 516 pt ≈ 7.17 in | 双栏通栏宽 |
| 正文行高 | ≈ 11.5 pt | 单栏每行占 1 栏宽 × 11.5 pt |
| 参考文献行高 | ≈ 9.0 pt | 比正文密 |
| 一页可用 | ≈ 2 × 9.25 = 18.5 栏英寸 | 扣掉页眉页脚后的净高 |

**栏英寸（column-inch）**：把任何浮动体折算成"占满一栏时的等效高度"：
- 单栏图：`栏英寸 = 放置高度(in)`
- 通栏图：`栏英寸 = 2 × 放置高度(in)`（占两栏宽）

**行数折算**：`行数 = 栏英寸 × 72 ÷ 行高(pt)`。参考文献 3 行 = 3 × 9.0 ÷ 72 = 0.375 栏英寸。

🔴 **这个换算是保守的**。实际编译对少量增行有吸收能力（末页余量、浮动体排布松紧）。
不要仅凭"栏英寸不够"就主张删内容——**先真实编译**。

---

## 2. 图片放置尺寸

```
放置高度(in) = 栏宽(in) × 宽度系数 ÷ 图片宽高比(AR)
AR = 图片宽(pt) ÷ 图片高(pt)
```

用 PyMuPDF 读图片实际尺寸：

```python
import fitz
d = fitz.open("figures/fig1.pdf")
r = d[0].rect
print(r.width, r.height, "AR =", r.width / r.height)
```

**缩图的两种方式**：

| 方式 | 效果 |
|---|---|
| 改 `\includegraphics[width=…]` | 等比缩放，**图内字号同步缩小** |
| 改绘图脚本的 `figsize`（图形用归一化坐标绘制时） | 只压扁画布，**图内字号不变** —— 优先用这种 |
| 重排版式（横构图 ↔ 竖构图） | 改变 AR，可在不缩字号的前提下改变占用高度 |

🔴 缩到印出字号低于约 5 pt 前先问作者。缩图比例记入日志。

🔴 **图件重出/替换后必须立即重测页数。** AR 一变，占用高度就变，页数跟着变——**与正文字数无关**。
实测：某图由横版 `453x380 pt` 改为竖版 `255x274 pt`，按 `0.85` 栏宽印出高度由 **175.7 pt 涨到
224.5 pt（+49 pt ≈ 5 行）**，全稿 **6 页变 7 页**；换回原画布即恢复 6 页。同一份源码、其余一切不变，
所以"文本没动就不用重编"是错的。

缩宽的阈值**必须实测，不能算**：该次实测 `0.72`、`0.70` 仍 7 页，`0.68`、`0.66` 才回 6 页。缩到 0.68
后印出宽度从 209 pt 降到约 167 pt，**图内字号同步缩小** ⇒ 更好的解法是把面板改成更宽的构型
（用满 `0.9–0.95\columnwidth`）或拆成两栏，而不是一路缩窄。

---

## 3. 浮动体行为

| 说明符 | 允许位置 |
|---|---|
| `[!t]` | 只许页顶 |
| `[!b]` | 只许栏底 |
| `[!tb]` | 页顶或栏底 |
| `[!htbp]` | 任意（模板不一定允许） |

- **`figure*`（通栏）只能排页顶**。放不下就整页留白，编译日志出现
  `Underfull \vbox (badness 10000)`。**这是隐形的版面浪费，比面积差本身影响更大**——优先考虑把通栏图改单栏。
- 浮动体"够不上页顶"会被推后并给当前页留白。页顶紧张时把 `[!t]` 放宽到 `[!tb]` 能显著减少空白。
- 这些分数由模板决定，**默认值不要去改**：

| 参数 | class 默认 | 常见被改成 | 后果 |
|---|---|---|---|
| `\topfraction` | 0.7 | 0.95 | 浮动体可吃满一页，正文被挤走，整页留白 |
| `\textfraction` | 0.2 | 0.05 | 同上 |
| `\bottomfraction` | 0.3 | 0.85 | 页底大量浮动体 |
| `\floatpagefraction` | 0.5 | 0.8 | 浮动页判定放宽 |

🔴 改这些是**为通栏大图设的权宜之计**。一旦通栏浮动体归零，应回落到 class 默认——既修版面，
也在模板合规上更安全。

---

## 4. 模板合规（易被忽略的拒稿点）

IEEE 会议条款通常要求**未修改**的模板，明令禁止用额外命令或宏包覆盖默认排版，包括行距、字号、页边距；
违规可能"不经评审直接拒稿"。`IEEEtran.cls` 自身也会在检测到行距被改时打印 WARNING。

**自检**：打开官方模板原文件，数一遍 preamble 里的排版设置条目。自己论文的 preamble 里
每一条额外设置都属偏离，逐条问"真的需要吗"。

---

## 5. 提交包

- **路径唯一**，就地更新，不要另建副本（版本由 git 承担）。
- 结构：`main.tex` / `references.bib` / `IEEEtran.cls` / `main.log.md` / `figures/`。
  **不含图源文件（`*.pptx` 等）**——Overleaf 编译不需要。
- 更新流程（原子、可验证）：

```python
import zipfile, hashlib, shutil, os
tmp = ZIP + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(SRC):
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in {".pptx"}:
                continue
            full = os.path.join(root, f)
            z.write(full, os.path.relpath(full, SRC).replace("\\", "/"))
with zipfile.ZipFile(tmp) as z:                       # 1) 结构完整
    assert z.testzip() is None
for full, rel in items:                               # 2) 逐字节一致
    assert hashlib.sha256(open(full, "rb").read()).hexdigest() == \
           hashlib.sha256(zipfile.ZipFile(tmp).read(rel)).hexdigest()
shutil.move(tmp, ZIP)                                 # 3) 原子替换
```

`shutil.move` 覆盖时不要写成"先删再拷"——中间态若被打断会丢掉旧包。

---

## 6. 修改论文的固定动作

1. `git status` 看现状（是否夹带别人的改动）。
2. 改前先读原文，取得**逐字准确**的旧串（注意长句里的连字符、`~`、`\%`）。
3. 批量机械替换时用脚本，并对每个模式**断言命中次数**——命中 0 或 >1 都停下来，
   不要用"看起来像"的近似串。中文路径不要作为命令行参数传给 git。
4. 改完立刻跑 `scripts/check_paper.py`。
5. 追加同名 `.log.md`：改前原文 / 改后原文 / 原因 / 复核数据 / 范围。
6. 重建提交包。
7. 按逻辑单元提交；提交后核对本次提交的文件范围，别把别人的暂存一起带走。
8. 回复里给**改前 → 改后对照表** + 自检数据 + 需要重编译确认的事项。

---

## 7. 模板合规自检（可复用的审计程序）

投稿前按下面步骤做一遍，全部可机械核对。

### 第 1 步：确认类文件与官方模板是同一份

```python
import hashlib
a = r"paper/IEEEtran.cls"
b = r"template/IEEEtran.cls"          # 官方模板包里的那一份
print(hashlib.sha256(open(a,'rb').read()).hexdigest() ==
      hashlib.sha256(open(b,'rb').read()).hexdigest())
```

类文件被改过是致命问题，必须第一步排除。IEEEtran 目前是 **V1.8b (2015/08/26)**——多年未更新，
2024/2025 年的官方模板包发的仍是这一版，所以"版本旧"不等于"不是官方版"，**以 sha256 比对为准**。

### 第 2 步：把 preamble 的设置逐条与官方模板比对

只统计 `\renewcommand` / `\setlength` / `\def\baselinestretch` / 非模板 `\usepackage`。官方模板的 preamble 是：

```latex
\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\def\BibTeX{...}
```

**除这 8 项以外的一切都算偏离。**

### 第 3 步：把偏离分成"真实改动"和"无害的 no-op"

很多 `\setlength` 写的其实就是类默认值。逐个查类文件里的定义再算差值，否则会把 no-op 也报成违规，
既吓人也误导作者。IEEEtran V1.8b、10pt、`conference` 的参考值：

| 参数 | 类默认 | 备注 |
|---|---|---|
| 正文 | 10pt / **leading 12.00pt** | 行距是本类最硬的红线 |
| `\topfraction` | **0.9** | 不是常被引用的 0.7 |
| `\bottomfraction` | **0.4** | |
| `\textfraction` | **0.1** | |
| `\floatpagefraction` | 0.8 | |
| `\dbltopfraction` / `\dblfloatpagefraction` | 0.8 | |
| `\textfloatsep` | 1.55×leading = **18.6pt** | |
| `\floatsep` | 0.85×leading = **10.2pt** | |
| `\dbltextfloatsep` / `\dblfloatsep` | 18.6pt / 10.2pt | |
| `\abovecaptionskip` | 0.5×leading = **6pt** | |
| `\belowcaptionskip` | **0pt** | |
| `\abovedisplayskip` | 1.5ex+4pt−2pt ≈ 7.5pt | 随字号变 |
| `\abovedisplayshortskip` | 0pt+4pt | |
| `\topsep`（`\@listi`） | **2pt plus 1pt minus 1pt** | 写 2pt±1pt 是 no-op |
| `\partopsep` / `\itemsep` / `\parsep` | **0** | 写 0 是 no-op |
| `\parskip` | 0ex plus 0.2ex minus 0.1ex | 写 `0pt` 去掉弹性，近乎等价 |

（用 `grep -n "\\topfraction\|\\textfloatsep\|..." IEEEtran.cls` 自己验一遍，本表只作起点。）

### 第 4 步：判定禁令的边界

`IEEEtran.cls` 自带 WARNING：

> Authors should not alter font sizes, baselineskip ("leading"), margins or other spacing values
> in an attempt to squeeze more material on each page.

模板正文另有一句：

> All margins, column widths, line spaces, and text fonts are prescribed; please do not alter them.

**三条最硬的线：字号、行距（baselineskip）、页边距/栏宽——一条都不能碰。**
浮动/公式/列表的间距属"other spacing values"，同样在禁令的字面范围内，但危害远小于上面三条。
报给作者时按这两档分开说。

### 第 5 步：量化图内字号（模板要求 8 pt）

模板原文：`Figure Labels: Use 8 point Times New Roman for Figure labels.`

用 PyMuPDF 读每个 span 的字号，再乘缩放系数（缩放 = 放置宽度 ÷ 图形自然宽度）换算成**印出字号**：

```python
import fitz
d = fitz.open("figures/fig1.pdf"); pg = d[0]
scale = (0.95 * 252.0) / pg.rect.width     # 252pt = IEEEtran 双栏的 \columnwidth
for b in pg.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            if s["text"].strip():
                print("%.1f pt -> %.1f pt  %s" % (s["size"], s["size"]*scale, s["font"]))
```

⚠️ **只报设计字号是错的**——图缩小后字号同步缩小，必须换算。一张放在 0.95 栏宽、自然宽度 515pt 的图，
缩放系数只有 0.46，设计 8pt 的标签印出来只有 3.7pt。**缩图的代价要在这里说清楚。**

⚠️ **两个"字号"不是一回事，报数时必须点明是哪一个**：设计字号 = 单独打开图片或绘图源文件时看到的尺寸；
印出字号 = 排进双栏页面后的尺寸。作者往往会打开原尺寸 PNG 判断"看着挺大"，而版面上其实只有 3～4 pt。
报告里写清"这是**印在页面上**的尺寸"，避免双方各说各话。作者若仍决定不动，把结论记进日志并停止追问。

### 第 6 步：文本层可机械核对的项目

| 项 | 判据 |
|---|---|
| 标题与各级标题无缩写 | 模板：`Do not use abbreviations in the title or heads unless they are unavoidable` |
| 标题/摘要无数学式、符号、脚注 | 模板：`Do Not Use Symbols, Special Characters, Footnotes, or Math in Paper Title or Abstract` |
| 浮动体只用 `t` / `b`，不用栏中 | 模板：`Place figures and tables at the top and bottom of columns` |
| `\label` 在 `\caption` 之后 | 模板：`a \label command should not go before the caption` |
| 图引用用 `Fig.~\ref{}`，句首也用 `Fig.` | 模板原文 |
| 无 `Ref.~[n]` / `reference [n]` 写法 | 模板原文 |
| 无 `eqnarray`；小数点前有 0；无 `essentially`；`non` 不加连字符 | 模板原文 |
| 作者 <6 位时列全，不用 `et al.` | 模板原文 |
| 文献题名只首词大写（专有名词除外） | 模板原文 |
| 无模板占位文字残留 | 模板末尾红字警告 |

### 第 7 步：缩写 — 模板有明文，别自己发明规则

模板原文：

> **Define abbreviations and acronyms the first time they are used in the text, even after they have
> been defined in the abstract.**

所以"摘要与正文各定义一次"不是你我的偏好，是模板要求。**删掉正文的展开是违规的。**
反之，若某区域只用一次全称、其后不再用缩写，在该处定义会留下悬空缩写——这种情况按区域分别判断。

### 第 8 步：页数限制

模板只写 `Please observe the conference page limits`——**具体页数在会议官网，不在模板里**。
官网常改版或 404，抓不到就明说"未能核实、需问组委会"，不要拿别届的数字顶替。

---

## 8. IEEEtran 下的子图（subfigures）

**结论先行：用 `subfig` 的 `\subfloat`，不要用 `subcaption`。** 依据是官方 `IEEEtran_HOWTO.pdf`
（随模板包分发，与 `IEEEtran.cls` 同级；本文写作时核到第 10 页"1) Subfigures"一节）。

官方原文要点：

- **`subfigure`（Cochran）**：已停止维护，且与越来越多宏包（含 `fixltx2e.sty`）不兼容——**不推荐**。
- **`subfig`（Cochran）**：**推荐**。但它依赖 `caption.sty`，而后者默认会**抢走 IEEEtran 的图注控制权**，
  导致主图注不再符合 IEEE 样式。因此**必须加 `caption=false`**。官方给的载入方式是：

```latex
\ifCLASSOPTIONcompsoc
\usepackage[caption=false,font=normalsize,labelfont=sf,textfont=sf]{subfig}
\else
\usepackage[caption=false,font=footnotesize]{subfig}
\fi
```

- **`subcaption`（Sommerfeldt）**：官方明写 **cannot be recommended at this time**，原因是它**没有**提供
  阻止 `caption.sty` 接管主图注格式的选项。**网上的教程推荐 `subcaption` 的多，但在 IEEEtran 下是错的。**

用法（`\subfloat` 的**可选参数必须写**，否则不会生成 (a)(b) 标签；不要子图注就写 `\subfloat[]`）：

```latex
\begin{figure*}[!t]
\centering
\subfloat[Case I]{\includegraphics[width=2.5in]{case1}\label{fig_case1}}
\hfil
\subfloat[Case II]{\includegraphics[width=2.5in]{case2}\label{fig_case2}}
\caption{Overall caption.}
\label{fig_sim}
\end{figure*}
```

### 三条容易被忽略的前提与代价

1. **一个 `\subfloat` 只能包一个 `\includegraphics`。** 如果现在的图是"一张 PDF 里画好多个面板"，
   LaTeX 无法给其中某个面板单独加注——**必须先把每个面板导出成独立 PDF**，并抹掉图内原有的 (a)(b) 角标。
   这是换用 `\subfloat` 最大的工作量，往往被忽略。
2. **官方自己说：大多数 IEEE 论文不用子图注。** 原文——
   "most IEEE authors/journals do not employ subfigure captions, but instead reference/describe all of the
   subfigures (a), (b), etc., **within the main caption**."
   也就是说"面板角标画在图上 + 主图注里逐条描述 (a)(b)(c)"**本身就是 IEEE 的常见做法**，不算违规。
   换 LaTeX 子图注多半是审美选择，不是合规要求。
3. **子图注要占版面。** 每个面板下多一行文字，整体变高；而子图并排通常需要比单栏更宽，官方建议放
   `figure*`（通栏）。**通栏浮动体只能排页顶**，会重新引入整页留白——这与"压页数"的目标相冲突。
   在页数吃紧的稿子上，这是一笔实打实的代价。

### 判断建议

评审前遇到"要不要改用 LaTeX 子图注"：先问清是**合规要求**还是**审美偏好**。若不是硬性要求，
且该图已经采用"图内角标 + 主图注逐条描述"，**保持现状即可**；要改，先确认图件能否按面板拆成独立 PDF，
并预留重新编译验证页数的时间。

---

## 9. 通栏浮动体的成本，与"该不该通栏"的判据

### 9.1 成本按两栏计

```
单栏浮动体占用 = 图高 + 子图注 + 图注                   （单位：栏高）
通栏浮动体占用 = 2 x (图高 + 子图注 + 图注)             （单位：栏高）
```

通栏浮动体占的是**页面高度**，它挤走的是**两栏**的正文。所以同样的图高，通栏的版面代价是单栏的两倍。
这一条决定了下面两个结论。

### 9.2 "通栏 + 缩小"凑页数通常是净亏

设通栏图原高 H，等比缩到 s（0<s<1）：

```
腾出量 = 2 x H x (1 - s)          （pt 的正文容量）
```

把 `腾出量 >= 需要腾出的溢出量` 解出 s，再回头看那个 s 下**面板的印出宽度**是多少。
若它已经小于单栏方案能给的宽度，就说明整个"通栏"决定是净亏——面板没变大，却一直按两栏计费。
（实测量级：一张 H=140 pt 的通栏图，缩到 s=0.556 才能腾出 124 pt，而那时面板宽 132 pt，
比单栏方案的 141 pt 还小。）

**判据**：通栏只在满足两条时才划算 ——
① 面板因此**比单栏方案能给的更大**；② 愿意**删正文**来买单。

### 9.3 宽高比不同的两块并排

```
等高：  w_a x ar_a = w_b x ar_b
定宽：  w_a + w_b  = 可用总宽 x 0.97      （留出 \hfil 的间隙）
=>      w_a = 总宽 x ar_b / (ar_a + ar_b)
```

🔴 **等高的宽度分数与基准宽度无关。** 所以单栏改通栏时，`.56/.41 \columnwidth`
直接改基准为 `.560/.410 \textwidth` 即可，**不必重算**——两块整体等比放大，等高关系自动保持。

反过来：宽高比不同时，**等宽、等高、两块内部字号一致**这三件事最多只能同时满足两件。
视觉上选**等高**（这是排版惯例），字号的不一致留给重导面板解决。

### 9.4 通栏浮动体的数量要控制

双栏页面上能挂的通栏浮动体数量有限。**同一区域同时排两个通栏浮动体**（例如某页页顶一个
`figure*`、下页页顶一个 `table*`）会让 LaTeX 被迫提前结算页面，在**栏中间**留下没有任何内容的
空带。判定与处理见 §10.3。

---

## 10. 用编译产物做版面取证

本机没有 LaTeX 时，**不要凭估算下结论**——向作者要一份编译出来的 PDF，下面的量都能直接读出来。

### 10.1 一次跑完

```bash
python scripts/check_layout.py paper.pdf --verify "[Y5ZDBSZL01]"
```

输出四段：每页每栏的文字范围与顶部/底部/内部空隙；**标题前间距的分布**；图/表落位（单栏还是通栏、
落在哪一栏）；参考文献编号是否连续、落在哪几页。`--verify` 是**版本一致性**检查——
拿一个"只有最新版才有的字符串"（例如刚改过的资助编号）去比对，命中才说明这份 PDF 是当前源编译的。

### 10.2 判断"异常空白"必须用同一文档的分布当基准

不要用绝对阈值。正确做法是**把该文档所有标题前的间距都量出来**，得到自己的 normal 区间，
异常值自然凸显。（实例：17 处标题前间距为 5.8-20.8 pt、中位 10.1；唯一一处 37.7 pt 就是异常。）

```
标题前间距 = 该标题行的 y_top - 同栏内上一行文字的 y_bottom
判定：> 3 x 中位 且 明显高于次大值 -> 异常
```

### 10.3 栏中空白的三个来源，按命中率排序

| 来源 | 特征 | 处理 |
|---|---|---|
| **通栏浮动体争槽位** | 空白处源码里什么都没有；该页或邻页页顶是 `figure*` / `table*` | 临时注释掉该通栏浮动体重编译，空白消失即确诊；长期解法是**减少通栏浮动体** |
| 浮动体落页底 | 空白下方能看到图/表 | 改用 `[!t]`，或把图挪到上一栏 |
| 标题需要与后续文字同栏 | 空白紧跟在标题前，且标题下只有一两行 | 一般无需处理；若很长再考虑挪段落 |

### 10.4 四条读 PDF 的经验判据

- **页底余量** = 版心底 y 减去该栏文字最低 y。这是"还能加多少内容"的唯一可靠数字。
- **页顶空 168 pt 左右**（首页右栏）= 标题/摘要块占的，属结构性的，**不是浪费**。
- **一页里两个图注分别落在左右栏**：读序 = 左栏先于右栏，所以左栏那张图的编号必须更小。
- **末栏底部余量 = 0 而末页没排满**：说明内容刚好压到页底，任何增行都会多出一页。

### 10.5 通栏判据（实测踩过三次的坑）

判断一个图注属于单栏还是通栏，**不能用 caption 首行的 x 位置，也不能用 caption 块的宽度**：

- 通栏 caption 是**居中**的，首行 x 落在页面中部（实测 `TABLE I` 首行 x=290.8）；
- 左栏的单栏 caption 首行 x 恰好等于页边（实测 `Fig. 5.` x=81.2 起）；
- 短 caption 的块很窄（`TABLE I` 块宽仅 309.5 pt，而它其实是通栏表）。

**唯一可靠的判据**：单栏 caption 必然**整体落在某一栏之内**；通栏 caption 会**跨过栏间空档**。

```
若 x0 < 栏分界 - 8  且  x1 > 栏分界 + 8   -> 通栏
否则 x1 <= 栏分界 -> 左栏单栏；x0 >= 栏分界 -> 右栏单栏
```

---

## 11. 本地编译环境：检查、安装、编译

### 11.1 先区分"发行版"与"引擎"

**TeX Live 是发行版**（引擎 ＋ 上万个宏包 ＋ 字体 ＋ 工具），不分中英文。
**分中英文的是引擎**，即那个把 `.tex` 变成 PDF 的程序：

| 引擎 | 中文 | 用在哪 |
|---|---|---|
| `pdflatex` | ✗（8-bit，无法直接排汉字） | **英文/IEEE 论文的标准选择** |
| `xelatex` | ✓（Unicode，可直接调系统字体） | **中文文档最常用**，配 `ctex` |
| `lualatex` | ✓（Unicode ＋ 可编程） | 现代方案，比 xelatex 慢但更强 |
| `latex` + `dvips` | ✗ | 老流程（DVI→PS），基本不用 |

中文文档还要两样：**`ctex`** 宏包（中文断行、标点、字号）＋ 一套中文字体。
TeX Live 自带 **Fandol** 四款开源中文字体，xelatex 下 `\setCJKmainfont{FandolSong}` 即可。
`pdflatex` 排中文需要 `CJK` 之类的老方案，很别扭——**中文一律走 xelatex/lualatex**。

### 11.2 检查

```
python scripts/check_env.py --need subfig,dblfloatfix,algorithmic,cite,booktabs
```

报出各引擎是否在位、版本、绝对路径，并用 `kpsewhich` 核实宏包能否解析。
**退出码 1 = 不可用**，可直接当构建闸门用。

### 11.3 安装（portable，免管理员）

本机提权通道常被安全策略封死，所以用 **portable 安装到非系统盘**（系统盘会被重置）：

```
python scripts/check_env.py --install --scheme small --extra subfig,dblfloatfix,algorithmic
```

- 安装器 `install-tl.zip`（约 24 MB）从镜像下载；**国内用清华 TUNA**：
  `https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet`
- 用 **profile 文件**做全自动安装（`-no-gui -profile texlive.profile -repo <镜像>`），关键项：

```
selected_scheme scheme-small
TEXDIR <非系统盘>/Software/texlive/<年>
instopt_adjustpath 0          # 不动 PATH，调用时用绝对路径
tlpdbopt_install_docfiles 0    # 文档与源码占大半体积，不装
tlpdbopt_install_srcfiles 0
```

- **scheme 决定落盘多少**：`small` 覆盖常见论文所需（含 `collection-xetex`），
  `full` 约 7 GB。**优先按需 `tlmgr install <包>` 补**，不要默认上 full。
- 缺包就用 `tlmgr install a b c`；建议先 `tlmgr option repository <镜像>` 换成国内源。

### 11.4 编译

```
pdflatex -interaction=nonstopmode -halt-on-error main.tex   # 跑两遍定页码与交叉引用
# 或
latexmk -pdf -interaction=nonstopmode main.tex              # 自动决定跑几遍
```

**手写 `thebibliography` 的稿子不需要 bibtex/biber**，两遍 pdflatex 足够。
编译完立刻用 `check_layout.py` 量页数、页底余量与落页——这才算"验证过"。

🔴 **但由 `.bib` 驱动文献表的稿子必须跑四步**：`pdflatex → bibtex → pdflatex → pdflatex`。

只跑 pdflatex 会**静默沿用目录里现成的 `main.bbl`**，于是"改了 `.bib` 却毫无变化"。实测踩到过一次：
`main.bbl` 停留在 2 小时前（早于 `.bib` 的修改），而当时那次编译只跑了 pdflatex ⇒ 成稿的参考文献
`[18]` 仍印着改动前的 `issue 2 ed.`，而正确结果是 `Oct. 2014, Issue 2`。判定方法：
**比对 `main.bbl` 与 `references.bib` 的 mtime**，`.bbl` 更早就有嫌疑；必要时先删 `main.bbl` 再编。

### 11.5 第一次编译常见的三个缺口（scheme-small 实测）

装完不等于能编。按报错顺序通常是这三个，逐个补即可：

| 报错 | 缺什么 | 补什么 |
|---|---|---|
| `LaTeX Warning: Citation 'b1' ... undefined` | 不是缺包，是**第一遍本来就不解析引用** | 再跑一遍，别去装东西 |
| `Font OT1/pcr/m/n/8=pcrr7t not loadable: Metric (TFM) file not found` + `Fatal error` | `\texttt{}` 用的 Courier 字体（`pcr`） | `tlmgr install collection-fontsrecommended` |
| `! LaTeX Error: File 'xxx.sty' not found` | 该宏包 | `tlmgr install <包名>` |

**包名 ≠ 文件名**，两个坑都踩过：
- `algorithmic.sty` 所在的 TeX Live 包叫 **`algorithms`**（不是 `algorithmic`），
  写 `tlmgr install algorithmic` 会得到 "package algorithmic not present in repository"。
- **字体类"包"没有 `.sty`**：`fandol`（中文字体）只有 `FandolSong-Regular.otf` 之类的字体文件，
  按包名去 `kpsewhich` 会**误报缺失**。核实字体请按**文件名**查：
  `kpsewhich FandolSong-Regular.otf`。
- 因此环境检查里列 `--need` 时，**宏包写 `xxx.sty`、字体写具体的字体文件名**最可靠。

### 11.6 编译产物：不入库、不入包

一次编译会生成 `main.aux / main.log / main.out / main.toc / main.pdf`（以及报错时的 `missfont.log`）。
它们都能由 `main.tex` 重生成，所以要 **① 写进 `.gitignore`、② 排除在交付包之外**。

- `.gitignore`：`<论文目录>/*.aux` `*.log` `*.out` `*.toc` 与 `main.pdf`。
  **注意别误伤变更日志**——日志叫 `main.log.md`，以 `.md` 结尾，不受 `*.log` 影响。
- 🔴 **`main.bbl` 与 `main.blg` 也必须排除**（bibtex 的产物）。过期 `.bbl` 一旦随包上传，
  在"只跑 pdflatex 不跑 bibtex"的编译下会**静默覆盖 `references.bib` 的正确结果**。
  实测：目录里有别人编译留下的旧 `.bbl` 时，包从 49 条目涨到 51 条目，多出的正是这两项。
- ⚠️ **`.gitignore` 常常漏掉 `.bbl`/`.blg`**（只盖了 `*.aux`/`main.pdf`）⇒ 它们在 `git status`
  里以未跟踪状态出现，容易被误当"待提交的新文件"。发现这个缺口要指出来（补不补是作者的调用）。
- 打包时**只排包根目录的产物**，`figures/` 下的 `.pdf` 是真正的图，必须保留。
  实现上有个坑：根目录文件的 `os.path.dirname()` 是**空串**而不是 `'.'`，
  判定条件要写 `dirname(rel) in ('', '.')`。
- `missfont.log` 是字体查找失败留下的垃圾，**见过就删**，别让它跟着提交。

---

## 12. 页数是台阶函数：加字/删字的实测规则

**不要把页数当成长度量**（"还能放几行"）。同一篇 6 页稿子上的实测：

| 改动 | 词数 | 页数 |
|---|---|---|
| 结论句去限定词（`a power-management SEFI` → `an SEFI`） | −2 | **7 ✗** |
| 同段等量让字（删 `computing`、`solely`） | −2 | **7 ✗** |
| 上面两处**成对** | −4 | **6 ✓** |
| §V-B 补"复位机理"整句 | +5 | **6 ✓** |
| 关键词行把 `COTS` 展开为 `commercial off-the-shelf (COTS)` | +4 | **7 ✗** |

结论：**是否翻页取决于段落整体重新断行的落点，与字数不同向**。因此：

1. **先测后改**：任何正文改动先在影子副本上编译一遍，再决定落不落盘。
2. **翻页就配平，别放弃**：在同一段（或紧邻同节）找一处冗余等量让字，两处一起上——
   "各自单独翻 7 页、成对回 6 页"是常态，因为整段的重排变了。
3. **敏感区**（按敏感度）：结论段末段 → **首页顶部的摘要/关键词块**（它一换行就多占一行、就翻页）
   → 任何末行恰好落在栏末的段落。
4. 反过来也成立：**+5 词可能是免费的**。别拿"这段已经很紧"当理由拒绝改动，去测。

## 13. 交付件新鲜度证明（投稿前必做）

"我刚重建过"不是证据。三步：

1. **mtime 对齐**：交付件（PDF / zip）的 mtime 必须**晚于所有输入**——`main.tex`、`references.bib`、
   `IEEEtran.cls`、`figures/` 下每一个文件。任一输入更新 ⇒ 该件已过期。
2. **同源重编比对**（最硬）：用当前源在影子目录重编一遍，**提取文本与交付件逐字比对**；
   一致即证明交付件就是这一版。这一步同时能验出"编译没跑 bibtex"。
3. **逐文件哈希**：包内每个条目与工作区逐一比对（`zipfile.read(name)` vs 磁盘），
   别只比 `main.tex`——**图件换过而包没重打**是最常见的漏网。

文本比对**必须先归一化**：去掉空白**与行末连字符**（`mea-\nsured` 这种断词会造成假阴性）。
字体检查：交付 PDF 里每种字体都应带子集前缀（`ABCDEF+`）；无前缀的字体可能被会议的 PDF 检查器拒收。

