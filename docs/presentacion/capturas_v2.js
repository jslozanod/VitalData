// Capturas del sitio para pacientes y del panel para hospitales (Edge sin ventana).
const { spawn } = require('child_process'); const fs = require('fs'); const path = require('path');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'; const PORT = 9337;
const OUT = path.join(__dirname, 'img'); const BASE = process.argv[2] || 'http://localhost:8000/';
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${path.join(process.env.TEMP, 'vd-edge-v2')}`, '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
  let lista; for (let i = 0; i < 40; i++) { try { lista = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); if (lista.length) break; } catch (e) {} await dormir(500); }
  const ws = new WebSocket(lista.find((t) => t.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const m = new Map(); ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && m.has(d.id)) { m.get(d.id)(d); m.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; m.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const js = async (x) => (await cdp('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result.result.value;
  const vista = (w, h, movil = false) => cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 2, mobile: movil });
  const ir = async (u) => { await cdp('Page.navigate', { url: BASE + u }); await dormir(3500); await js(`document.querySelectorAll('.revelar').forEach(n=>n.classList.add('vis'));document.querySelectorAll('.guia').forEach(g=>g.hidden=true);1`); await dormir(900); };
  const clip = async (sel, nombre, margen = 0) => {
    const r = JSON.parse(await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});e.scrollIntoView({block:'start'});const b=e.getBoundingClientRect();return JSON.stringify({x:b.x+scrollX,y:b.y+scrollY,w:b.width,h:b.height})})()`));
    await dormir(400);
    const s = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: Math.max(0, r.x - margen), y: Math.max(0, r.y - margen), width: r.w + 2 * margen, height: r.h + 2 * margen, scale: 1 } });
    fs.writeFileSync(path.join(OUT, nombre), Buffer.from(s.result.data, 'base64')); console.log('guardada', nombre, Math.round(r.w), Math.round(r.h));
  };
  const enviar = async (t) => { await js(`(async()=>{const e=document.getElementById('chat-in');e.value=${JSON.stringify(t)};document.getElementById('chat-form').requestSubmit();await new Promise(r=>setTimeout(r,1800));return 1})()`); };
  const clic = (txt) => js(`(async()=>{const b=[...document.querySelectorAll('#msgs .quick button')].find(x=>x.textContent==${JSON.stringify(txt)});b&&b.click();await new Promise(r=>setTimeout(r,500));return 1})()`);
  const fijar = () => js(`(async()=>{document.querySelector('#p-dias button[data-d="5"]').click();const s=document.getElementById('p-hora-sel');s.value='10';s.dispatchEvent(new Event('change'));await new Promise(r=>setTimeout(r,900));return 1})()`);

  await cdp('Page.enable');
  await vista(1440, 900);
  await ir('');
  await fijar();
  await enviar('tengo fiebre y dolor de garganta');
  await clic('Qué puedo tomar');
  const cam = await cdp('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(OUT, 'sitio_inicio.png'), Buffer.from(cam.result.data, 'base64')); console.log('guardada sitio_inicio.png');
  await clip('.portada-chat .phone', 'chat_fiebre.png', 14);
  await clic('Nueva consulta');
  await enviar('me duele el pecho');
  await clip('.portada-chat .phone', 'chat_alarma.png', 14);
  await clip('#donde-ir', 'sitio_donde.png');
  // panel para hospitales
  await ir('panel.html#demo');
  await js(`(async()=>{const s=(id,v)=>{const e=document.getElementById(id);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));};s('d-dot',4);await new Promise(r=>setTimeout(r,1500));return 1})()`);
  await vista(1440, 1500);
  await dormir(600);
  await clip('#demo .panel', 'panel_tablero.png');
  // movil
  await vista(390, 844, true);
  await ir('');
  await dormir(600);
  const mv = await cdp('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(OUT, 'sitio_movil.png'), Buffer.from(mv.result.data, 'base64')); console.log('guardada sitio_movil.png');
  ws.close(); edge.kill(); process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
