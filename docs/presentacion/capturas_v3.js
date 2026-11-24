// Capturas de las secciones del sitio para revisarlas.
const { spawn } = require('child_process'); const fs = require('fs'); const path = require('path');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'; const PORT = 9338;
const OUT = path.join(__dirname, 'img'); const BASE = 'http://localhost:8000/';
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${path.join(process.env.TEMP, 'vd-edge-v3')}`, '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
  let lista; for (let i = 0; i < 40; i++) { try { lista = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); if (lista.length) break; } catch (e) {} await dormir(500); }
  const ws = new WebSocket(lista.find((t) => t.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const m = new Map(); ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && m.has(d.id)) { m.get(d.id)(d); m.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; m.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const js = async (x) => (await cdp('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result.result.value;
  await cdp('Page.enable'); await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await cdp('Page.navigate', { url: BASE }); await dormir(5000);
  await js(`document.querySelector('header.sitio').style.position='static';1`);
  await js(`(async()=>{const d=[...document.querySelectorAll('#cal-dias .cal-dia:not([disabled])')];d[4].click();await new Promise(r=>setTimeout(r,1200));document.querySelectorAll('#r-franjas .hora:not([disabled])')[3].click();await new Promise(r=>setTimeout(r,300));document.getElementById('verif-lista').querySelectorAll('input')[0].click();document.querySelector('#auxilios details').open=true;1})()`);
  for (const [sel, nombre] of [['#donde-ir', 'v_donde.png'], ['#reservar', 'v_reservar.png'], ['#urgente', 'v_urgente.png'], ['#preguntas', 'v_preguntas.png'], ['#opiniones', 'v_opiniones.png']]) {
    const r = JSON.parse(await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});const b=e.getBoundingClientRect();return JSON.stringify({x:0,y:b.y+scrollY,w:innerWidth,h:b.height})})()`));
    const s = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: r.y, width: r.w, height: r.h, scale: 0.6 } });
    fs.writeFileSync(path.join(OUT, nombre), Buffer.from(s.result.data, 'base64')); console.log(nombre, Math.round(r.h));
  }
  const rr = JSON.parse(await js(`(()=>{const e=document.querySelector('#reservar .reserva');const b=e.getBoundingClientRect();return JSON.stringify({x:b.x+scrollX,y:b.y+scrollY,w:b.width,h:b.height})})()`));
  const ss = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: rr.x, y: rr.y, width: rr.w, height: rr.h, scale: 1.4 } });
  fs.writeFileSync(path.join(OUT, 'reserva.png'), Buffer.from(ss.result.data, 'base64')); console.log('reserva.png');
  ws.close(); edge.kill(); process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
