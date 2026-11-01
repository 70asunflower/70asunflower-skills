# Three.js 预览避坑与调试手册 (Preview Pitfalls & Debug Playbook)

本手册收录 2026-10 大型装配体预览（Jetson Thor DevKit，251MB STEP → 60MB 离线单文件 HTML）实战中踩过并验证修复的坑。**遇到症状先查本表的"症状→根因→处方"，再动手改代码。**

---

## 一、症状 → 根因 → 处方 速查表

| 症状 | 根因 | 处方 |
|------|------|------|
| **整个装配散架**（零件四处乱飞、堆在原点附近） | 合并几何时未烘焙节点世界变换；glTF 装配的位移/旋转挂在节点树上，几何体本身只有局部坐标 | 每件 `geometry.applyMatrix4(mesh.matrixWorld)` 后再合并；`gltf.scene.updateMatrixWorld(true)` 要先于遍历 |
| 散架修复后部分零件仍错位/变形 | 同一 meshDef 被多节点实例复用（螺丝、垫片），`applyMatrix4` 直接改了共享 BufferAttribute，污染其他实例 | 烘焙前 `position/normal/index` 一律 `.clone()` 深拷贝 |
| 转换在**结束时**报 `Cannot open output file` | OCCT 写不了非 ASCII 路径（Windows 中文目录），且报错发生在整场转换（数百秒）结束、工时全废 | 输出到 ASCII 临时目录，成功后 `shutil.move` 回目标；用 `scripts/step_to_glb.py` 已内置 |
| 颜色发灰/发暗/过曝 | r128 GLTFLoader 不做 sRGB→Linear 转换，又开了 sRGBEncoding 输出或 ACES 色调映射 | 保持默认 Linear 输出管线 + `NoToneMapping`，CAD 颜色即原样还原 |
| 黑色/灰色零件泛蓝光、灰色机壳泛金 | 场景里有彩色补光灯（如 0x93c5fd 蓝、0xfef08a 黄），深色材质镜面反射补光色 | **灯光一律中性白**：Ambient + 2~3 盏白色 Directional，不加彩色光 |
| 零件有塑料假高光、像喷了漆 | 生成器全局覆盖 metalness/roughness（如强制 metalness=0.15） | 尊重 GLB 自带 PBR 值，最多把 roughness>0.95 压到 0.85 |
| 剖切滑块数值离谱（0.3 之类） | STEP 转出的 GLB 单位是米 | 整体 `model.scale.setScalar(1000)` 转毫米，再做 Box3/相机/滑块 |
| 大装配双击打开极卡或崩溃 | 全精度网格转成 JSON 数组内嵌（360 万面 ≈ 145MB 文本） | 改路线 B：GLB base64 内嵌 + `GLTFLoader.parse(ArrayBuffer)`；**未经用户要求不得加面数预算** |
| 上万零件掉帧 | 每零件一个 draw call | 按材质颜色 `mergeBufferGeometries` 合组（万件 → 约百组），侧栏提供颜色组显隐 |
| 白屏 | JS 语法错误；或内嵌库/数据含 `</script>` 提前闭合标签 | 库与数据用带属性标签（`data-lib` / `type="text/plain"`）；内嵌前断言不含 `</script`；跑 `check_preview_syntax.py`（node 强校验） |
| 语法检查报 NaN 但明明没有 | 旧版检查器对整份文件做 `in` 搜索，three.min.js 里的 `isNaN` 命中 | 用 v1.1 检查器：NaN 只查应用脚本块 |

---

## 二、"屏幕上这个异物是什么/怎么删" 标准流程

参考 CAD 常带垃圾几何：丝印面片、冗余的旧版外壳、虚拟网络节点。**禁止靠零件名猜测，按下面流程走：**

1. **查数据**：解析 GLB 的 JSON chunk（见 §四），按零件名/颜色/包围盒反查。OCCT 导出会保留 STEP 零件名，名字有语义（`FOOT_RUBBER_*`、`LOGO_SILK_*`、`155-xxxx-000` 料号等）。
2. **定位屏幕坐标对应的零件**：复现相机投影（见 §五），把所有零件的世界包围盒投影到屏幕，落在目标像素附近的就是候选。
3. **二分验证**：复制 HTML 副本 → 正则替换 `EXCLUDED_COLORS` 集合 → `snap` 截图对比。每轮把候选颜色对半分，2~3 轮锁定确切颜色组。**改动与否以截图为准，不以推断为准。**
4. **剔除**：把确认的颜色写进生成器的 `EXCLUDED_COLORS`，重新生成正式文件。注意同组可能混有合法零件——若颜色组里良莠混杂，改为按零件名/包围盒剔除而非按颜色。

> 实战案例：Thor DevKit 表面两个"C 形件"先后被误判为丝印贴片、橡胶脚垫，最终二分定位到颜色组 `(164,164,255)` = 冗余旧版外壳上的装饰件，整组删除后包围尺寸 61.7→56.9mm 才是真实值。

---

## 三、投影/相机调试注意事项

- **画布宽 ≠ 窗口宽**：侧栏占宽后 canvas = 窗口宽 − 侧栏宽（如 1280−360=920），`camera.aspect = 920/800`。复现投影时用**画布尺寸**，否则所有屏幕坐标横向错位，一个零件都对不上。
- 复现三件套：`lookAt(eye, target, up)` 视图矩阵 + `PerspectiveCamera(fov, aspect, near, far)` 投影矩阵 + `ndc → (px, py)` 换算；生成器的相机摆放公式（`center + (0.95, 0.7, 0.95) × maxDim`）是确定性的，可精确复现。
- 判断"某零件在截面上哪里"优先用**零件世界包围盒 8 角投影取屏幕包围盒**，比中心点命中更稳。

## 四、GLB 数据速查（不依赖 trimesh 的解析）

```python
import json, numpy as np

def glb_json_chunk(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"glTF"
    ln = int.from_bytes(data[12:16], "little")   # JSON chunk 长度
    return json.loads(data[20:20 + ln])

g = glb_json_chunk("model.glb")
# 零件名在 g["nodes"][i]["name"]；网格在 g["meshes"][n["mesh"]]；
# 颜色在 g["materials"][prim["material"]]["pbrMetallicRoughness"]["baseColorFactor"]；
# 包围盒在 POSITION accessor 的 min/max（需再乘节点世界矩阵）。
```

截图像素采样用 PIL：裁剪目标区域，按 HSV 饱和度过滤后取均值，与颜色组对照。

## 五、体积与耗时参考值（2026-10 实测）

| 项 | 数值 |
|----|------|
| 251MB STEP → GLB（cascadio, tol 0.1mm/0.5°, 并行） | 44.2MB / 205s |
| 3.6M 面 GLB base64 内嵌 HTML | 59.7MB（浏览器端 ~45s 完成解码+解析+合并） |
| 同精度若转 JSON 数组 | ≈ 145MB（弃用该方案的原因） |
| 内嵌 GLB 后建议内存 | ≥16GB 机器，首开 10~20s 需加载动画 |
