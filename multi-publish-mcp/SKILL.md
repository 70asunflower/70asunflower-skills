---
name: multi-publish-mcp
description: 自建多平台草稿 MCP 服务器（multi-publish-mcp），适配器架构逆向复刻自「CSDN 同步助手」扩展：知乎（已实现）、微信公众号/小红书/抖音（端点已提取待实现）。用 playwright-core CDP 接管自动化 Chrome 的 cookie，把本地 Markdown 连图存成各平台草稿，只存草稿不自动发布。当用户说「发知乎、传知乎、同步公众号/小红书/抖音」时使用。
agent_created: true
---

# multi-publish-mcp —— 多平台草稿 MCP

与 `csdn-publish-mcp`（本地文章→CSDN）互补：本技能做**出方向**（本地 → 其他平台），
替代已卸载的「CSDN 同步助手」扩展。只存草稿，发布人工确认。

## 适配器进度

| 平台 | 状态 | 模式 |
|---|---|---|
| 知乎 | ✅ 已实现（草稿） | 纯 fetch：`api/v4/me` + `api/articles/drafts` + `api/articles/{id}/draft`；图走 `api.zhihu.com/images`（MD5 去重）+ OSS PUT |
| 公众号 | 端点已提取 | 纯 fetch：`cgi-bin/operate_appmsg`（表单）+ `filetransfer` 传图 + `cropimage` 封面；token 从后台首页 HTML 正则提取 |
| 小红书 | 端点已提取 | 页面注入：creator 页 `_webmsxyw` 签名 → `edith.xiaohongshu.com`；草稿在页面 indexedDB `draft-database-v1` |
| 抖音 | 端点已提取 | 页面注入：STS 凭证传 TOS + `aweme/create_v2`；`x-tt-verify-passport-decision` = 要验证，放弃直发留草稿 |

逆向存档（端点与参数上下文）: 工作区 `csdn_publish/ext_adapters.txt`、`zhihu_adapter.txt`、
`zhihu_upload.txt`；扩展源码解包在 `csdn_publish/ext_src/`。

## MCP 工具

| 工具 | 参数 | 说明 |
|---|---|---|
| `check_auth` | `platform?`（默认 all） | 各平台登录状态 |
| `sync_article` | `platform, title, markdown, images?, idempotencyKey?` | 存草稿；images 传绝对路径，自动上传平台图床并替换引用 |
| `doctor` | — | Chrome/依赖/CDP/适配器就绪状态 |

## 首次安装

```cmd
cd /d <本技能目录>\scripts
..\run.cmd install     # npm i（marked + playwright-core）
```

浏览器复用 `~/.csdn-publish-mcp/chrome-profile`（与 csdn-publish-mcp 同一个自动化 Chrome，
登录态集中管理）。各平台需在该窗口登录一次。

## 架构纪律（沿用扩展的设计，勿破坏）

- **只存草稿**；publish 路径需要页面注入平台签名模块（知乎 webpack `wdfs1`/`x-zse-96`、
  小红书 `_webmsxyw`），后续版本再开
- 结果不明的请求**绝不自动重试**
- 幂等键 24h 内复用结果，防重复发帖
- 知乎 content 是**带 data-draft 属性的特定 HTML**（表格/代码块有专属变换），在
  `zhihu.transformHtml` 里，勿用通用 md→html 直出

## 已知坑位

- playwright-core 依赖解析：先找本技能 node_modules，回退 `csdn-publish-mcp/scripts/node_modules`
  （两技能共享一份依赖）。
- 未实现平台调用会报「端点已提取」提示，别当平台故障排查。

### 知乎适配器实测坑（2026-11）

1. **网关认 UA/Origin**：`api.zhihu.com` 的请求必须从 `www.zhihu.com` 页面上下文发
   （context.request 裸发会 400 MalformRequest）；`zhuanlan.zhihu.com` 草稿接口必须同源。
   → zFetch 按目标域名自动路由承载页，别改回裸 HTTP。
2. **本地图 OSS 直传必须走 context.request**（等价扩展 runtime.fetch）：带 Authorization
   的跨域 PUT 从页面里发会 CORS 预检失败（Failed to fetch）；后台通道可带二进制与任意头。
3. 图片注册的 `image_hash` 用 MD5 就行（只是去重键；服务端同 hash 直接返回
   `state:1`，轮询 `api.zhihu.com/images/{image_id}` 拿 original_hash 即最终地址）。
4. OSS 签名：`OSS access_id:sig`，sig = HMAC-SHA1(access_key,
   `PUT\n\n{ctype}\n{UTC日期}\n{x-oss-date,x-oss-security-token,x-oss-user-agent 按序}\n/zhihu-pics/{object_key}`)。
5. `pageFetch` 失败重试一次（瞬态 Failed to fetch 实测存在）。
6. 知乎草稿 content 是**特定 HTML**：表格必须 `data-draft-node/type` 属性、代码块
   `<pre lang>`、图片包 `<figure>`——变换逻辑在 `zhihu.transformHtml`，勿直出通用 HTML。
