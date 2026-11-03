#!/usr/bin/env node
// multi-publish-mcp — 多平台草稿 MCP 服务器（stdio，零构建）
//
// 架构复刻自 CSDN 同步助手扩展（v1.2.0）的适配器，映射关系:
//   扩展 runtime.fetch(带cookie+DNR注头) → 平台页面上下文里的 fetch（page.evaluate）
//   ——知乎网关认 UA/Origin，裸 HTTP 请求会被 MalformRequest 拒掉，必须在
//   zhuanlan.zhihu.com 页面里发（Origin/Referer/UA/cookie 全部自然正确）。
//
// 纪律沿用: 只存草稿不自动发布；结果不明不重试；幂等键 24h 内复用。
// 平台端点与参数提取自扩展 background/index.mjs（ext_adapters.txt / zhihu_adapter.txt）。

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import readline from "node:readline";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
// playwright-core 从本技能或 csdn-publish-mcp 的 node_modules 解析（共享依赖，避免装两份）
let chromiumApi;
try {
  chromiumApi = require("playwright-core");
} catch {
  const alt = path.join(os.homedir(), ".zcode", "skills", "csdn-publish-mcp", "scripts");
  chromiumApi = require(path.join(alt, "node_modules", "playwright-core"));
}
const { chromium } = chromiumApi;
const { marked } = require("marked");

// ---------------------------------------------------------------- 常量与配置

const RUNTIME_DIR = path.join(os.homedir(), ".multi-publish-mcp");
const TASKS_PATH = path.join(RUNTIME_DIR, "tasks.json");
// 复用 csdn-publish-mcp 的自动化 Chrome（登录态集中在一个配置档）
const BROWSER = {
  profileDir: path.join(os.homedir(), ".csdn-publish-mcp", "chrome-profile"),
  debugPort: 9222,
  candidates: [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(os.homedir(), "AppData", "Local", "Google", "Chrome", "Application", "chrome.exe"),
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ],
};

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(path.join(RUNTIME_DIR, "config.json"), "utf8"));
  } catch {
    return {};
  }
}

const basename = (p) => p.replace(/[\\/]/g, "/").split("/").pop();
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function log(...a) {
  console.error(`[multi-publish-mcp ${new Date().toISOString()}]`, ...a);
}

function readTasks() {
  try {
    const all = JSON.parse(fs.readFileSync(TASKS_PATH, "utf8"));
    const fresh = {};
    for (const [k, v] of Object.entries(all)) {
      if (Date.now() - v.ts < 24 * 3600 * 1000) fresh[k] = v;
    }
    return fresh;
  } catch {
    return {};
  }
}

function saveTask(key, result) {
  const all = readTasks();
  all[key] = { ts: Date.now(), result };
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
  fs.writeFileSync(TASKS_PATH, JSON.stringify(all, null, 1));
}

function stripFrontmatter(markdown, title) {
  let md = markdown;
  const fm = md.match(/^---\r?\n.*?\r?\n---\s*\r?\n?/s);
  if (fm) md = md.slice(fm[0].length);
  const firstH1 = md.match(/^# (\S[^\n]*)\r?\n+/);
  if (firstH1 && firstH1[1].trim() === title.trim()) md = md.slice(firstH1[0].length);
  return md.trim();
}

function replaceImageRefs(md, basenameToUrl) {
  let out = md;
  for (const [base, url] of Object.entries(basenameToUrl)) {
    const re = new RegExp(`\\]\\((?:\\./)?(?:assets/)?${escapeRe(base)}\\)`, "g");
    const re2 = new RegExp(`src="(?:\\./)?(?:assets/)?${escapeRe(base)}"`, "g");
    out = out.replace(re, `](${url})`).replace(re2, `src="${url}"`);
  }
  return out;
}

// ---------------------------------------------------------------- 浏览器管理

let browser = null;
let opChain = Promise.resolve();

function findChrome(cfg) {
  for (const p of BROWSER.candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

async function tryConnect(port) {
  try {
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`, { timeout: 5000 });
    return true;
  } catch {
    browser = null;
    return false;
  }
}

async function ensureBrowser({ allowLaunch = true } = {}) {
  if (browser) return;
  const cfg = loadConfig();
  const port = cfg.debugPort || BROWSER.debugPort;
  if (await tryConnect(port)) return;
  if (!allowLaunch) throw new Error("自动化 Chrome 未运行（doctor 只体检，不启动）");
  const exe = cfg.chromePath || findChrome(BROWSER);
  if (!exe) throw new Error("找不到 Chrome/Edge，请在 " + RUNTIME_DIR + " 配置 chromePath");

  fs.mkdirSync(BROWSER.profileDir, { recursive: true });
  log("启动自动化 Chrome:", exe);
  const child = spawn(
    exe,
    [
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${BROWSER.profileDir}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--window-size=1440,900",
      "about:blank",
    ],
    { detached: true, stdio: "ignore" }
  );
  child.unref();
  for (let i = 0; i < 45; i++) {
    await sleep(1000);
    if (await tryConnect(port)) break;
  }
  if (!browser) throw new Error(`Chrome 已拉起但 CDP(${port}) 连不上`);
}

async function browserContext() {
  await ensureBrowser();
  return browser.contexts()[0] || (await browser.newContext());
}

// ---------------------------------------------------------------- 通用: 带cookie的HTTP（等价扩展 runtime.fetch，无 CORS 限制）

async function httpFetch(url, opts = {}) {
  const ctx = await browserContext();
  return ctx.request.fetch(url, { ...opts, failOnStatusCode: false, timeout: 60000 });
}

// ---------------------------------------------------------------- 页面内 fetch 桥

// 在指定页面上发 fetch（Origin/Referer/UA/cookie 全部自然正确）
// 返回 {status, ok, body(text)}
async function pageFetch(page, url, { method = "GET", headers = {}, body = null, form = null } = {}) {
  const payload = [url, { method, headers, body, bodyB64: null, form }];
  let lastErr = null;
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const res = await page.evaluate(
        async ([u, o]) => {
          const init = { method: o.method || "GET", credentials: "include", headers: o.headers || {} };
          if (o.body) init.body = o.body;
          if (o.bodyB64) init.body = Uint8Array.from(atob(o.bodyB64), (c) => c.charCodeAt(0));
          if (o.form) {
            init.body = new URLSearchParams(o.form).toString();
            init.headers["Content-Type"] = "application/x-www-form-urlencoded";
          }
          const r = await fetch(u, init);
          const t = await r.text();
          return { status: r.status, ok: r.ok, body: t };
        },
        payload
      );
      if (res.status === 0) throw new Error(`页面内请求失败（CORS/网络）: ${url}`);
      return res;
    } catch (e) {
      lastErr = e;
      if (attempt < 2) {
        log("pageFetch retry after:", e.message?.slice?.(0, 80) || e);
        await sleep(1500);
      }
    }
  }
  throw lastErr;
}

function readJsonZ(res, what) {
  if (res.status === 401 || res.status === 403) {
    throw new Error(`${what}: 未登录或登录已过期（HTTP ${res.status}）——请在自动化 Chrome 里重新登录`);
  }
  if (!res.ok) throw new Error(`${what}: HTTP ${res.status} ${res.body.slice(0, 160)}`);
  try {
    return JSON.parse(res.body);
  } catch {
    throw new Error(`${what}: 响应不是有效 JSON - ${res.body.slice(0, 160)}`);
  }
}

// ---------------------------------------------------------------- 知乎适配器（草稿模式）

// 端点与参数提取自扩展 zhihu 适配器（zhihu_adapter.txt / zhihu_upload.txt）
// 网关认 UA/Origin —— 全部请求走 zhuanlan.zhihu.com 页面上下文
const ZHIHU_API = {
  me: "https://www.zhihu.com/api/v4/me",
  draftsCreate: "https://zhuanlan.zhihu.com/api/articles/drafts", // POST {title,content:"",delta_time:0} -> {id}
  draftUpdate: (id) => `https://zhuanlan.zhihu.com/api/articles/${id}/draft`, // PATCH {title,content}
  imageRegister: "https://api.zhihu.com/images", // POST {image_hash,source:"article"} -> {upload_file,upload_token}
  imageStatus: (id) => `https://api.zhihu.com/images/${id}`, // GET -> {status,original_hash}
  imageRemote: "https://zhuanlan.zhihu.com/api/uploaded_images", // POST form {url,source} -> {src}
  ossUploadBase: "https://zhihu-pics-upload.zhimg.com",
  picBase: "https://pic4.zhimg.com",
};

const ZHIHU_HEADERS = { "x-requested-with": "fetch" };

const zhihu = {
  id: "zhihu",
  name: "知乎",
  format: "html",

  // 按目标域名自动选承载页（CORS 各接口要求不同，实测结论）:
  //   zhuanlan.zhihu.com 草稿接口 → zhuanlan 页（同源）
  //   api.zhihu.com 图片接口 → www 页（实测 200；zhuanlan 来源会被拒）
  //   zhihu-pics-upload.zhimg.com OSS PUT → zhuanlan 页（编辑器自身的上传组合）
  async zFetch(url, opts) {
    const ctx = await browserContext();
    const host = new URL(url).hostname;
    const useZhuanlan = host === "zhuanlan.zhihu.com" || host === "zhihu-pics-upload.zhimg.com";
    const pattern = useZhuanlan ? /^https:\/\/zhuanlan\.zhihu\.com/ : /^https:\/\/www\.zhihu\.com/;
    const entry = useZhuanlan ? "https://zhuanlan.zhihu.com/" : "https://www.zhihu.com/";
    let p = ctx.pages().find((x) => pattern.test(x.url()));
    if (!p) {
      p = await ctx.newPage();
      await p.goto(entry, { waitUntil: "domcontentloaded", timeout: 60000 });
      await sleep(2000);
    }
    return pageFetch(p, url, opts);
  },

  async checkAuth() {
    const r = await this.zFetch(ZHIHU_API.me, { headers: ZHIHU_HEADERS });
    const j = readJsonZ(r, "知乎登录状态");
    if (j && j.id) return { authenticated: true, user: { id: j.id, name: j.name, url_token: j.url_token } };
    return { authenticated: false, error: "知乎未登录：请在自动化 Chrome 里登录 zhihu.com" };
  },

  async createDraft(title) {
    const r = await this.zFetch(ZHIHU_API.draftsCreate, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...ZHIHU_HEADERS },
      body: JSON.stringify({ title, content: "", delta_time: 0 }),
    });
    const j = readJsonZ(r, "创建知乎草稿");
    if (!j.id) throw new Error("创建知乎草稿失败: 响应缺少草稿 ID");
    return String(j.id);
  },

  async updateDraft(id, title, html) {
    const r = await this.zFetch(ZHIHU_API.draftUpdate(id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...ZHIHU_HEADERS },
      body: JSON.stringify({ title, content: html }),
    });
    if (!r.ok) throw new Error(`更新知乎草稿失败: HTTP ${r.status} ${r.body.slice(0, 160)}`);
    return true;
  },

  // 远程图转存（扩展同款: 表单 url+source）
  async uploadImageByUrl(url) {
    const r = await this.zFetch(ZHIHU_API.imageRemote, {
      method: "POST",
      form: { url, source: "article" },
      headers: ZHIHU_HEADERS,
    });
    const j = readJsonZ(r, "知乎远程图片转存");
    if (!j.src) throw new Error(j.msg || "知乎远程图片转存失败: 响应缺少图片地址");
    return j.src;
  },

  // 本地图直传: 注册(hash 去重) -> 已存在则轮询取 original_hash -> 否则 OSS PUT
  async uploadImageBinary(filePath) {
    const buf = fs.readFileSync(filePath);
    const hash = crypto.createHash("md5").update(buf).digest("hex");
    const ctype = filePath.toLowerCase().endsWith(".png")
      ? "image/png"
      : filePath.toLowerCase().endsWith(".gif")
        ? "image/gif"
        : filePath.toLowerCase().endsWith(".webp")
          ? "image/webp"
          : "image/jpeg";

    const r = await this.zFetch(ZHIHU_API.imageRegister, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...ZHIHU_HEADERS },
      body: JSON.stringify({ image_hash: hash, source: "article" }),
    });
    const j = readJsonZ(r, "获取知乎图片上传凭证");
    const uf = j.upload_file;
    const tk = j.upload_token;
    if (!uf || !tk) throw new Error("获取知乎图片上传凭证失败: 响应不完整");

    if (uf.state === 1) {
      for (let i = 0; i < 10; i++) {
        const s = await this.zFetch(ZHIHU_API.imageStatus(uf.image_id), { headers: ZHIHU_HEADERS });
        const sj = readJsonZ(s, "查询知乎图片状态");
        if (sj.status === "completed" || sj.original_hash) {
          if (!sj.original_hash) throw new Error("知乎图片已存在但缺少图片地址");
          return `${ZHIHU_API.picBase}/${sj.original_hash}`;
        }
        await sleep(1000);
      }
      throw new Error("知乎图片处理超时");
    }

    // OSS PUT（签名规则与扩展 ossUpload 一致；从页面上下文发，Origin 自然正确）
    const date = new Date().toUTCString();
    const ossHeaders = {
      "x-oss-date": date,
      "x-oss-security-token": tk.access_token,
      "x-oss-user-agent": "aliyun-sdk-js/6.8.0",
    };
    const canonical = Object.keys(ossHeaders)
      .sort()
      .map((k) => `${k}:${ossHeaders[k]}`)
      .join("\n");
    const objectKey = uf.object_key;
    const resource = `/zhihu-pics/${objectKey}`;
    const stringToSign = ["PUT", "", ctype, date, canonical, resource].join("\n");
    const sig = crypto.createHmac("sha1", tk.access_key).update(stringToSign).digest("base64");

    // OSS PUT 走后台请求通道（context.request）：无 CORS 限制、可带二进制与任意头——
    // 等价于扩展的 runtime.fetch；页面内发跨域 PUT 会被 CORS 预检拒掉（实测 Failed to fetch）
    const put = await httpFetch(`${ZHIHU_API.ossUploadBase}/${objectKey}`, {
      method: "PUT",
      headers: {
        Authorization: `OSS ${tk.access_id}:${sig}`,
        "Content-Type": ctype,
        Origin: "https://zhuanlan.zhihu.com",
        Referer: "https://zhuanlan.zhihu.com/",
        ...ossHeaders,
      },
      data: buf,
    });
    if (!put.ok()) throw new Error(`知乎图片 OSS 上传失败: HTTP ${put.status()} ${(await put.text()).slice(0, 160)}`);
    const finalKey = filePath.toLowerCase().endsWith(".gif") ? `${objectKey}.gif` : objectKey;
    return `${ZHIHU_API.picBase}/${finalKey}`;
  },

  // 知乎草稿 HTML 变换（扩展 transformContent 同款）
  transformHtml(html) {
    let r = html;
    r = r.replace(/<figure[^>]*>\s*(<table[\s\S]*?<\/table>)\s*<\/figure>/gi, "$1");
    r = r.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (m, inner) => {
      const thead = inner.match(/<thead[^>]*>([\s\S]*?)<\/thead>/i);
      const tbody = inner.match(/<tbody[^>]*>([\s\S]*?)<\/tbody>/i);
      let head = "";
      let body = "";
      if (thead) {
        head = thead[1].replace(/<td([^>]*)>/gi, "<th$1>").replace(/<\/td>/gi, "</th>");
      }
      if (tbody) {
        body = tbody[1];
      } else {
        body = inner.replace(/<thead[^>]*>[\s\S]*?<\/thead>/gi, "").replace(/<\/?tbody[^>]*>/gi, "");
      }
      if (!thead) {
        const firstTr = body.match(/<tr[^>]*>([\s\S]*?)<\/tr>/i);
        if (firstTr) {
          if (/<th[^>]*>/i.test(firstTr[1]) && !/<td[^>]*>/i.test(firstTr[1])) {
            head = firstTr[0];
            body = body.replace(firstTr[0], "");
          }
        }
      }
      return `<table data-draft-node="block" data-draft-type="table" data-size="normal" data-row-style="normal"><tbody>${head}${body}</tbody></table>`;
    });
    r = r.replace(/(<figure[^>]*>[\s\S]*?<\/figure>)|(<img\b[^>]*>)/gi, (m, fig, img) =>
      fig ? fig : `<figure>${img}</figure>`
    );
    r = r.replace(
      /<pre([^>]*)>\s*<code([^>]*)class="[^"]*\blanguage-([\w+-]+)\b[^"]*"([^>]*)>/gi,
      '<pre lang="$3"><code>'
    );
    r = r.replace(/\s*data-(?!draft)[a-z0-9-]+="[^"]*"/gi, "");
    r = r.replace(/\s*style="[^"]*"/gi, "");
    return r;
  },

  async syncDraft({ title, markdown, images }) {
    const auth = await this.checkAuth();
    if (!auth.authenticated) throw new Error(auth.error);

    const urlByBase = {};
    for (const img of images || []) {
      if (!fs.existsSync(img)) throw new Error(`图片不存在: ${img}`);
      urlByBase[basename(img)] = await this.uploadImageBinary(img);
      log("zhihu image uploaded:", basename(img));
    }

    let md = stripFrontmatter(markdown, title);
    md = replaceImageRefs(md, urlByBase);
    let html = marked.parse(md, { gfm: true, breaks: false });
    html = this.transformHtml(html);

    const id = await this.createDraft(title);
    await this.updateDraft(id, title, html);
    return {
      platform: "zhihu",
      draftId: id,
      draftUrl: `https://zhuanlan.zhihu.com/p/${id}/edit`,
      imagesUploaded: Object.keys(urlByBase).length,
    };
  },
};

// ---------------------------------------------------------------- 平台注册表

const PLATFORMS = {
  zhihu,
  // 以下平台的适配器端点已从扩展逆向提取完毕（见 SKILL.md 参考文档），待后续版本实现
  weixin: { id: "weixin", name: "微信公众号", todo: "端点已提取: cgi-bin/appmsg + filetransfer + cropimage（纯 fetch 模式，需先登录 mp.weixin.qq.com）" },
  xiaohongshu: { id: "xiaohongshu", name: "小红书", todo: "端点已提取: creator/publish/publish + edith 签名 + indexedDB 草稿（需页面注入 _webmsxyw）" },
  douyin: { id: "douyin", name: "抖音", todo: "端点已提取: aweme/create_v2 + STS 传图 + 安全验证处理（需页面注入）" },
};

async function dispatchSync(platform, args) {
  const adapter = PLATFORMS[platform];
  if (!adapter) throw new Error(`未知平台: ${platform}（可用: ${Object.keys(PLATFORMS).join(", ")}）`);
  if (adapter.todo) throw new Error(`${adapter.name} 适配器尚未实现。${adapter.todo}`);
  return adapter.syncDraft(args);
}

async function dispatchAuth(platform) {
  const adapter = PLATFORMS[platform];
  if (!adapter) throw new Error(`未知平台: ${platform}`);
  if (!adapter.checkAuth) {
    return { authenticated: false, note: adapter.todo };
  }
  return adapter.checkAuth();
}

// ---------------------------------------------------------------- 工具实现

async function toolCheckAuth({ platform }) {
  if (platform && platform !== "all") {
    const r = await dispatchAuth(platform);
    return { content: [{ type: "text", text: JSON.stringify({ [platform]: r }) }] };
  }
  const out = {};
  for (const [id, adapter] of Object.entries(PLATFORMS)) {
    try {
      out[id] = adapter.checkAuth ? await adapter.checkAuth() : { authenticated: false, note: adapter.todo };
    } catch (e) {
      out[id] = { authenticated: false, error: e.message };
    }
  }
  return { content: [{ type: "text", text: JSON.stringify(out) }] };
}

async function toolSyncArticle(args) {
  const { platform, title, markdown, images, idempotencyKey, articleId } = args;
  if (!platform || !title || !markdown) throw new Error("platform, title, markdown 必填");
  const key = idempotencyKey || crypto.randomUUID();
  const tasks = readTasks();
  if (tasks[key] && tasks[key].result) {
    return { content: [{ type: "text", text: JSON.stringify({ ...tasks[key].result, cached: true }) }] };
  }
  if (articleId) throw new Error("articleId 更新已有草稿暂未支持（zhihu v0.2）");

  const result = await dispatchSync(platform, { title, markdown, images });
  const full = { ...result, idempotencyKey: key };
  saveTask(key, full);
  return { content: [{ type: "text", text: JSON.stringify(full) }] };
}

async function toolDoctor() {
  const cfg = loadConfig();
  const here = path.dirname(fileURLToPath(import.meta.url));
  const cdpOk = await tryConnect(cfg.debugPort || BROWSER.debugPort);
  if (cdpOk) browser = null;
  const out = {
    runtimeDir: RUNTIME_DIR,
    chromePath: findChrome(BROWSER),
    cdpAttached: cdpOk,
    deps: {
      playwright: fs.existsSync(path.join(here, "node_modules", "playwright-core")),
      marked: fs.existsSync(path.join(here, "node_modules", "marked")),
    },
    platforms: Object.fromEntries(
      Object.entries(PLATFORMS).map(([k, v]) => [k, v.checkAuth ? "ready" : `todo: ${v.todo?.slice(0, 40)}…`])
    ),
  };
  return { content: [{ type: "text", text: JSON.stringify(out) }] };
}

const TOOLS = [
  {
    name: "check_auth",
    description: "检查各平台登录状态。platform 传具体平台 id 或 'all'。",
    inputSchema: {
      type: "object",
      properties: { platform: { type: "string", description: "zhihu | all" } },
      additionalProperties: false,
    },
  },
  {
    name: "sync_article",
    description:
      "把标题+Markdown 存成平台草稿（不做自动发布）。images 传本地图片绝对路径数组，自动上传平台图床并替换正文引用；自动剥离 YAML frontmatter 和与标题重复的首个 H1。当前支持 platform=zhihu。",
    inputSchema: {
      type: "object",
      properties: {
        platform: { type: "string", description: "zhihu" },
        title: { type: "string" },
        markdown: { type: "string" },
        images: { type: "array", items: { type: "string" } },
        idempotencyKey: { type: "string" },
      },
      required: ["platform", "title", "markdown"],
      additionalProperties: false,
    },
  },
  {
    name: "doctor",
    description: "体检：Chrome、依赖、CDP、各平台适配器就绪状态。只读不启动。",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

async function dispatch(name, args) {
  const run = opChain.then(() => {
    switch (name) {
      case "check_auth": return toolCheckAuth(args);
      case "sync_article": return toolSyncArticle(args);
      case "doctor": return toolDoctor(args);
      default: throw new Error(`未知工具: ${name}`);
    }
  });
  opChain = run.catch(() => {});
  return run;
}

// ---------------------------------------------------------------- MCP stdio 协议（手写最小实现）

function send(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

const serverInfo = { name: "multi-publish-mcp", version: "0.2.0" };

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    return;
  }
  const { id, method, params } = msg;
  if (id === undefined || id === null) return;

  switch (method) {
    case "initialize":
      send({
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: params?.protocolVersion || "2025-03-26",
          capabilities: { tools: {} },
          serverInfo,
        },
      });
      return;
    case "tools/list":
      send({ jsonrpc: "2.0", id, result: { tools: TOOLS } });
      return;
    case "tools/call": {
      const { name, arguments: args } = params || {};
      dispatch(name, args || {})
        .then((result) => send({ jsonrpc: "2.0", id, result }))
        .catch((err) =>
          send({
            jsonrpc: "2.0",
            id,
            result: { content: [{ type: "text", text: `ERROR: ${err.message}` }], isError: true },
          })
        );
      return;
    }
    case "prompts/list":
      send({ jsonrpc: "2.0", id, result: { prompts: [] } });
      return;
    case "resources/list":
      send({ jsonrpc: "2.0", id, result: { resources: [] } });
      return;
    case "ping":
      send({ jsonrpc: "2.0", id, result: {} });
      return;
    default:
      send({ jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } });
  }
});

process.on("disconnect", () => process.exit(0));
log("started, runtime dir:", RUNTIME_DIR);
