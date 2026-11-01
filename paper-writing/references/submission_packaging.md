# 引用、版面预算与投稿打包

论文被拒有一半不是内容问题，是这三件事没做好。

## 一、单调引用（避免 desk reject）

正文里的引用必须**严格升序**出现：`[1]` `[2]` `[3]` … `[N]`。

- 不允许跳号：还没出现 `[4]` 就先引了 `[7]`
- 参考文献表里**不能有孤儿**：列了但正文没引
- 中英文稿都要维护一份回填清单，模板 `templates/literature_checklist_template.md`

```bash
python scripts/check_monotonic_citations.py --tex paper.tex --checklist _文献回填清单.md
```

这个检查要在**每次改完正文**后跑，不要等到投稿前——后期插入一条引用会让后面全部错位。

## 二、页数预算（会议论文的硬天花板）

6 页限制是**硬上限**，多一行就是行政退稿，内容再好也进不了评审。

压缩顺序（从低损失到高损失）：

1. **图表标题**：压到 40 词以内，去掉「如图所示」这类废话
2. **表格**：用 `booktabs`，不要竖线，不要重复表头
3. **段落**：合并短段，删掉重复的动机陈述
4. **图**：改双栏跨图或缩小尺寸（最后才动，会影响可读性）
5. **末页平衡**：`\IEEEtriggeratref{N}` 或 `\usepackage{balance}`

## 三、图表规格

| 用途 | 格式 | 要求 |
|---|---|---|
| 插入 LaTeX 终稿 | **矢量 PDF** | 字体嵌入，任意放大不糊 |
| Markdown 草稿 / 评审幻灯片 | PNG | ≥ 300 DPI |
| 网页 / 快速预览 | PNG | ≥ 2 倍图 |

```bash
python scripts/convert_figures.py --input-dir figures/ --dpi 300
```

矢量图交付前跑 `layoutfix check --strict`，查字压图、超画布、箭头悬空。

## 四、投稿打包

- **双镜像**：本地与 Overleaf 各一份，改完同步，别只留一处
- **清理**：提交前删掉 `.aux` `.log` `.synctex.gz` 和临时图，只留 `.tex` `.bib` `.cls` 和 `figures/`
- **自证新鲜**：确认提交的 PDF 确实是**当前源码**编出来的（字体、`.bbl`、图版本都要对）

```bash
python scripts/sync_mirror_and_pack.py --src . --out submission.zip
```

## 投稿前清单

- [ ] `check_monotonic_citations.py` 通过
- [ ] 页数在限制内（含参考文献和图表）
- [ ] 所有图是矢量 PDF，字体已嵌入
- [ ] `layoutfix check --strict` 零 error
- [ ] 打包 zip 里没有中间文件
- [ ] 提交的 PDF 由当前源码编出
