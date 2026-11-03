---
name: csdn-publish-mcp
description: 自建 MCP 服务器（csdn-publish-mcp）：用 playwright-core 接管本工具专属的 Chrome 配置档，把本地 Markdown 文章连同图片存成 CSDN 草稿，图片自动上传 CSDN 官方图床并替换正文引用。当用户说「文章发到 CSDN、传 CSDN、存 CSDN 草稿、本地文章上传 CSDN」时使用。支持 check_login / upload_image_file / sync_article / doctor 四个 MCP 工具；首次使用要先安装依赖并登录一次 CSDN。
agent_created: true
---

# csdn-publish-mcp —— 本地文章 → CSDN 草稿

与官方「CSDN 同步助手」扩展（方向是 CSDN → 多平台，MCP 目标列表里没有 CSDN）互补：
本技能做反方向，**本地 Markdown → CSDN 草稿**。存草稿不做直接发布，发布人工确认。

## 何时使用

用户要把本地文章（思源导出、md 文件）发布到 CSDN 时。全链路：导出正文 + 收集图片 →
`sync_article`（服务端自动传图换官方图床 URL、替换引用、存草稿）→ 人工核对发布。

## 架构

```
MCP 客户端 ──stdio── server.mjs ──CDP── 专属 Chrome 配置档(~/.csdn-publish-mcp) ──> mp.csdn.net 编辑器
```

- 不写浏览器扩展、不逆向 API、不碰 cookie 文件；登录态持久在专属配置档里
- 图片经编辑器自带上传 = CSDN 官方图床（i-blog.csdnimg.cn），无防盗链问题
- 运行时状态（chrome-profile / tasks.json）在 `~/.csdn-publish-mcp/`，仓库里只有源码

## MCP 工具

| 工具 | 参数 | 说明 |
|---|---|---|
| `check_login` | — | 检查登录态（会打开编辑器页面） |
| `upload_image_file` | `filePath` | 单张图上传，返回图床 URL |
| `sync_article` | `title, markdown, images?, articleId?, idempotencyKey?` | 存草稿；images 传绝对路径数组，服务端逐张上传并按文件名替换正文引用；自动剥离 YAML frontmatter 和与标题重复的首个 H1；传 `articleId` 则更新已有草稿；同幂等键 24h 内复用结果 |
| `doctor` | — | 体检：Chrome 路径 / 依赖 / CDP 连接，只读不启动 |

## 首次安装（每台机器一次）

```cmd
cd /d <本技能目录>\scripts
..\run.cmd install     # npm i playwright-core（源码目录里装，全 agent 共享）
..\run.cmd test        # 冒烟：握手 + tools/list
```

首次 `sync_article` 会弹出自动化 Chrome 窗口 → 登录 CSDN 一次 → 之后免登录。

## 测试

```cmd
..\run.cmd test                       # MCP 握手冒烟
python <测试客户端> doctor             # 体检（只读）
```

## 已知坑位（2026-11 实测）

**编辑器架构**：账号默认可能是新版富文本编辑器（`mp.csdn.net/mp_blog/creation/editor/new`，
加载会卡死在遮罩）——必须走 `editor.csdn.net/md?notrack=1` 强制 Markdown 模式。正文是
StackEdit 系 **cledit** 引擎（`div.editor__inner[contenteditable]`），无 CodeMirror。

**cledit 三大坑**：
1. `insertText` 的裸换行被吞——42K 文章挤成 3 行。必须真剪贴板粘贴（最稳）→ 合成
   paste 事件 → 逐行 insertText+Enter，三级兜底；每种都按底部字数条的「行数」硬验证
   （innerText 因分区渲染不可信，行数是唯一全局可信信号）。
2. 图片上传入口是 `input.cfw-file-input`（accept 全为图片格式）；`input.hidden-file`
   是「导入 .md」用的，别混。
3. 连续 `setInputFiles` 3 次后上传 handler 失效（签名接口不再调用）——**每 3 张 reload
   一次编辑器**再 clearBody 即可恢复；已传图片不受影响。上传确认信号：预览区
   `img[src*="i-blog.csdnimg.cn/direct/"]` 计数（别用裸 `csdnimg`，会算上头像）。

**其他**：
- 标题 `input.article-bar__title` 带 `aria-hidden`，过不了 Playwright 可见性检查——
  等 `attached` + 原生 setter 填值。
- 图片上传内部走 `bizapi.csdn.net` 签名 + 华为 OBS 直传 + 回调，签名是前端 HMAC——
  不要逆向重写，永远复用页面自己的 handler。
- 保存草稿成功判定：URL 出现 `articleId` 或页面出现成功文案；两者都没有时报错让人工
  确认，不盲报成功。
- 所有工具串行执行（内部互斥）；ZCode 侧 `timeoutMs: 600000`（23 图长文要几分钟）。
- 选择器全部集中在 `scripts/server.mjs` 顶部 `SEL` 对象，CSDN 改版先改它。

## 与其他技能的关系

- 从思源导出文章用 `siyuan-kernel-ops`（exportMdContent + getFile 下载资源，
  注意其 getFile 是工作区根相对，资源要加 `/data/` 前缀）。
- 反方向（CSDN 已发文章 → 知乎/小红书等 16 平台）用官方「CSDN 同步助手」扩展的
  `csdn-article-sync-mcp`（ZCode 配置里同名服务器）。
