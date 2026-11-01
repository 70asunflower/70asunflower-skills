#!/usr/bin/env node
// WorkBuddy wrapper: SVG -> PNG via puppeteer-core + system Chrome/Edge
// Usage: node png_export.js <input.svg> [output.png] [width]
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const CHROME_CANDIDATES = [
  process.env.FIREWORKS_CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
].filter(Boolean);

async function main() {
  const svgPath = path.resolve(process.argv[2]);
  const pngPath = path.resolve(process.argv[3] || svgPath.replace(/\.svg$/, ".png"));
  const outWidth = Number(process.argv[4] || 1920);

  const svg = fs.readFileSync(svgPath, "utf8");
  let width = 1200, height = 800;
  const wm = svg.match(/width="(\d+(?:\.\d+)?)/);
  const hm = svg.match(/height="(\d+(?:\.\d+)?)/);
  const vbm = svg.match(/viewBox="[\d.\s-]+ (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/);
  if (wm && hm) { width = +wm[1]; height = +hm[1]; }
  else if (vbm) { width = +vbm[1]; height = +vbm[2]; }

  const executablePath = CHROME_CANDIDATES.find((p) => p && fs.existsSync(p));
  if (!executablePath) throw new Error("no Chrome/Edge found; set FIREWORKS_CHROME_PATH");

  const browser = await puppeteer.launch({
    executablePath,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  try {
    const page = await browser.newPage();
    const targetHeight = Math.round((height / width) * outWidth);
    await page.setViewport({ width: outWidth, height: targetHeight, deviceScaleFactor: 2 });
    await page.setContent(
      `<html><body style="margin:0;background:transparent"><img src="data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}" width="${outWidth}" height="${targetHeight}"></body></html>`,
      { waitUntil: "networkidle0" }
    );
    await page.screenshot({ path: pngPath, type: "png", omitBackground: true });
    console.log(`PNG_OK ${pngPath} ${outWidth}x${targetHeight}@2x`);
  } finally {
    await browser.close();
  }
}

main().catch((e) => { console.error(e.message || e); process.exit(1); });
