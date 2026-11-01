# snap（随附副本）

本目录的 `snap.mjs` 是从主项目**复制**过来的副本，目的是让 paper-figures 在被单独安装时也能截图，不必依赖 snap 技能先装好。

## 真相源

```
D:\Project\Zcode\snap\code\snap.mjs     ← 主项目，所有修改在这里做
```

## 同步

主项目更新后，把新版覆盖过来：

```bash
cp "D:/Project/Zcode/snap/code/snap.mjs" \
   "D:/Project/workspace/my_github/my-skills/paper-figures/scripts/snap/snap.mjs"
```

改完跑一遍主项目的回归：`node D:/Project/Zcode/snap/code/tests/run-tests.mjs`。

## 什么时候用它

| 输入 | 用什么 |
|---|---|
| `.svg` / `.pdf`（论文图、示意图） | **`scripts/preview.py`**（PyMuPDF 直出，零额外依赖） |
| `.html`（海报、演示页、网页） | 本目录 `snap.mjs` |
| 需要 audit / 像素对比 / 基线回归 | 本目录 `snap.mjs` |

## 依赖

Node.js 22+ 与本机 Chrome 或 Edge。论文图渲染不需要这些——用 `preview.py` 即可。
