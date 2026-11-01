# layoutfix 设计文档

> 本文件讲**为什么这样实现**与**模块之间约定了什么**。改内部实现前读这里；
> 日常操作规则看根目录 `AGENTS.md`；使用说明与踩坑清单看 `README.md`。

## 1. 定位

给示意图做**几何体检**与**人工微调**，替掉「agent 画图 → 截图 → 目测 → 再猜 → 再截图」这个循环。

- 输入：`.svg` 或 `.pdf`（matplotlib 出的、Illustrator 出的、agent 直接写的都行）
- 输出：可断言的违例清单（JSON + 退出码）、以及被人手调过但可重放的图

**不做**：位图修图、改配色方案、增删元素、审美判断。

## 2. 为什么不用现成编辑器

| 候选 | 否决理由 |
|---|---|
| SVG-Edit / Penpot / Excalidraw / tldraw | 它们接管整份文档：解析成自己的模型、重新序列化、自己管撤销栈。「只改目标元素」和「delta 清单」两个保证全没了，也不认我们的元素句柄 |
| Fabric.js / Konva | 在 canvas 上画，不操作 SVG DOM。要改就得把 SVG 导成对象模型，丢保真，还可能所见非所得 |
| Moveable / Interact.js | **对路**——只在已有 DOM 元素上加拖拽与参考线。但为「吸附」一个功能引依赖不划算，自己写了约 80 行，保持零依赖 |
| 自建中间表示（mini-Figma） | 无底洞。要的是协议，不是编辑器 |

结论：**不接管文档，只在文档上做最小改写**。这是整个设计的支点，任何功能都不能破坏它。

## 3. 架构与数据流

```
浏览器                          本地服务 (127.0.0.1)               磁盘
──────                          ─────────────────────              ────
                                                                  
拖动元素                                                          
  ↓ 视觉预览（直接改 DOM 属性）                                    
松开                                                              
  ↓ POST /apply {id, dx, dy}                                      
                            edit.move()                          
                              ├─ read_raw（字节级）              
                              ├─ _locate(id) 定位单个标签        
                              ├─ _shift_tag() 改坐标             
                              ├─ write_raw ───────────────────→ 图.svg（只变一行）
                              └─ append_op ───────────────────→ 图.svg.nudge.jsonl
                            ↓                                    
  ← {ok:true}                                                    
  ↓ refresh()                                                    
  ← /fig.svg（注入 data-ffid 的副本）+ /state（probe 结果）        
```

一次「体检」的数据流：

```
图.svg ──pymupdf.open()──→ page
                            ├─ get_texttrace()  → span（bbox + 字号 + seqno）
                            └─ get_drawings()   → shape（rect + fill + seqno）
                                    ↓
                          _merge_lines() 聚成视觉行
                                    ↓
                  ┌─────────────────┴─────────────────┐
            几何检查（MuPDF 坐标）            语义检查（SVG 源码）
            overlap / occluded / bounds      dangling / offcenter
                  └─────────────────┬─────────────────┘
                                    ↓
                        Violation[] → JSON / 人读文本
```

**关键分工：MuPDF 给几何，SVG 源码给身份。** MuPDF 不保留 `id`，所以两边按文字内容优先、位置兜底对齐（`attach_identity`）。

## 4. 模块契约

### 4.1 `probe.py` — 几何体检

```python
run(path, width_mm=None) -> dict     # 唯一对外入口，纯函数无副作用
```

返回结构固定：`file / unit_mm / canvas / counts / violations[]`。
每条违例含 `code / severity / msg / eids / ffids / region`。

内部三层，改动时别越界：
- `parse_svg()` — 只读 SVG 源码，产出 rects / texts / arrows + 每个元素的 `ffid`
- `load_geometry()` — 只读 MuPDF，产出 page_size / spans / items，**用完必须 `doc.close()`**
- `check_*()` — 只吃上面两者的产出，不读文件

判定阈值集中在这里，改阈值要同步改 `README` 的检查项表：

| 检查 | code | 判定 |
|---|---|---|
| 文字重叠 | `text_overlap` | 横向重叠 > 0.6 单位，且纵向重叠 > `0.12 × 字号`，且占较小者面积 > 4% |
| 文字被盖 | `text_occluded` | 覆盖者 `seqno` 更大、`fill` 非 None、`fill_opacity > 0.95`、覆盖率 > 8% |
| 超出画布 | `text_out_of_canvas` | 文字 bbox 越出页面矩形 0.6 单位以上 |
| 箭头悬空 | `arrow_dangling` | 一端距框 ≤ 2.5mm（视为接上）、另一端 > 2.5mm |
| 标签偏心 | `label_offcenter` | `text-anchor=middle`，与宿主框中心水平偏差 > 1.2mm |

三个必须保留的细节（删了就会误报/漏报）：
1. `seqno` 交错排序决定 z-order，只比 bbox 会把整图文字判成被背景覆盖
2. `dedupe_spans()` 去掉白色描边遮罩造成的重复绘制
3. `_merge_lines()` 横向**重叠**的两段字不许合并，否则重叠缺陷会被「同一行」规则抑制掉

### 4.2 `edit.py` — 元素寻址与属性落地

```python
annotate(raw) -> str                      # 给副本加 data-ffid，只用于下发
inventory(raw) -> list[dict]              # CLI 列表，eid/locked/hint
apply_move(raw, eid, dx, dy) -> str       # 纯字符串变换，不碰磁盘
apply_set(raw, eid, attrs) -> str
move(fig, eid, dx, dy) -> dict            # 落盘 + 记清单
set_values(fig, eid, attrs) -> dict
set_text(fig, eid, text) -> dict          # 文字内容；\n → tspan；from 存旧元素整段字节
undo_last(fig) -> dict | None
```

**文字内容（set_text）**：`to` 是逻辑文本（`\n` 分行），`from` 是旧元素
**整段字节**（开标签+旧内容+`</text>`）。撤销 = 把这段字节原样拼回，
所以行距节奏、空格、属性顺序一个不动；重做 = 按 `to` 重建（确定性，同样的
输入编出同样的 tspan）。行距沿用旧 tspan 的 dy，全新多行按 字号×1.35 兜底。

**编号规则（唯一真相）**：`eid = "<tag>:<该 tag 在文档中出现的序号>"`，按标签名**分别计数**，覆盖 `MOVABLE` 全部类型，跳过闭合标签与注释。`annotate` / `inventory` / `_locate` 三处必须完全一致，否则拖 A 改到 B。

**属性分流**：
- `STYLE_PROPS`（字号/字体/填充/描边/透明度等）→ 写内联 `style`，因为 CSS 规则优先级高于呈现属性
- 其余（`x`/`y`/`width`/`height` 等）→ 写呈现属性
- `NEEDS_PX`（font-size / letter-spacing）→ 值后补 `px`，CSS 里不能裸写数字

**界面只暴露「版面」那一半**：位置、宽高、字号、对齐、图层。
颜色 / 字体 / 加粗**不给界面入口**，但 `edit.py` 的接口照样支持（agent 要用）。
这不是没做完，是分工：颜色和字体属于设计决定，要服从整张图的视觉体系，
不该由没有全局视野的人在界面上逐个改。**别"顺手"把取色器加回界面。**

**位移策略**：
- 有 `x`/`y`（或 `cx`/`cy`）且无 `transform` → 直接改数值
- 其余 → `transform="translate(tx,ty) <原 transform>"`，`translate` **必须在最前**（transform 列表右起生效）

### 4.3 `tune.py` — 本地服务

| 路由 | 方法 | 说明 |
|---|---|---|
| `/` `/index.html` | GET | 注入 SVG 与 `UNIT_MM` 的界面；`?file=` 切换同目录 svg（basename 校验防穿越），`?z=` `?sel=` `?theme=` 同理 |
| `/fig.svg` | GET | 带 `data-ffid` 的副本 |
| `/state` | GET | probe 结果 + 清单 + 同目录 `files` 列表 |
| `/selftest` | GET | 合成拖拽自测页 |
| `/apply` | POST | `{id, dx, dy}` 位移 |
| `/set` | POST | `{id, attrs:{...}}` 改属性 |
| `/set_text` | POST | `{id, text}` 改文字内容（`\n` → tspan） |
| `/undo` | POST | 撤销最后一条 |

约束：
- 只监听 `127.0.0.1`
- **当前图可切换**（`?file=`）：undo/redo 的内存栈按文件路径隔离，切换不串台
- 所有读写持同一把 `threading.Lock`（`write` 先截断再写，不加锁会读到半截文件）
- 所有路由先 `urlparse().path` 再匹配（否则带查询串就 404）
- 每个路由有 `try/except` 兜底，异常返回 JSON 而非 500 HTML

### 4.4 `web/index.html` — 拖动界面

单文件、零依赖、零构建。要点：

- **预览不用 CSS `transform`**：CSS transform 会整个替换元素自带的 transform 属性，拖动已移动/旋转过的元素时按下瞬间会跳回原位。改为快照属性后直接改 `x`/`y`/`transform`，与服务端算法一致。
- **图内文字编辑用浮层、不用 foreignObject**：foreignObject 出了浏览器就不渲染（MuPDF 体检、Office 导入全瞎），会同时破坏几何体检和交付。浮层提交后落盘仍是纯 `<text>/<tspan>`。
- **文字手柄 = 折行宽度，不拖字号**：一个手柄干两件事说不清。折行测宽直接在原图里量（临时 tspan + `getComputedTextLength()`），字体环境与原图一致；CJK 按字折、拉丁按词折、超长词硬切。
- **写操作串行化**：`queue()` 把 `/apply`、`/set`、`/undo` 串成一条链。并发时 `/undo` 可能抢在 `/apply` 前面，撤销撤错 op。
- **吸附优先级**：元素边缘/中心 → 网格。吸到元素画参考线，吸网格不画（避免画面太吵）。
- **主题与反相**：`[亮][暗]` 分段控件，高亮=当前态；反相只在暗色可用，亮色下 `disabled`。网格永远用黑色画，暗色反相时被滤镜翻成白线。
- **`data-fflock`**：背景板标记锁定而非跳过，保证编号与 `_locate` 一致。

## 5. 清单协议

`<图>.nudge.jsonl`，一行一条，追加写：

```json
{"id":"text:4","op":"move","dx":0,"dy":-4.0,"at":"2026-10-31T22:13:35"}
{"id":"rect:1","op":"set","to":{"width":300,"height":90},
 "from":{"width":"260","height":"78"},"at":"..."}
```

- `move` 用 `dx`/`dy`（图自身单位）
- `set` 用 `to`/`from` 字典；`from` 为 `null` 表示原本没有该属性（继承自 CSS）
- 撤销 = 反向 `move` 或写回 `from`，然后抹掉最后一行
- 读清单必须容错：坏行跳过，否则一行残缺就让工具永久打不开

## 6. 测试矩阵

| 层次 | 手段 | 验的是什么 |
|---|---|---|
| 单元 | 手工构造最小 SVG | 换行不被改写、`width` 不命中 `stroke-width`、单引号属性、NaN 拦截、零位移拦截 |
| 逐元素 | 对图里**每个**元素单独施加位移，比对全部标签文本 | 编号一致性（拖 A 不会改到 B） |
| 往返 | N 次编辑 + N 次撤销，比对字节 | 撤销精确性 |
| 端到端 | `/selftest` 合成拖拽 | 预览、落盘、清单、违例刷新、主题切换、文字编辑与折行（撤销后字节还原） |
| 回归 | `demo/` 全部图跑 `check` | 阈值调整后误报/漏报是否变化 |

**逐元素验证是编号一致性的唯一可靠验证方式**，读代码看不出问题。脚本见 `tmp/`，逻辑：`apply_move(raw, eid, 5, 0)` 后对比两版标签列表，差异必须**恰好**是目标那一个。

> 写这类验证脚本时注意：`eid` 的序号是**按标签名分别计数**，不是「所有可拖元素的总序」。按总序算会得到一堆假失败。

## 7. 扩展指南

**加一种检查**：
1. `probe.py` 里写 `check_xxx(...) -> list[Violation]`
2. 在 `run()` 里接上，`code` 用下划线命名
3. 补进 `README` 的检查项表；`AGENTS.md` 无需改（检查项不进规范）
4. 在 `demo/` 找一张能触发的图，跑 `check` 确认命中数变化合理

**加一种可编辑属性**：
1. 判断它属于 `STYLE_PROPS` 还是几何属性
2. 若在 `NEEDS_PX` 里，确认单位
3. 前端属性面板加输入框，`bindNum()` 或 `commitSet()` 接上
4. 跑一次「改属性 → 撤销 → 字节还原」验证

**换渲染底座**（比如改用浏览器测量文字）：
`probe.py` 的 `load_geometry()` 是唯一依赖 MuPDF 的地方，换掉它即可，`check_*()` 不用动。

## 8. 已知边界

- 只处理单页，多页 PDF 只看第一页
- `arrow_dangling` 只认 `marker-end` 标记的箭头，手绘多边形箭头认不出
- `label_offcenter` 只查 `text-anchor="middle"`，且一框多字（引脚编号）时自动跳过
- 拖动界面管版面、文字内容（tspan 多行）与线段端点（限无 transform 的 line）；不支持多选、旋转、等比缩放、增删元素
- 坐标默认按 CSS 96dpi 折算毫米，精确物理尺寸需 `--width-mm`
- 元素编号依赖文档顺序：agent 重新生成时若增删元素，旧清单会指向错位的元素

## 9. 路线图

- [ ] 多选与整体移动
- [ ] 清单重放：`layoutfix replay <图> <清单>`，把人工调整套到重新生成的图上
- [ ] 锚点声明：`data-anchor="node-a:right:2mm"`，让标签跟随目标，从根上减少压字
- [ ] `check` 增加色盲/灰度仿真与最小线宽检查
- [x] 与 `snap` 打通：违例区域直接喂 `snap --clip` 只截那一小块（`check --json` 输出 `region`；paper-figures 的 `preview.py --violations` 自动逐违例渲染）

## 10. 实现坑清单

15 条踩过的坑（含现象、根因、修法）在 `README.md` 的「设计上踩过的坑」一节，改代码前务必先读一遍。
