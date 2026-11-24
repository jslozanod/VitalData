// Captura de la interfaz de Airflow (local) con la corrida completa del flujo diario.
const { spawn } = require('child_process'); const fs = require('fs'); const path = require('path');
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'; const PORT = 9335;
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
const env = Object.fromEntries(fs.readFileSync(path.join(__dirname, '..', '..', '.env'), 'utf-8').split(/\r?\n/).filter((l) => l.includes('=') && !l.startsWith('#')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]));
(async () => {
  const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${path.join(process.env.TEMP, 'vd-edge-perfil3')}`, '--window-size=1500,900', 'about:blank'], { stdio: 'ignore' });
  let lista; for (let i = 0; i < 40; i++) { try { lista = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); if (lista.length) break; } catch (e) {} await dormir(500); }
  const ws = new WebSocket(lista.find((t) => t.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const m = new Map(); ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && m.has(d.id)) { m.get(d.id)(d); m.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r) => { const n = ++id; m.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const js = async (x) => (await cdp('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result.result.value;
  await cdp('Page.enable'); await cdp('Emulation.setDeviceMetricsOverride', { width: 1500, height: 900, deviceScaleFactor: 1.5, mobile: false });
  await cdp('Page.navigate', { url: 'http://localhost:8080/login/' }); await dormir(3000);
  await js(`document.querySelector('input[name=username]').focus(); 1`); await cdp('Input.insertText', { text: 'admin' });
  await js(`document.querySelector('input[name=password]').focus(); 1`); await cdp('Input.insertText', { text: env.AIRFLOW_ADMIN_PASSWORD.replace(/^["']|["']$/g, '') });
  await js(`document.querySelector('input[type=submit],button[type=submit],.btn-primary').click(); 1`);
  await dormir(4000); console.log('tras login:', await js('location.href'), (await js(`(document.querySelector('.alert')||{}).innerText||''`)));
  await cdp('Page.navigate', { url: 'http://localhost:8080/dags/vitaldata_diario/grid?tab=graph&dag_run_id=scheduled__2026-11-22T05%3A00%3A00%2B00%3A00' }); await dormir(6000);
  const r = await cdp('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(path.join(__dirname, '..', 'evidencias', 'capturas', 'airflow-grafo.png'), Buffer.from(r.result.data, 'base64'));
  console.log('airflow-grafo.png', await js('document.title'));
  ws.close(); edge.kill(); process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
