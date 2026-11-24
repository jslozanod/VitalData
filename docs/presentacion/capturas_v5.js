const { spawn } = require('child_process'); const fs = require('fs'); const path = require('path');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'; const PORT = 9340; const OUT = path.join(__dirname, 'img');
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${path.join(process.env.TEMP, 'vd-edge-v5')}`, '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
  let lista; for (let i = 0; i < 40; i++) { try { lista = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); if (lista.length) break; } catch (e) {} await dormir(500); }
  const ws = new WebSocket(lista.find((t) => t.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const m = new Map(); ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && m.has(d.id)) { m.get(d.id)(d); m.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; m.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const js = async (x) => (await cdp('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result.result.value;
  await cdp('Page.enable'); await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await cdp('Page.navigate', { url: 'http://localhost:8000/' }); await dormir(5500);
  await js(`document.querySelector('header.sitio').style.position='static';1`);
  for (const [sel, n, esc] of [['#hospitales .hosp-doble', 'hosp_doble.png', 1.3], ['#hosp-cifras', 'hosp_cifras.png', 1.3]]) {
    const r = JSON.parse(await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});const b=e.getBoundingClientRect();return JSON.stringify({x:b.x+scrollX,y:b.y+scrollY,w:b.width,h:b.height})})()`));
    const s = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: r.w, height: r.h, scale: esc } });
    fs.writeFileSync(path.join(OUT, n), Buffer.from(s.result.data, 'base64')); console.log(n, Math.round(r.w), Math.round(r.h));
  }
  ws.close(); edge.kill(); process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
