# -*- coding: utf-8 -*-
"""layoutfix.tune — 本地拖动界面：人拖一下，图立刻改好，同时记一行可重放的清单。

为什么是「两个都写」：
  - 只改图：人马上看到效果，但 agent 下次重新生成就全丢；
  - 只写清单：重跑不丢，但人得等 agent 跑一轮才看到结果；
  - 所以拖动落地时同时做两件事——改文件 + 追加 .nudge.jsonl。

服务只监听 127.0.0.1，用完 Ctrl+C 即走。
"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import edit
import probe

WEB = Path(__file__).parent / "web" / "index.html"

SELFTEST = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>layoutfix selftest</title><style>
body{font:12px/1.75 "Segoe UI","Noto Sans SC",sans-serif;margin:0;background:#f4f4f2}
#log{padding:12px 16px;font-family:"Cascadia Mono",Consolas,monospace;font-size:12px;white-space:pre-wrap}
.pass{color:#0f6e56}.fail{color:#b3261e}
iframe{width:1200px;height:720px;border:0;display:block}
</style></head><body>
<div id="log">running…</div>
<iframe id="fr" src="/"></iframe>
<script>
const out = [], log = document.getElementById('log'), fr = document.getElementById('fr');
const say = (s, ok) => out.push('<span class="' + (ok === false ? 'fail' : 'pass') + '">' + s + '</span>');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const state = () => fetch('/state').then(r => r.json());
const fig = () => fetch('/fig.svg').then(r => r.text());

fr.onload = async () => {
  await sleep(1000);
  const W = fr.contentWindow, D = fr.contentDocument;
  const el = D.querySelector('[data-ffid="text:4"]');
  if(!el){ log.innerHTML = '<span class="fail">FAIL 找不到 text:4</span>'; return; }
  const before = await state();
  const mk = (t,x,y) => new W.MouseEvent(t,{bubbles:true,cancelable:true,clientX:x,clientY:y});
  const r = el.getBoundingClientRect();
  const cx = r.left + r.width/2, cy = r.top + r.height/2;

  // 1) 点选 → 属性面板出现，字号有值
  el.dispatchEvent(mk('mousedown', cx, cy));
  W.dispatchEvent(mk('mouseup', cx, cy));
  await sleep(150);
  const props = D.getElementById('props');
  const fsVal = D.getElementById('p-fs').value;
  say('点选 text:4  属性面板=' + (props.style.display !== 'none' ? '显示' : '隐藏')
      + '  字号=' + fsVal + '  宽=' + D.getElementById('p-w').value, props.style.display !== 'none');

  // 2) 拖角手柄存在
  const h = D.querySelector('#ff-handle rect');
  say('拖角手柄 ' + (h ? '已渲染 bbox=' + Math.round(h.getAttribute('width')) : '缺失'), !!h);

  // 3) 拖角 = Word 式折行宽度：向左拖窄 → 实时重排成多行、内容不变；
  //    撤销后字节级还原（行距节奏、空格一个不动）
  const raw0 = await fig();
  if(h){
    const hr = h.getBoundingClientRect();
    const er = el.getBoundingClientRect();
    const hx = hr.left + hr.width/2, hy = hr.top + hr.height/2;
    h.dispatchEvent(mk('mousedown', hx, hy));
    await sleep(50);
    const tx = hx - er.width * 0.45;      // 收窄近一半，单行长句必然折行
    for(let i=1;i<=5;i++){ W.dispatchEvent(mk('mousemove', hx + (tx - hx) * i / 5, hy)); await sleep(30); }
    W.dispatchEvent(mk('mouseup', tx, hy));
    await sleep(900);
    const el2 = D.querySelector('[data-ffid="text:4"]');
    const spans = el2 ? el2.querySelectorAll('tspan') : [];
    // 内容保持 = 去掉全部空白后逐字一致（断行吃掉的只有空格/行界，不该丢字）
    const squish = s => (s || '').replace(/\s+/g, '');
    const before = squish(el.textContent);
    const joined = spans.length ? squish(Array.from(spans).map(t=>t.textContent).join(''))
                                : squish(el2 ? el2.textContent : '');
    say('拖角收窄 → 折行 ' + spans.length + ' 行，内容保持 ' +
        (joined === before),
        spans.length >= 2 && joined === before);
    await fetch('/undo', {method:'POST'});
    await sleep(300);
    const raw2 = await fig();
    say('撤销折行 → 字节级还原 ' + (raw2 === raw0 ? '一致' : '不一致'), raw2 === raw0);
  }

  // 4) 面板输入改宽度（矩形）
  const rect = D.querySelector('[data-ffid="rect:2"]');
  if(rect){
    const rr = rect.getBoundingClientRect();
    rect.dispatchEvent(mk('mousedown', rr.left + 10, rr.top + 10));
    W.dispatchEvent(mk('mouseup', rr.left + 10, rr.top + 10));
    await sleep(120);
    const pw = D.getElementById('p-w');
    say('选中 rect:2  宽=' + pw.value + '  高=' + D.getElementById('p-h').value, !pw.disabled);
    const s1 = await state();
    await fetch('/set', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id:'rect:2', attrs:{width: 333}})});
    await sleep(300);
    const s2 = await state();
    const raw = await fig();
    say('改宽 → width="333" ' + (raw.indexOf('width="333"') >= 0 ? '已写入' : '未写入'),
        raw.indexOf('width="333"') >= 0);
    await fetch('/undo', {method:'POST'});
    await sleep(300);
    const s3 = await state();
    say('撤销后清单 ' + s3.ops.length + ' 条（应为 ' + s1.ops.length + '）',
        s3.ops.length === s1.ops.length);
  }

  // 4b) 文字内容编辑：改内容 + 回车分行转 tspan；撤销后必须字节级还原
  {
    const raw0 = await fig();
    await fetch('/set_text', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id:'text:4', text:'新内容甲\\n新内容乙'})});
    await sleep(300);
    const raw1 = await fig();
    const multi = raw1.indexOf('新内容甲') >= 0 && raw1.indexOf('<tspan') >= 0;
    say('改文字 → 两行 tspan ' + (multi ? '已写入' : '未写入'), multi);
    await fetch('/undo', {method:'POST'});
    await sleep(300);
    const raw2 = await fig();
    say('撤销文字 → 字节级还原 ' + (raw2 === raw0 ? '一致' : '不一致'), raw2 === raw0);
  }

  // 5) 主题与反相：断言按钮状态与生效状态一致，不只看按钮在不在
  const html = D.documentElement;
  const bl = D.getElementById('t-light'), bd = D.getElementById('t-dark');
  const inv = D.getElementById('t-invert');
  const st = () => ({ theme: html.getAttribute('data-theme'),
                      lightOn: bl.classList.contains('on'),
                      darkOn: bd.classList.contains('on'),
                      invDis: inv.disabled,
                      invOn: inv.classList.contains('on'),
                      cls: html.classList.contains('invert') });
  const fmt = o => '亮=' + o.lightOn + ' 暗=' + o.darkOn + ' 反相禁用=' + o.invDis +
                   ' 反相高亮=' + o.invOn + ' invert类=' + o.cls;

  const a = st();
  say('初始亮色：' + fmt(a), a.theme === 'light' && a.lightOn && !a.darkOn
      && a.invDis && !a.invertClass && !a.invOn);

  bd.click(); await sleep(120);
  const b = st();
  say('点暗：' + fmt(b), b.theme === 'dark' && !b.lightOn && b.darkOn
      && !b.invDis && b.invOn && b.cls);

  inv.click(); await sleep(120);
  const c = st();
  say('点反相：' + fmt(c), !c.invOn && !c.cls && c.theme === 'dark');

  bl.click(); await sleep(120);
  const e = st();
  say('回亮色：' + fmt(e), e.theme === 'light' && e.lightOn
      && e.invDis && !e.cls && !e.invOn);

  // 6) 图层顺序 + 重做 + 对齐按钮
  const el3 = D.querySelector('[data-ffid="text:4"]');
  if(el3){
    const r3 = el3.getBoundingClientRect();
    el3.dispatchEvent(mk('mousedown', r3.left + 5, r3.top + 5));
    W.dispatchEvent(mk('mouseup', r3.left + 5, r3.top + 5));
    await sleep(150);
    const oBtn = D.querySelector('#row-order [data-order="front"]');
    const aBtn = D.querySelector('#row-text [data-anchor="middle"]');
    say('图层按钮=' + !!oBtn + '  对齐按钮=' + !!aBtn, !!oBtn && !!aBtn);

    const s1 = await state();
    if(oBtn){
      oBtn.click();
      await sleep(700);
      const s2 = await state();
      const o2 = s2.ops[s2.ops.length - 1];
      say('置顶 → op=' + (o2 && o2.op) + '  清单 ' + s2.ops.length,
          !!o2 && o2.op === 'order' && s2.ops.length === s1.ops.length + 1);

      await fetch('/undo', {method:'POST'});
      await sleep(350);
      const s3 = await state();
      await fetch('/redo', {method:'POST'});
      await sleep(350);
      const s4 = await state();
      say('撤销→重做  清单 ' + s3.ops.length + ' → ' + s4.ops.length,
          s3.ops.length === s1.ops.length && s4.ops.length === s1.ops.length + 1);
    }
  }

  // 7) Ctrl 多选 → 整体拖动 = 一条 move_multi → 撤销字节级还原
  {
    const raw0 = await fig();
    const a = D.querySelector('[data-ffid="text:5"]');
    const b = D.querySelector('[data-ffid="text:6"]');
    if(a && b){
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      a.dispatchEvent(mk('mousedown', ra.left+2, ra.top+2));
      W.dispatchEvent(mk('mouseup', ra.left+2, ra.top+2));
      await sleep(120);
      b.dispatchEvent(new W.MouseEvent('mousedown', {bubbles:true, cancelable:true,
        clientX:rb.left+2, clientY:rb.top+2, ctrlKey:true}));
      W.dispatchEvent(new W.MouseEvent('mouseup', {bubbles:true}));
      await sleep(120);
      say('Ctrl 加选 → 状态栏=' + D.getElementById('st-id').textContent,
          D.getElementById('st-id').textContent.indexOf('2') >= 0);
      a.dispatchEvent(mk('mousedown', ra.left+2, ra.top+2));
      await sleep(50);
      for(let i=1;i<=4;i++){ W.dispatchEvent(mk('mousemove', ra.left+2+i*3, ra.top+2)); await sleep(25); }
      W.dispatchEvent(mk('mouseup', ra.left+2+12, ra.top+2));
      await sleep(900);
      const s2 = await state();
      const lo = s2.ops[s2.ops.length-1];
      say('整体拖 → op=' + (lo&&lo.op) + ' n=' + (lo&&lo.n),
          !!lo && lo.op === 'move_multi' && lo.n === 2);
      await fetch('/undo', {method:'POST'});
      await sleep(300);
      const raw2 = await fig();
      say('撤销整体拖 → 字节还原 ' + (raw2 === raw0 ? '一致' : '不一致'), raw2 === raw0);
    } else {
      say('text:5/6 缺失，跳过多选回归', true);
    }
  }

  const fin = await state();
  log.innerHTML = out.join('<br>') + '<br><br>最终违例 ' + fin.counts.violations + ' 条 / 改动 ' + fin.ops.length + ' 条';
};
</script></body></html>"""


def build_page(fig: Path, unit_mm: float) -> str:
    raw = edit.read_raw(fig)
    html = WEB.read_text(encoding="utf-8")
    return (html.replace("{{SVG}}", edit.annotate(raw))
                .replace("{{UNIT_MM}}", repr(unit_mm)))


def state_of(fig: Path) -> dict:
    rep = probe.run(fig)
    ops = edit.read_ops(fig)
    return {
        "file": str(fig),
        "unit_mm": rep["unit_mm"],
        "counts": rep["counts"],
        "violations": rep["violations"],
        "ops": ops,
        # 同目录可切换的图：界面顶栏的下拉列表数据源
        "files": sorted(p.name for p in fig.parent.glob("*.svg")),
        # 字段叫 touched 而不是 pinned：它只是"你动过的元素"，不是"已定稿"。
        # 早期版本在状态栏显示"已定稿 N"，但界面上没有任何入口能定稿，
        # 数字永远是 0 或者等于改动数，属于承诺了不存在的能力。
        "touched": sorted({o["id"] for o in ops if o.get("op") == "move"}),
    }


def serve(fig: Path, port: int = 8770, open_browser: bool = True,
          idle_minutes: float = 0.0) -> None:
    fig = fig.resolve()
    if not fig.exists():
        raise SystemExit(f"文件不存在: {fig}")
    lock = threading.Lock()
    cur = {"fig": fig}               # 当前图：?file= 可切换到同目录其他 svg
    # 重做栈按文件隔离：切到另一张图再切回来，撤销历史不能串台
    redo_stacks: dict[str, list[dict]] = {}
    def stacks_for(f: Path) -> list[dict]:
        return redo_stacks.setdefault(os.path.normcase(str(f)), [])
    def get_fig() -> Path:
        return cur["fig"]
    # 心跳时间戳：页面开着就每 15s 打一次 /ping；空闲超时的判断依据
    seen = {"t": time.time()}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body: bytes, ctype="application/json; charset=utf-8",
                  code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            seen["t"] = time.time()
            # 必须剥掉查询串：/?z=0.5 与 / 是同一个页面，
            # 直接比 self.path 会把它当成 404。
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path in ("/", "/index.html"):
                    # ?file=name.svg：切到同目录其他图。basename 校验挡住
                    # 路径穿越——切换器只在本目录内活动。
                    req_file = parse_qs(parsed.query).get("file", [None])[0]
                    if req_file:
                        base = os.path.basename(req_file)
                        if base.endswith(".svg"):
                            cand = get_fig().parent / base
                            if cand.is_file():
                                cur["fig"] = cand
                    # 整个「探测 + 生成页面」都持锁：write 是先截断再写，
                    # 并发下不加锁会读到半截文件，ET 解析直接抛错。
                    with lock:
                        f = get_fig()
                        rep = probe.run(f)
                        page = build_page(f, rep["unit_mm"])
                    self._send(page.encode("utf-8"), "text/html; charset=utf-8")
                elif path == "/fig.svg":
                    with lock:
                        raw = edit.read_raw(get_fig())
                    self._send(edit.annotate(raw).encode("utf-8"),
                               "image/svg+xml; charset=utf-8")
                elif path == "/state":
                    with lock:
                        st = state_of(get_fig())
                    self._send(json.dumps(st, ensure_ascii=False).encode("utf-8"))
                elif path == "/ping":
                    # 心跳：页面开着每 15s 打一次。空闲自关的依据就是它——
                    # 关标签页后心跳停止，到点服务自行退出；刷新/导航不受影响
                    self._send(json.dumps({
                        "ok": True,
                        "idle_left_min": round(max(0.0, idle_minutes * 60
                            - (time.time() - seen["t"])) / 60, 1),
                    }).encode("utf-8"))
                elif path == "/selftest":
                    self._send(SELFTEST.encode("utf-8"), "text/html; charset=utf-8")
                else:
                    self._send(b'{"ok":false}', code=404)
            except Exception as exc:                      # noqa: BLE001
                # 没有兜底会返回 500 HTML，前端 r.json() 解析失败，
                # 界面停在旧状态且看不到任何错误。
                self._send(json.dumps({"ok": False, "error": str(exc)},
                                      ensure_ascii=False).encode("utf-8"),
                           code=500)

        def do_POST(self):
            seen["t"] = time.time()
            path = urlparse(self.path).path
            if path == "/shutdown":
                # 显式关闭：先把响应送出去，再让服务退出（否则响应到不了浏览器）
                self._send(b'{"ok":true}')
                threading.Timer(0.3, srv.shutdown).start()
                return
            if path == "/redo":
                try:
                    with lock:
                        f = get_fig()
                        stack = stacks_for(f)
                        if not stack:
                            raise RuntimeError("没有可重做的改动")
                        op = stack.pop()
                        raw = edit.read_raw(f)
                        edit.write_raw(f, edit.redo_op(raw, op))
                        edit.append_op(f, op)
                    self._send(json.dumps({"ok": True, "op": op},
                                          ensure_ascii=False).encode("utf-8"))
                except Exception as exc:                 # noqa: BLE001
                    self._send(json.dumps({"ok": False, "error": str(exc)},
                                          ensure_ascii=False).encode("utf-8"))
                return
            if path == "/order":
                n = int(self.headers.get("Content-Length", 0))
                try:
                    req = json.loads(self.rfile.read(n) or b"{}")
                    with lock:
                        f = get_fig()
                        op = edit.set_order(f, req["id"], req["mode"])
                        stacks_for(f).clear()
                    self._send(json.dumps({"ok": True, "eid": op.get("eid_after")},
                                          ensure_ascii=False).encode("utf-8"))
                except Exception as exc:                 # noqa: BLE001
                    self._send(json.dumps({"ok": False, "error": str(exc)},
                                          ensure_ascii=False).encode("utf-8"))
                return
            if path == "/undo":
                try:
                    with lock:
                        f = get_fig()
                        op = edit.undo_last(f)
                        if op:
                            stacks_for(f).append(op)
                    self._send(json.dumps({"ok": True, "op": op},
                                          ensure_ascii=False).encode("utf-8"))
                except Exception as exc:                 # noqa: BLE001
                    self._send(json.dumps({"ok": False, "error": str(exc)},
                                          ensure_ascii=False).encode("utf-8"))
                return
            if path == "/set_text":
                n = int(self.headers.get("Content-Length", 0))
                try:
                    req = json.loads(self.rfile.read(n) or b"{}")
                    with lock:
                        f = get_fig()
                        # 返回实际命中的元素：编号是位置序号，图层动过就会漂移，
                        # 调用方（尤其 agent 脚本）得能一眼看出改的是不是那一行。
                        found = edit.describe(edit.read_raw(f), req["id"])
                        op = edit.set_text(f, req["id"], str(req.get("text") or ""),
                                           expect=req.get("expect"))
                        stacks_for(f).clear()
                    self._send(json.dumps({"ok": True, "op": op, "found": found},
                                          ensure_ascii=False).encode("utf-8"))
                except Exception as exc:                 # noqa: BLE001
                    self._send(json.dumps({"ok": False, "error": str(exc)},
                                          ensure_ascii=False).encode("utf-8"))
                return
            if path == "/set":
                n = int(self.headers.get("Content-Length", 0))
                try:
                    req = json.loads(self.rfile.read(n) or b"{}")
                    with lock:
                        f = get_fig()
                        attrs = req.get("attrs") or {req["attr"]: req["value"]}
                        found = edit.describe(edit.read_raw(f), req["id"])
                        edit.set_values(f, req["id"], attrs, expect=req.get("expect"))
                        stacks_for(f).clear()
                    self._send(json.dumps({"ok": True, "found": found},
                                          ensure_ascii=False).encode("utf-8"))
                except Exception as exc:                 # noqa: BLE001
                    self._send(json.dumps({"ok": False, "error": str(exc)},
                                          ensure_ascii=False).encode("utf-8"))
                return
            if path != "/apply":
                self._send(b'{"ok":false}', code=404)
                return
            n = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
                with lock:
                    f = get_fig()
                    if req.get("moves"):
                        # 整体移动（多选拖动）：一条 move_multi op，撤销整体回退
                        edit.move_multi(f, req["moves"], note=req.get("note", ""))
                    else:
                        edit.move(f, req["id"], float(req["dx"]), float(req["dy"]),
                                  note=req.get("note", ""), expect=req.get("expect"))
                    stacks_for(f).clear()
                self._send(b'{"ok":true}')
            except Exception as exc:                     # noqa: BLE001
                self._send(json.dumps({"ok": False, "error": str(exc)},
                                      ensure_ascii=False).encode("utf-8"))

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}/"
    print(f"layoutfix tune → {url}")
    print(f"  文件: {fig}")
    print(f"  清单: {edit.log_path(fig)}")
    if idle_minutes > 0:
        print(f"  空闲 {idle_minutes:g} 分钟自动关闭（页面开着就不会关）")
    print("  Ctrl+C 结束")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    if idle_minutes > 0:
        def _watchdog():
            while True:
                time.sleep(5)
                if time.time() - seen["t"] > idle_minutes * 60:
                    print(f"\n[layoutfix] 空闲 {idle_minutes:g} 分钟无人访问，服务自动关闭")
                    srv.shutdown()
                    return
        threading.Thread(target=_watchdog, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        srv.server_close()
