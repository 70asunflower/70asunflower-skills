# 技术架构图：fireworks 风格库

本 skill 是 [`fireworks-tech-graph`](https://github.com/yizhiyanhua-ai/fireworks-tech-graph)
的 WorkBuddy 包装层。**原 skill 已原样安装**在
`C:\Users\qilin\.workbuddy\skills\fireworks-tech-graph\`（保持上游一致，未改动）。
本包装只负责：① 修正资源定位（WorkBuddy 没有 `CLAUDE_SKILL_DIR`）；② 绑定本机
已配置的渲染运行时；③ 简化调用方式。

## SKILL_ROOT（硬编码，勿用环境变量）

```
C:\Users\qilin\.workbuddy\skills\fireworks-tech-graph
```

所有 references / scripts / templates 均相对该根目录。

## 本机运行时（已配置，2026-08-19 验证）

| 能力 | 运行时 | 状态 |
|---|---|---|
| SVG 生成/校验 | Python `C:\Users\qilin\.workbuddy\binaries\python\versions\3.13.12\python.exe` | ✅ |
| PNG 导出 | Node + puppeteer-core + 系统 Chrome（本包装脚本） | ✅ 已实测 |
| GIF 动画 | Node `svg2gif.js` + ffmpeg（可选） | ⚠️ 需 ffmpeg，先 `doctor` 探测 |
| HTML 交互导出 | Python `export-interactive-html.py` | ✅ |

**注意**：
- 本机 **cairosvg 不可用**（Windows 缺 `cairo-2.dll`），原包 `generate-diagram.sh` 的 cairosvg 分支会失败，**不要用它导出 PNG**。
- 原包 `svg2png.js` `require("puppeteer")` 会触发下载浏览器，**不要直接用**；用本包装的 `png_export.js`（puppeteer-core + 系统 Chrome/Edge）。

## 工作流（WorkBuddy 版）

> **默认只交付 SVG**（2026-08-26 用户裁定）：不主动导出 PNG/GIF；用户明确要求
> PNG/GIF/其他格式时，才按下方命令模板转换。视觉审查也改为直接 Read SVG 源码
> 检查几何/标签（或仅在已导出 PNG 时读图）。

1. **分类**图型：`architecture | data-flow | flowchart | sequence | comparison | timeline | mind-map | agent | memory | use-case | class | state-machine | er-diagram | network-topology`
2. **读参考**：默认 `references/style-1-flat-icon.md`（用户指定其他样式则读 `style-N-*.md`）+ `references/composition-quality-contract.md`（布局/质量契约）
3. **生成 SVG**：按参考样式直接写 `.svg` 文件到输出目录（`D:\Project\workspace\workbuddy\_diagrams\`）。**用 Python 逐行写文件**（列表 join），避免引号/转义/截断错误；所有文本内容做 XML 转义
4. **校验**：优先用 Python 直调校验器（Windows 下 `.sh` 包装有路径问题）：
   `python "$SKILL_ROOT/scripts/validate_svg.py" <file>.svg --check geometry --check composition`
5. **（按需）PNG 导出**：仅用户要求时执行——见下方命令模板（png_export.js）
6. **（按需）GIF**：用户要求动图时，先 `python "$SKILL_ROOT/scripts/fireworks.py" doctor` 探测；可行则 `motion.py` 流程
7. **视觉审查**：Read SVG 源码检查箭头坐标/标签越界；若已导出 PNG 则读图检查穿盒、碰撞、重叠；最多两轮修正。报告 `visual_review: passed`
8. **交付**：present_files 展示 SVG

## 命令模板（Windows 环境，直接复制）

```bash
SKILL_ROOT="C:/Users/qilin/.workbuddy/skills/fireworks-tech-graph"
OUT="D:/Project/workspace/workbuddy/_diagrams"
NODEEXE="C:/Users/qilin/.workbuddy/binaries/node/versions/22.22.2/node.exe"
export NODE_PATH="C:/Users/qilin/.workbuddy/binaries/node/workspace/node_modules"

# 校验 SVG
bash "$SKILL_ROOT/scripts/validate-svg.sh" "$OUT/arch.svg"

# 导出 PNG（宽 1920，@2x）
"$NODEEXE" "C:/Users/qilin/.workbuddy/skills/fireworks-tech-graph-wb/scripts/png_export.js" "$OUT/arch.svg" "$OUT/arch.png" 1920

# 环境自检（PNG/GIF 能力探测）
python "$SKILL_ROOT/scripts/fireworks.py" doctor
```

## 样式清单（styles 1–12）

1 Flat Icon · 2 Dark Terminal · 3 Blueprint · 4 Notion Clean · 5 Glassmorphism ·
6 Claude Official · 7 OpenAI · 8 Dark Luxury · 9 C4 Review Canvas · 10 Cloud Fabric ·
11 Event Transit · 12 Ops Pulse

默认 1（flat-icon）。用户指定风格时读对应 `references/style-N-*.md` 拿精确色板/排版。

## 已知限制

- **PNG**：cairosvg 不可用 → 统一走 puppeteer-core + 系统 Chrome（`png_export.js`）。若用户机器换了浏览器，改 `png_export.js` 的 `CHROME_CANDIDATES` 或设 `FIREWORKS_CHROME_PATH`。
- **GIF**：依赖 ffmpeg（系统 PATH 中）与 node workspace 的 puppeteer-core。`doctor` 输出 `animation_export.ok=false` 时告知用户"GIF 需安装 ffmpeg"，不强行生成。
- 原包更新：重新安装原 skill 后，本包装无需改动（SKILL_ROOT 不变）。
