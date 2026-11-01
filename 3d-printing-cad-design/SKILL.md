---
name: 3d-printing-cad-design
description: >-
  Standardized end-to-end workflow for 3D printing mechanical CAD design, parametric modeling
  (using build123d / CadQuery), watertight mesh verification, interactive Three.js 3D web preview
  generation (both self-built small parts AND large imported STEP assemblies via STEP→GLB
  single-file offline preview), and manufacturing delivery packaging. Use this skill whenever designing
  custom 3D printed parts, mechanical brackets, clamps, motor mounts, robotic linkages, or assemblies,
  or when asked to render/preview any STEP/STL model in an HTML viewer.
---

# 3D 打印机械 CAD 建模与工程交付全流程规范 (3D Printing CAD Design Workflow)

本 Skill 沉淀了一套工业级、高可靠的 **3D 打印机械结构设计、参数化 CAD 建模、模型质检与交付闭环流程**。无论是设计电机安装底座、碳纤维管夹具、连接铰链还是复杂多件装配体，均应遵循以下五阶段工程标准执行。

---

## 运行环境

CAD 依赖只装在 miniconda，**本文档所有 `python <脚本>` 命令里的 `python` 一律指**：

```
C:\Users\qilin\miniconda3\python.exe
```

已装：trimesh 5.1.0、build123d 0.11.1、matplotlib 3.11.2、numpy 2.5.1、cascadio 0.1.1（STEP→GLB）、fast-simplification 0.2.0（网格简化）、Pillow。Node.js 22 可用（JS 强校验）。其他 Python 运行时（含 WorkBuddy 托管环境 `C:\Users\qilin\.workbuddy\binaries\python\`）为隔离环境，未装这些包，直接用 `python` 会报 `ModuleNotFoundError`。

> 版本：v1.1（2026-10-22 实战修订）——新增大型 STEP 装配体预览路线 B、几何合并铁律、离线内嵌规范、垃圾几何剔除流程；升级 check_preview_syntax.py（node --check 强校验，消除 NaN 误报）；**每个预览 HTML 强制配套同名 `<name>.README.md`（七项内容，见阶段四"交付说明文件"）**。

---

## 核心设计哲学与避坑准则

1. **结构强度第一，严禁盲目削弱材料**：
   - 碳纤维管、薄壁金属件严禁打孔，全部采用**上下对开半圆柱抱箍摩擦对夹**（Saddle Clamping），保持主梁完整性与抗扭弯刚度。
   - 正交交叉管件之间，**必须预留 $\ge 3.0 \sim 5.0\text{mm}$ 的纯实心隔离层**，严禁让两个方向的凹槽在物理空间或视觉上重叠/贯通。
2. **特征轮廓外显，拒绝死板方块**：
   - 圆柱夹具段必须具备**显著外凸的半圆柱筒身**（圆柱外壳高出螺栓固定耳片 $3 \sim 5\text{mm}$），侧腰采用收身倒角，让机械轮廓与受力路径清晰外露。
3. **配合标高绝对受控（Z-Elevation Budgeting）**：
   - 建模前必须绘制**Z轴高程分配表**，精确标定底面电机端、下构件、隔离层、上构件、顶盖各层的绝对坐标，从源头杜绝干涉与装配反向。
4. **100% 水密性（Watertight）自动化质检**：
   - 任何导出的 STL 文件在交给用户前，必须通过 `trimesh` 自动化流形检验，确保无任何破面、反向法线或非流形边。
5. **零插件交互式 3D 网页预览**：
   - 交付物必须包含轻量级 `preview.html`（基于 Three.js），提供爆炸分解、高程图层显隐、剖切透视与板厚切换，极大降低沟通成本。

---

## 阶段一：需求与物理约束梳理 (Requirements & Constraints)

在写任何建模代码前，必须明确并确认以下 4 类核心参数：

1. **动力源/执行器接口（Actuator Interface）**：
   - 电机型号（如达妙 DM-J4310、DM3507 等）、安装 PCD 孔心距（如 6×M3 PCD 27mm）。
   - 转子定位凸台直径与高度（如 Φ35mm × 1.0mm）、中心出线避空孔（如 Φ14mm）。
   - 螺栓下沉空间：沉头槽深度必须让螺钉头部完全沉入零件表面下方，避免与上方旋转/夹持件干涉。
2. **主传力构件（Structural Members）**：
   - 构件截面（如 Φ12mm 碳管、8×2mm 扁铁）。
   - 配合公差：3D 打印内孔半径应留 $+0.05 \sim +0.15\text{mm}$ 装配间隙（如 Φ12mm 管，鞍座内孔取 $R = 6.0\text{mm}$）。
3. **末端被夹持件（End Effectors / Plates）**：
   - 宽度、板厚规格（如 50mm 宽，板厚 1mm / 2mm / 3mm）。
   - 采用**对称双边开槽**（上下两半各挖一半深度，例如 2mm 板上下各挖 1.0mm）。
4. **标准五金配件规范（Fastener BOM）**：
   - 紧固件等级推荐 12.9 级内六角圆柱头螺栓（DIN912）。
   - 螺母槽设计：底座外侧开六角槽（对边 $s$，外接圆半径 $R_{hex} = s / \sqrt{3}$，深度为螺母厚度 $+0.2\text{mm}$），实现防转自锁。
   - 详见参考文档：[标准紧固件与沉槽公差规范](./references/hardware_fasteners.md)。

---

## 阶段二：参数化 CAD 建模 (Parametric CAD with build123d)

使用现代 Python CAD 库 `build123d` 进行高精度的实体 Brep 建模。

> 工业级参数化建模的写法约定（Builder vs Algebra 模式怎么选、Sketch 约束、定位与镜像、常见报错）见 [build123d 最佳实践](./references/build123d_best_practices.md)，动手前先读一遍。

### 1. 强制执行 Z 轴标高规划
在编写代码前，用注释清晰定义全局 Z 轴坐标：
```python
# =============================================================================
# Z 轴标高绝对分配 (Z-Elevation Budget):
# Z = 0.0 mm : 电机转子输出贴合端面 (Φ35mm 凸台配合)
# Z = 12.0 mm: 下层横向碳管轴心 (下管占用 Z in [6.0, 18.0] mm)
# Z = 18.0 ~ 23.0 mm: 5.0 mm 纯实心塑料隔离墙 (杜绝融化与干涉!)
# Z = 29.0 mm: 上层竖向碳管轴心 (上管占用 Z in [23.0, 35.0] mm)
# Z = 38.5 mm: 顶盖最外端外弧顶点
# =============================================================================
```

### 2. 保证特征鲜明（圆柱抱箍与侧腰收身）
- **圆柱段外凸**：
  ```python
  # 碳管外径 12mm (R_tube = 6.0)
  # 外圆柱半径 R_cyl = 9.5mm (凸起高 9.5mm)
  # 耳片厚度仅 H_ear = 4.5mm
  # -> 半圆柱凸出耳片 9.5 - 4.5 = 5.0mm！
  ```
- **中间件侧腰收身**：中间隔层不要做成笨重实心死方块，采用十字交叉筋板连接四角柱，将圆柱弧面裸露在外，方便观察与减重。

### 3. 多规格变体参数化生成
末端夹具应支持厚度动态参数化：
```python
def make_end_clamp(plate_thick=2.0, is_base=True):
    slot_depth = plate_thick / 2.0
    ...
```

---

## 阶段三：多重严苛质检与几何验证 (Verification & QA)

在向用户汇报或交付 STL 前，必须完成以下 4 项自动化验证：

1. **水密流形检测（Watertight Check）**：
   运行质检脚本：
   ```powershell
   python scripts/check_stl_watertight.py <folder_path>
   ```
   - 验证所有 STL 的 `is_watertight == True`。
   - 检查是否有非流形边、法线反转。
2. **三维包围盒与高度校准（Bounds Check）**：
   - 打印每个零件的 `mesh.bounds`，确认零件的 Z 高程与初始标高规划表完全吻合（无翻转、无位移偏置）。
3. **干涉与零碰撞校验（Interference Check）**：
   - 在 `build123d` 中构建装配 Compound，并导出完整的总成 STEP 文件。
4. **多视角 2D/3D 渲染确认（Visual Confirmation）**：
   - 使用 `matplotlib` 3D 渲染 4 个关键视角（总成三层图、中层双鞍座图、夹具底座图、夹具盖板图），重点自检两凹槽之间是否有实心隔墙，夹具是否有突出圆柱。
5. **外部大型装配体（导入的 100MB+ STEP）的替代质检闭环**：
   - 第三方装配体无法逐件水密检测，改用：转换返回码 `rc=0` → 预览 HTML 用 snap 体检 **0 控制台错误** → 多角度截图目检（模型完整、无散架、无穿模）；
   - 目检发现"异物"时，先用数据定位再动手删：解析 glTF JSON 查零件名/颜色/包围盒（OCCT 导出会保留 STEP 零件名），或用"隐藏颜色组 + 截图"二分法锁定（见阶段四与避坑手册）。

---

## 阶段四：零插件 3D 网页预览生成 (Three.js Interactive Preview)

生成包含在交付包中的本地 HTML 3D 预览。**先判断模型规模，再选路线**（两条路线均要求：完全离线单文件、双击即开、Three.js 一并内嵌）。

### 路线 A：自建小模型（≤ 50 件，STL 均在手）

1. **网格数据内嵌**：用 `trimesh` 读取 STL 的 vertices/normals/faces，顶点取整到 0.01mm，`json.dumps(..., separators=(',', ':'))` 紧凑 JSON 内嵌。
2. **Three.js 一并内嵌**：`three.min.js` 与 `OrbitControls.js`（r128）放进 `<script data-lib="...">` 属性标签内嵌——带属性的标签会被语法检查器自动跳过，且文件彻底离线（答辩现场无网也不白屏；依赖 CDN 的预览在现场是有白屏风险的）。
3. **核心交互能力**：
   - **爆炸分解滑块（Explode Slider）**：0~60mm 动态分解，展示零件分层与内部装配顺序。
   - **图层显隐勾选框（Visibility Checkboxes）**：逐层隐去顶盖、上管、中鞍座，直观透视内部。
   - **规格切换按钮（Variant Switcher）**：实时切换 1mm / 2mm / 3mm 夹具厚度。
   - **剖切平面透视（Section Clipping Plane）**：使用 `THREE.Plane` 沿中心轴纵切，直接展示壁厚均匀度与防转螺母槽。

### 路线 B：外部大型装配体（100MB+ STEP，整机/板卡级参考设计）

**严禁把全精度网格转成 JSON 数组内嵌**（360 万面 ≈ 145MB 文本，浏览器解析即卡死）。正确做法：

1. **转换**：`python scripts/step_to_glb.py <input.stp> <output.glb>`，cascadio（OCCT 并行）转 GLB，tol_linear=0.1mm / tol_angular=0.5°。实测 251MB STEP 约 205s 转 44MB GLB。**输出路径必须纯 ASCII**——OCCT 写不了中文路径，会在耗尽数分钟的转换*结束*时报 `Cannot open output file` 前功尽弃；脚本已自动先落临时目录再移回。
2. **内嵌**：GLB 以 base64 放入 `<script type="text/plain" data-payload="glb-base64">`（严禁作为 JS 字符串拼接），浏览器端 `GLTFLoader.parse(ArrayBuffer)` 直读。251MB STEP → 约 60MB 单文件，**零简化、零精度损失**。
3. **未经用户明确要求，不做任何面数简化/预算**。确需简化时用 `fast_simplification` 并单独征得确认。
4. **合并几何的铁律（违反 = 整个装配散架，已踩坑一次）**：
   - 每件先 `geometry.applyMatrix4(mesh.matrixWorld)` 烘焙节点世界变换——glTF 装配的位置/旋转挂在节点树上，几何体本身只是局部坐标；
   - 烘焙前必须 clone 位置/法线/索引属性——同一 meshDef 会被多节点实例复用，直接改共享缓冲区会互相污染；
   - 按材质颜色合并成组（1.4 万零件 → 约百个 draw call），侧栏提供颜色组显隐。
5. **显示正确性**：
   - r128 GLTFLoader 不做 sRGB 转换：保持默认 Linear 管线 + `NoToneMapping`，CAD 颜色原样还原；
   - **灯光只用中性白光**——彩色补光会把黑色橡胶脚垫照成"蓝色异物"、把灰色机壳照成金色，诱发误判删错零件；
   - 不全局覆盖 metalness/roughness（假高光误导材质判断）；
   - 模型单位常为米：整体 `scale.setScalar(1000)` 转毫米，剖切滑块/包围尺寸才有物理意义。
6. **参考 CAD 的垃圾几何**（丝印面片、冗余备用外壳、虚拟网络节点）：用 `EXCLUDED_COLORS` 颜色黑名单剔除。定位"屏幕上某个异物是什么"禁止靠猜，用二分法：复制 HTML → 正则替换排除集 → 每轮 snap 截图对比，2~3 轮锁定颜色组（详见 [Three.js 预览避坑与调试手册](./references/threejs_preview_pitfalls.md)）。

### 语法与渲染双重校验

```powershell
python scripts/check_preview_syntax.py preview.html
```
- 有 node 时自动对每个应用脚本块跑 `node --check` 强校验，无 node 退回括号配对检查；
- `data-lib` 库块与 `type="text/plain"` 数据块自动跳过（旧版对 three.min.js 里的 `isNaN` 会误报 NaN）；
- 再用 snap 体检（0 控制台错误）+ 截图目检作为渲染门禁。

### 交付说明文件（强制工序）

**每一个预览 HTML 都必须配套同名 README**：`<预览文件名>.README.md`，与 HTML 同目录、同名前缀，随交付包一起发出。**缺 README 的预览视为未交付。** README 必须包含以下七项：

1. **这是什么**：一句话说明预览对象与数据来源（源模型文件 / 方案文档路径）
2. **打开方式**：双击即开、是否离线、首次加载时长与硬件建议
3. **内容概览**：面数 / 尺寸 / 颜色分组等统计，或场景构成清单（与示意图序号一一对应）
4. **交互功能**：逐项列出滑块、显隐、剖切、跨距等操作
5. **已剔除 / 近似说明**：被剔除的冗余几何（颜色组）与程序化近似器件同真实件的差异
6. **再生成方法**：生成脚本、依赖与执行步骤（模型更新后可一键重建）
7. **已知限制** 与必要的安全提示（如激光安全）

> 工序位置：生成预览 → 语法/渲染双重校验 → **写 `<name>.README.md`** → 交付。README 写完应自查：一个拿到文件的新人，不问任何人就能打开、看懂、改出自己需要的版本。

---

## 阶段五：交付物规范与发包打包 (Packaging & Fabrication)

完成建模与测试后，组织规范的交付目录结构并自动生成 ZIP：

```text
3D打印交付文件_<项目规格名>/
├── preview.html                      # 完整装配总成 3D 交互预览 (支持爆炸分解)
├── preview.README.md                 # 预览使用说明 (打开方式/交互/剔除项/再生成)
├── preview_clamp.html                # 末端夹具专属 3D 交互预览 (支持剖切透视与板厚切换)
├── preview_clamp.README.md           # 夹具预览使用说明
├── 3D打印与装配说明_<项目规格名>.txt # 纯文本发包清单 (打印店切片人员友好)
├── 设计尺寸与装配工程规范_<项目名>.md  # 详细工程尺寸、标高公差与五金装配规范
├── 完整机构总成_<项目规格名>.step     # 工业 CAD 通用装配总成 (SolidWorks/Fusion360可打开)
├── 中心轮毂_下层底座_Base.stl / .step
├── 中心轮毂_中层双向鞍座_Mid.stl / .step
├── 中心轮毂_顶盖_Cap.stl / .step
├── 碳管末端夹具_底座_1mm板.stl / .step
├── 碳管末端夹具_盖板_1mm板.stl / .step
├── 碳管末端夹具_底座_2mm板.stl / .step
├── 碳管末端夹具_盖板_2mm板.stl / .step
├── 碳管末端夹具_底座_3mm板.stl / .step
└── 碳管末端夹具_盖板_3mm板.stl / .step
```

### 打印参数推荐标准
- **材料选择**：优先选用 PETG、ABS、ASA 或 尼龙 PA12（避免高温软化，韧性好抗开裂）。
- **壁厚与填充**：外圈壁厚（Wall Loops）$\ge 4$ 层（厚度 $\ge 1.6\text{mm}$），填充率（Infill）$\ge 40\%$（推荐螺旋或蜂窝填充 Gyroid），保证螺栓大扭矩夹紧时不破裂。

