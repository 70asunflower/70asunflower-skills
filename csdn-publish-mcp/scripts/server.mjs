#!/usr/bin/env node
// csdn-publish-mcp — 把本地文章存成 CSDN 草稿的 MCP 服务器（stdio，零构建）
//
// 架构: playwright-core 通过 CDP 接管一个本工具专属的 Chrome 配置档
// （首次运行弹出窗口登录 CSDN 一次，cookie 持久），驱动 editor.csdn.net/md
// 的 Markdown 编辑器。不写扩展、不逆向 API、不碰 cookie 文件；图片走编辑器
// 自带上传 = CSDN 官方图床。
//
// 实测要点（2026-11）:
// - 账号默认可能是富文本编辑器（mp.csdn.net/mp_blog/creation/editor/new 会卡
//   loading），必须走 editor.csdn.net/md?notrack=1 强制 Markdown 模式。
// - 正文是 CodeMirror 6（.cm-content），文本被虚拟化，不能靠 textContent 读全文；
//   一律用「全选 + insertText 整体替换」，上传结果用预览区 img[src] 计数确认。
//
// CSDN 编辑器改版时，所有脆弱点集中在下面 SEL 对象里，先改它。

import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import readline from "node:readline";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------- 常量与配置

const RUNTIME_DIR = path.join(os.homedir(), ".csdn-publish-mcp");
const PROFILE_DIR = path.join(RUNTIME_DIR, "chrome-profile");
const CONFIG_PATH = path.join(RUNTIME_DIR, "config.json");
const TASKS_PATH = path.join(RUNTIME_DIR, "tasks.json");
const IMG_HOST = "i-blog.csdnimg.cn";

function loadConfig() {
  const defaults = {
    chromeCandidates: [
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
      path.join(os.homedir(), "AppData", "Local", "Google", "Chrome", "Application", "chrome.exe"),
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    ],
    debugPort: 9222,
  };
  try {
    return { ...defaults, ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")) };
  } catch {
    return defaults;
  }
}

// CSDN 编辑器的脆弱点全部集中在此（按「改版只改这里」维护）
// 实测（2026-11）: editor.csdn.net/md 的正文是 StackEdit 系 cledit 引擎——
// div.editor__inner[contenteditable]，无 CodeMirror；图片上传入口是
// input.cfw-file-input（accept 全为图片格式；.hidden-file 是导入 .md 用的，别混）
const SEL = {
  editorUrl: "https://editor.csdn.net/md?notrack=1",
  loginHost: "passport.csdn.net",
  title: "input.article-bar__title",
  sourcePane: ".editor__inner",
  fileInput: "input.cfw-file-input",
  imgHost: IMG_HOST,
  draftBtnTexts: ["保存草稿"],
  saveToastTexts: ["保存成功", "草稿保存成功", "已保存"],
};

// ---------------------------------------------------------------- 小工具

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const basename = (p) => p.replace(/[\\/]/g, "/").split("/").pop();
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function log(...a) {
  console.error(`[csdn-publish-mcp ${new Date().toISOString()}]`, ...a);
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

function stripFrontmatter(markdown, title) {
  let md = markdown;
  // 注意: JS 正则没有 \A 锚（那是 Python 的），^ 配 /s（无 /m）等价字符串开头
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
let page = null;
let opChain = Promise.resolve(); // 简单互斥：操作串行执行

function findChrome(cfg) {
  for (const p of cfg.chromeCandidates) {
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
  const port = cfg.debugPort;
  if (await tryConnect(port)) return;
  if (!allowLaunch) throw new Error("Chrome 自动化实例未运行（doctor 只体检，不启动）");

  const exe = findChrome(cfg);
  if (!exe) throw new Error("找不到 Chrome/Edge，请在 " + CONFIG_PATH + " 配置 chromeCandidates");

  fs.mkdirSync(PROFILE_DIR, { recursive: true });
  log("启动自动化 Chrome:", exe, "profile:", PROFILE_DIR);
  const child = spawn(
    exe,
    [
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${PROFILE_DIR}`,
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
  if (!browser) throw new Error(`Chrome 已拉起但 CDP(${port}) 连不上；若端口被占用请关闭旧的自动化实例后重试`);
}

async function currentPage() {
  await ensureBrowser();
  const ctx = browser.contexts()[0] || (await browser.newContext());
  page = ctx.pages().find((p) => p.url().includes("csdn.net")) || (await ctx.newPage());
  return page;
}

// ---------------------------------------------------------------- 工具实现

async function toolCheckLogin() {
  const p = await currentPage();
  await p.goto(SEL.editorUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await sleep(3000);
  const loggedIn = !p.url().includes(SEL.loginHost);
  return { content: [{ type: "text", text: JSON.stringify({ loggedIn, url: p.url() }) }] };
}

// 打开 md 编辑器并等待挂载（cm-content 出现 = 正文编辑器就绪）
// 注意: 标题 input 带 aria-hidden，不能用 visible 判定，一律 attached
async function openEditor() {
  const p = await currentPage();
  await p.goto(SEL.editorUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (p.url().includes(SEL.loginHost)) {
    throw new Error("CSDN 未登录：请在弹出的自动化 Chrome 窗口里登录 mp.csdn.net（登录一次会记住）");
  }
  await p.waitForSelector(SEL.title, { state: "attached", timeout: 90000 });
  await p.waitForSelector(SEL.sourcePane, { state: "attached", timeout: 90000 });
  return p;
}

// aria-hidden 的 input 过不了 fill 的可见性检查，用原生 setter + input 事件
async function setTitle(p, title) {
  await p.evaluate(
    ([sel, v]) => {
      const el = document.querySelector(sel);
      const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      set.call(el, v);
      el.dispatchEvent(new Event("input", { bubbles: true }));
    },
    [SEL.title, title]
  );
}

async function focusSourcePane(p) {
  await p.click(SEL.sourcePane, { timeout: 15000 });
}

// 清空正文（欢迎文档），光标留在编辑器内
async function clearBody(p) {
  await focusSourcePane(p);
  await p.keyboard.press("Control+a");
  await p.keyboard.press("Delete");
  await sleep(300);
}

// 上传单张图: 走编辑器自带 file input（内部完成签名+OBS直传+回调），
// 用预览区 img[src*=i-blog…/direct/] 计数确认；失败重试 3 次
async function uploadOneImage(p, absPath) {
  const imgSel = `img[src*="${SEL.imgHost}/direct/"]`;
  const before = await p.evaluate((s) => document.querySelectorAll(s).length, imgSel);
  const want = before + 1;

  for (let attempt = 1; attempt <= 3; attempt++) {
    // 上传 input 是隐藏的，只等 attached（setInputFiles 不需要可见）
    const input = await p.waitForSelector(SEL.fileInput, { state: "attached", timeout: 15000 });
    await input.setInputFiles(absPath);
    const ok = await p
      .waitForFunction(([s, n]) => document.querySelectorAll(s).length >= n, [imgSel, want], {
        timeout: 90000,
      })
      .then(() => true)
      .catch(() => false);
    if (ok) {
      const urls = await p.evaluate((s) => [...document.querySelectorAll(s)].map((i) => i.src), imgSel);
      return urls[urls.length - 1];
    }
    if (attempt < 3) {
      log(`upload retry ${attempt + 1}/3: ${basename(absPath)}`);
      await p.keyboard.press("Escape").catch(() => {}); // 清掉可能的弹窗/提示
      await sleep(3000);
    }
  }
  throw new Error(`图片上传 3 次未确认（${basename(absPath)}）——截图检查编辑器是否有报错弹窗`);
}

// 读底部字数条的行数（"Markdown N 字数 M 行数"）——cledit 分区渲染导致
// innerText 不可靠，行数是唯一可信的全局信号
async function editorLines(p) {
  return p.evaluate(() => {
    const m = document.body.innerText.match(/([\d,]+)\s*行数/);
    return m ? parseInt(m[1].replace(/,/g, ""), 10) : -1;
  });
}

// 整体替换正文。cledit 的坑：insertText 的裸换行会被吞掉（整文挤成几行），
// 所以按优先级试三种写法，每种都用行数硬验证：
//   1. 真剪贴板粘贴（换行处理最完整）
//   2. 合成 paste 事件（DataTransfer 带 text/plain）
//   3. insertText 逐行 + Enter（慢但保真）
async function setBodyText(p, text, minLines) {
  await focusSourcePane(p);
  await p.keyboard.press("Control+a");

  // 1. 真剪贴板
  let how = "none";
  try {
    await p.evaluate((t) => navigator.clipboard.writeText(t), text);
    await p.keyboard.press("Control+v");
    how = "clipboard";
  } catch {
    how = "none";
  }
  if (await waitLines(p, minLines)) return how;

  // 2. 合成 paste 事件
  await focusSourcePane(p);
  await p.keyboard.press("Control+a");
  await p.evaluate((t) => {
    const dt = new DataTransfer();
    dt.setData("text/plain", t);
    const el = document.querySelector(".editor__inner");
    el.focus();
    el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
  }, text);
  how = "synthetic-paste";
  if (await waitLines(p, minLines)) return how;

  // 3. 逐行 insertText
  await focusSourcePane(p);
  await p.keyboard.press("Control+a");
  const arr = text.split("\n");
  for (let i = 0; i < arr.length; i++) {
    await p.keyboard.insertText(arr[i]);
    if (i < arr.length - 1) await p.keyboard.press("Enter");
  }
  how = "insert-text-lines";
  if (await waitLines(p, minLines)) return how;
  throw new Error(`正文写入后行数不对（期望≥${minLines}，实际 ${await editorLines(p)}）——三种策略都失败`);
}

async function waitLines(p, minLines) {
  return p
    .waitForFunction(
      (n) => {
        const m = document.body.innerText.match(/([\d,]+)\s*行数/);
        return m ? parseInt(m[1].replace(/,/g, ""), 10) >= n : false;
      },
      minLines,
      { timeout: 30000 }
    )
    .then(() => true)
    .catch(() => false);
}

async function saveDraft(p) {
  const loc = p.locator(`button:has-text("${SEL.draftBtnTexts[0]}")`).first();
  if ((await loc.count()) === 0) throw new Error("找不到「保存草稿」按钮——CSDN 可能改版，更新 SEL.draftBtnTexts");
  await loc.click({ timeout: 5000 });
  const ok = await p
    .waitForFunction(
      ([texts]) => {
        if (location.href.includes("articleId")) return true;
        const t = document.body.innerText;
        return texts.some((x) => t.includes(x));
      },
      [SEL.saveToastTexts],
      { timeout: 90000 }
    )
    .then(() => true)
    .catch(() => false);
  if (!ok) throw new Error("保存草稿后既没跳转 articleId 也没看到成功提示——请人工确认草稿是否已存在");
  await sleep(1500);
  return p.url();
}

async function toolUploadImage({ filePath }) {
  if (!filePath || !fs.existsSync(filePath)) throw new Error(`文件不存在: ${filePath}`);
  const p = await openEditor();
  const url = await uploadOneImage(p, filePath);
  return { content: [{ type: "text", text: url }] };
}

async function toolSyncArticle({ title, markdown, images, idempotencyKey, articleId }) {
  if (!title || !markdown) throw new Error("title 和 markdown 必填");
  const key = idempotencyKey || crypto.randomUUID();
  const tasks = readTasks();
  if (tasks[key] && tasks[key].result) {
    return { content: [{ type: "text", text: JSON.stringify({ ...tasks[key].result, cached: true }) }] };
  }

  const p = await currentPage();
  const url = articleId
    ? SEL.editorUrl + "&articleId=" + articleId
    : SEL.editorUrl;
  await p.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (p.url().includes(SEL.loginHost)) {
    throw new Error("CSDN 未登录：请在弹出的自动化 Chrome 窗口里登录 mp.csdn.net（登录一次会记住）");
  }
  await p.waitForSelector(SEL.title, { state: "attached", timeout: 90000 });
  await p.waitForSelector(SEL.sourcePane, { state: "attached", timeout: 90000 });
  if (articleId) await sleep(5000); // 带文章id时会加载旧内容，等它挂完再整体替换
  await clearBody(p);

  const urlByBase = {};
  let sinceReload = 0;
  for (const img of images || []) {
    if (!fs.existsSync(img)) throw new Error(`图片不存在: ${img}`);
    // 实测: 连续 setInputFiles 3 次后编辑器内部上传 handler 失效（签名接口不再调用），
    // 每 3 张 reload 一次编辑器即可恢复；已传图片不受影响
    if (sinceReload >= 3) {
      await p.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
      await p.waitForSelector(SEL.title, { state: "attached", timeout: 90000 });
      await p.waitForSelector(SEL.sourcePane, { state: "attached", timeout: 90000 });
      await clearBody(p);
      sinceReload = 0;
      log("editor reloaded to refresh upload pipeline");
    }
    urlByBase[basename(img)] = await uploadOneImage(p, img);
    sinceReload++;
    log("uploaded", basename(img), "->", urlByBase[basename(img)]);
  }

  let md = stripFrontmatter(markdown, title);
  md = replaceImageRefs(md, urlByBase);

  // 行数硬验证: 非空行 × 0.9 为下限
  const nonEmpty = md.split("\n").filter((l) => l.trim()).length;
  const minLines = Math.max(1, Math.ceil(nonEmpty * 0.9));

  // 上传过程会把 ![](url) 追加进正文，最后整体替换一次，顺带覆盖欢迎文档
  const how = await setBodyText(p, md, minLines);
  log("body written via", how, "lines≥", minLines);
  await setTitle(p, title);
  const finalUrl = await saveDraft(p);
  const m = finalUrl.match(/articleId=(\d+)/);
  const result = {
    draftUrl: finalUrl,
    articleId: m ? m[1] : null,
    imagesUploaded: Object.keys(urlByBase).length,
    idempotencyKey: key,
  };
  const all = readTasks();
  all[key] = { ts: Date.now(), result };
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
  fs.writeFileSync(TASKS_PATH, JSON.stringify(all, null, 1));
  return { content: [{ type: "text", text: JSON.stringify(result) }] };
}

async function toolDoctor() {
  const cfg = loadConfig();
  const here = path.dirname(fileURLToPath(import.meta.url));
  const cdpOk = await tryConnect(cfg.debugPort);
  if (cdpOk) browser = null; // 体检只探测，不占用句柄
  const out = {
    runtimeDir: RUNTIME_DIR,
    chromePath: findChrome(cfg),
    profileExists: fs.existsSync(PROFILE_DIR),
    depsInstalled: fs.existsSync(path.join(here, "node_modules", "playwright-core")),
    cdpAttached: cdpOk,
  };
  return { content: [{ type: "text", text: JSON.stringify(out) }] };
}

const TOOLS = [
  {
    name: "check_login",
    description: "检查 CSDN 自动化 Chrome 的登录状态。",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "upload_image_file",
    description: "上传本地图片到 CSDN 官方图床，返回图片 URL（会打开/复用 Markdown 编辑器页面）。",
    inputSchema: {
      type: "object",
      properties: { filePath: { type: "string", description: "图片绝对路径" } },
      required: ["filePath"],
      additionalProperties: false,
    },
  },
  {
    name: "sync_article",
    description:
      "把标题+Markdown 存成 CSDN 草稿（不做直接发布）。images 传本地图片绝对路径数组：逐张上传官方图床并自动替换正文里的同名引用；markdown 里的 YAML frontmatter 和与标题重复的首个 H1 会被剥离。",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        markdown: { type: "string" },
        images: { type: "array", items: { type: "string", description: "图片绝对路径" } },
        articleId: { type: "string", description: "传入则更新已有草稿，否则新建" },
        idempotencyKey: { type: "string", description: "同一键 24h 内复用上次结果" },
      },
      required: ["title", "markdown"],
      additionalProperties: false,
    },
  },
  {
    name: "doctor",
    description: "体检：Chrome 路径、依赖安装、CDP 连接、配置档。只读不启动。",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

async function dispatch(name, args) {
  // 全部工具串行执行，避免并发操作同一个编辑器页面
  const run = opChain.then(() => {
    switch (name) {
      case "check_login": return toolCheckLogin(args);
      case "upload_image_file": return toolUploadImage(args);
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

const serverInfo = { name: "csdn-publish-mcp", version: "0.3.0" };

const rl = readline.createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    return;
  }
  const { id, method, params } = msg;
  if (id === undefined || id === null) return; // notification，忽略

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
            result: {
              content: [{ type: "text", text: `ERROR: ${err.message}` }],
              isError: true,
            },
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
