/* Logica de la pagina. Todo lo que se muestra sale de la API o del archivo exportado de la misma base. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const { fmt, C } = Charts;
  const pct = (v, d = 1) => fmt(v * 100, d) + ' %';
  const pad = (n) => String(n).padStart(2, '0');
  const NOMBRE = (s) => s.toLowerCase().replace(/(^|\s)\S/g, (m) => m.toUpperCase()).replace(/\bCs\b/, 'CS');
  const COLORES = { vitaldata: C.coral, vitaldata_sin_clima: C.gold, b_media_4s: '#7C8790', b_semana_anterior: '#A9B2B9', b_nivel: '#CBD2D7' };
  const NOMBRES_M = { vitaldata: 'VitalData', vitaldata_sin_clima: 'VitalData sin clima', b_media_4s: 'Media de 4 semanas', b_semana_anterior: 'Misma hora, semana anterior', b_nivel: 'Nivel de la última semana' };
  const est = { resumen: null, ips: [], metricas: [], calidad: null, modelables: [] };

  async function seguro(fn, host, msg) {
    try { return await fn(); } catch (e) { if (host) host.innerHTML = `<p class="sub">${msg || 'No se pudo cargar'}: ${e.message}</p>`; console.warn(e); return null; }
  }

  /* ------------------------------------------------------------------ arranque */
  async function main() {
    const modo = await Api.init();
    const b = $('#modo');
    b.textContent = modo === 'live' ? 'API en vivo' : 'Datos exportados';
    b.className = 'modo ' + (modo === 'live' ? 'live' : 'static');
    b.title = modo === 'live' ? 'La página está consultando la API y PostgreSQL en este momento' : 'La API no está en marcha: la página usa los datos exportados de la misma base (el escenario con clima necesita la API)';

    [est.resumen, est.ips, est.metricas, est.calidad] = await Promise.all([Api.resumen(), Api.ips(), Api.metricas(), Api.calidad()]);
    est.modelables = (est.ips || []).filter((i) => i.modelable && i.rango_pronostico);
    efectosDeScroll();
    const si = (sel, fn) => { if ($(sel)) fn(); };
    tema();
    guias();
    vistas();
    cifras(); si('#hist', problema); si('#flujo-datos', datos); si('#sel-ips-serie', serieHistorica); si('#curva', hallazgo);
    si('#d-chart', coordinador); si('#msgs', paciente); si('#modelo', modelo); si('#arq', arquitectura); si('#calidad', calidad);
    si('#finanzas', finanzas); si('#u-form', usuarios); si('#repo-link', equipo);
  }

  /* Boton para cambiar entre modo oscuro y claro (se recuerda en el navegador). */
  function tema() {
    const barra = $('header.top .wrap'); if (!barra) return;
    const actual = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
    const b = document.createElement('button'); b.type = 'button'; b.className = 'tema';
    b.textContent = actual === 'dark' ? '☀ Modo claro' : '☾ Modo oscuro';
    b.setAttribute('aria-label', actual === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    b.onclick = () => { try { localStorage.setItem('vd_tema', actual === 'dark' ? 'light' : 'dark'); } catch (e) { /* sin almacenamiento */ } location.reload(); };
    barra.appendChild(b);
  }

  /* Guia corta de cada pantalla: se muestra la primera vez y el boton Ayuda la vuelve a mostrar. */
  function guias() {
    const gs = $$('.guia'); if (!gs.length) return;
    const leer = (k) => { try { return localStorage.getItem('vd_guia_' + k) === '1'; } catch (e) { return false; } };
    const guardar = (k, v) => { try { if (v) localStorage.setItem('vd_guia_' + k, '1'); else localStorage.removeItem('vd_guia_' + k); } catch (e) { /* sin almacenamiento */ } };
    gs.forEach((g) => { g.hidden = leer(g.dataset.guia); $('.guia-x', g).onclick = () => { g.hidden = true; guardar(g.dataset.guia, true); }; });
    const barra = $('header.top .wrap'), modo = $('#modo');
    const b = document.createElement('button'); b.type = 'button'; b.className = 'ayuda'; b.textContent = '? Ayuda'; b.setAttribute('aria-label', 'Mostrar la guía de uso de esta pantalla');
    b.onclick = () => { gs.forEach((g) => { g.hidden = false; guardar(g.dataset.guia, false); }); const v = $('.vista:not([hidden]) .guia'); if (v) v.scrollIntoView({ behavior: 'smooth', block: 'center' }); };
    barra.insertBefore(b, modo);
  }

  /* Vistas de la aplicacion: una a la vez, segun la direccion (#demo, #paciente, #analisis). */
  function vistas() {
    const tabs = $$('nav.tabs a'); if (!tabs.length) return;
    const ids = tabs.map((a) => a.getAttribute('href').slice(1));
    const mostrar = () => {
      const id = ids.includes(location.hash.slice(1)) ? location.hash.slice(1) : ids[0];
      $$('.vista').forEach((s) => { s.hidden = s.id !== id; });
      tabs.forEach((a) => { const on = a.getAttribute('href') === '#' + id; a.classList.toggle('on', on); if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
      $$('.vista:not([hidden]) .revelar').forEach((n) => n.classList.add('vis'));
    };
    window.addEventListener('hashchange', () => { mostrar(); window.scrollTo(0, 0); });
    mostrar();
  }

  function efectosDeScroll() {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('vis'); io.unobserve(e.target); } }), { threshold: 0.12 });
    $$('.revelar').forEach((n) => io.observe(n));
    const links = $$('nav.menu:not(.tabs) a');
    const sec = links.map((a) => $(a.getAttribute('href')));
    const spy = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) links.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)); }), { rootMargin: '-45% 0px -50% 0px' });
    sec.forEach((s) => s && spy.observe(s));
  }

  /* ------------------------------------------------------------------ cifras del inicio */
  function contar(nodo, hasta, dec = 0) {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { nodo.textContent = fmt(hasta, dec); return; }
    const t0 = performance.now();
    const paso = (t) => { const k = Math.min(1, (t - t0) / 1100); nodo.textContent = fmt(hasta * (1 - Math.pow(1 - k, 3)), dec); if (k < 1) requestAnimationFrame(paso); };
    requestAnimationFrame(paso);
  }
  function cifras() {
    const r = est.resumen; if (!r) return;
    const m = { atenciones: r.atenciones, ips: r.ips, mediana: r.espera_mediana_min, p90: r.espera_p90_min };
    $$('#cifras b').forEach((n) => contar(n, m[n.dataset.k], n.dataset.k === 'mediana' || n.dataset.k === 'p90' ? 0 : 0));
  }

  /* ------------------------------------------------------------------ 1. problema */
  async function problema() {
    const r = est.resumen; if (!r) return;
    Charts.histograma($('#hist'), { bins: r.histograma_espera.filter((x) => x.desde < 360), marca: 120 });
    const tot = r.histograma_espera.reduce((a, x) => a + x.n, 0), mas2h = r.histograma_espera.filter((x) => x.desde >= 120).reduce((a, x) => a + x.n, 0);
    $('#hist-nota').textContent = `La mitad espera menos de ${fmt(r.espera_mediana_min, 0)} minutos, pero ${pct(mas2h / tot, 0)} espera más de dos horas.`;
    criterios();
  }

  function precisionPromedio(nivel) {
    const v = est.metricas.map((m) => m.metricas.metricas[nivel].vitaldata.precision);
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  }
  async function criterios() {
    const [pr, bm, af, us] = await Promise.all([Api.evidencias('pruebas'), Api.evidencias('benchmark'), Api.evidencias('airflow'), Api.usabilidad()]);
    const L = [];
    const gana = est.metricas.filter((m) => { const t = m.metricas.metricas['3h']; return t.vitaldata.wape < Math.min(t.b_media_4s.wape, t.b_semana_anterior.wape, t.b_nivel.wape); }).length;
    const claras = est.metricas.filter((m) => m.metricas.vs_referencia_3h && m.metricas.vs_referencia_3h.ic95[0] > 0).length;
    L.push([gana >= 2 ? 'ok' : 'no', `El pronóstico le gana a la mejor referencia sin IA en ${gana} de ${est.metricas.length} centros (franja de 3 horas); la mejora es estadísticamente clara en ${claras}.`]);
    const p3 = precisionPromedio('3h'), pd = precisionPromedio('dia');
    if (p3 != null) L.push([p3 >= 0.85 ? 'ok' : 'no', `Meta del proyecto: precisión de 85 % por franja de 3 horas. Resultado real: ${pct(p3)} por franja y ${pct(pd)} por día. En estos centros pequeños la meta no se cumple por franja; sí se acerca por día.`]);
    const c = est.calidad && est.calidad.conciliacion;
    if (c) L.push([c.coincide ? 'ok' : 'no', `La carga concilia: ${fmt(c.extraidas, 0)} extraídas − ${fmt(c.menos_duplicados, 0)} duplicadas − ${fmt(c.menos_rechazadas, 0)} rechazadas = ${fmt(c.esperado_en_base, 0)} en la base.`]);
    L.push(pr ? [pr.failed === 0 ? 'ok' : 'no', `Las ${pr.total} pruebas automáticas pasan (${pr.passed} pasaron, ${pr.failed} fallaron).`] : ['wait', 'Las pruebas automáticas pasan (se ejecutan con pytest).']);
    if (pr && pr.cobertura != null) L.push([pr.cobertura >= 80 ? 'ok' : 'no', `Cobertura del código de ${fmt(pr.cobertura, 0)} % (meta: 80 %).`]);
    if (bm) L.push([bm.p95_ms < 1000 ? 'ok' : 'no', `La API responde en menos de 1 s: mediana ${fmt(bm.mediana_ms, 0)} ms, percentil 95 de ${fmt(bm.p95_ms, 0)} ms.`]);
    if (af) L.push([af.estado === 'success' ? 'ok' : 'no', `El flujo diario corre completo en Airflow (${af.tareas.length} tareas, estado: ${af.estado}).`]);
    if (us && us.sesiones >= 5) L.push([us.sus_media >= 68 ? 'ok' : 'no', `Usabilidad: SUS de ${fmt(us.sus_media, 1)} con ${us.sesiones} personas (meta: 68 o más).`]);
    if (!$('#criterios')) return;
    $('#criterios').innerHTML = L.map(([s, t]) => `<li><span class="ic ${s}" aria-hidden="true">${s === 'ok' ? '✓' : s === 'no' ? '✗' : '…'}</span><div>${t} <span class="sr">${s === 'ok' ? 'Cumple' : s === 'no' ? 'No cumple' : 'Pendiente'}</span></div></li>`).join('');
  }

  /* ------------------------------------------------------------------ 2. datos */
  function selectorIps(host, activo, cb) {
    host.innerHTML = est.modelables.map((i) => `<button type="button" data-ips="${i.nombre}" aria-pressed="${i.nombre === activo}">${NOMBRE(i.nombre)}</button>`).join('');
    host.onclick = (e) => { const b = e.target.closest('button'); if (!b) return; $$('button', host).forEach((x) => x.setAttribute('aria-pressed', x === b)); cb(b.dataset.ips); };
  }
  async function datos() {
    D.flujoDatos($('#flujo-datos'), $('#flujo-det'), est.resumen, est.calidad);
    const q = est.calidad;
    if (q && q.corrida) {
      const c = q.conciliacion;
      $('#concilia').innerHTML = `<div class="kpis" style="grid-template-columns:repeat(2,1fr)"><div class="kpi"><div class="l">Bajaron de la API</div><div class="v">${fmt(c.extraidas, 0)}</div></div>
        <div class="kpi"><div class="l">Quedaron en la base</div><div class="v c">${fmt(q.filas_en_base, 0)}</div><div class="s">${c.coincide ? '✓ coincide con lo esperado' : '✗ no coincide'}</div></div></div>
        <p class="nota">${fmt(c.extraidas, 0)} − ${fmt(c.menos_duplicados, 0)} duplicadas − ${fmt(c.menos_rechazadas, 0)} rechazadas = ${fmt(c.esperado_en_base, 0)}.</p>`;
      $('#tabla-reglas tbody').innerHTML = q.reglas.map((r) => `<tr><td><code>${r.regla}</code><br><span class="pill ${r.severidad === 'error' ? 'no' : r.severidad === 'aviso' ? 'wait' : ''}">${r.severidad}</span></td><td>${fmt(r.filas, 0)}</td><td>${r.accion}</td></tr>`).join('');
    }
  }
  function serieHistorica() {
    const cambiar = async (ips) => {
      const s = await Api.serieDia(ips); if (!s) return;
      const inicio = new Date(s[0].t.slice(0, 10)), fin = new Date(s[s.length - 1].t.slice(0, 10));
      const dias = []; const m = new Map(s.map((x) => [x.t.slice(0, 10), x.llegadas]));
      for (let d = new Date(inicio); d <= fin; d.setDate(d.getDate() + 1)) dias.push(d.toISOString().slice(0, 10));
      const valores = dias.map((d) => (m.has(d) ? m.get(d) : null));
      const iMay = dias.indexOf('2022-05-01'), iAbr = dias.indexOf('2020-04-01');
      Charts.lineChart($('#serie'), { labels: dias.map((d) => d.slice(0, 7)), series: [{ name: 'Llegadas por día', color: C.coral, values: valores, width: 2 }], xEvery: Math.floor(dias.length / 8), height: 300, tipTitle: (i) => dias[i], tipDec: 0, aria: 'Llegadas por día', marks: [iAbr >= 0 ? { i: iAbr, text: 'sin registros hasta mar. 2021' } : null, iMay >= 0 ? { i: iMay, text: 'salto de mayo de 2022' } : null].filter(Boolean) });
    };
    selectorIps($('#sel-ips-serie'), est.modelables[0] && est.modelables[0].nombre, cambiar);
    if (est.modelables[0]) cambiar(est.modelables[0].nombre);
  }

  /* ------------------------------------------------------------------ 3. hallazgo */
  async function hallazgo() {
    const cambiar = async (ips) => {
      const r = await Api.esperaReal(ips); if (!r) return;
      Charts.curvaEspera($('#curva'), { curva: r.curva });
      const cor = r.correlacion, a = r.curva[0], z = r.curva[r.curva.length - 1];
      $('#curva-nota').textContent = `Correlación de Spearman entre llegadas y espera: ${cor.spearman} sobre ${fmt(cor.n_horas, 0)} horas. Prueba de permutación: p = ${cor.p_permutacion} (la probabilidad de ver algo así por azar).`;
      $('#curva-lectura').innerHTML = `En <b>${NOMBRE(ips)}</b>, las horas con ${a.llegadas_en_la_hora} llegada tienen una espera media de <b>${fmt(a.espera_media_min, 0)} min</b>; con ${z.llegadas_en_la_hora}, de <b>${fmt(z.espera_media_min, 0)} min</b>.`;
    };
    selectorIps($('#sel-ips-espera'), est.modelables[0] && est.modelables[0].nombre, cambiar);
    if (est.modelables[0]) cambiar(est.modelables[0].nombre);
    const t = est.resumen.por_triage;
    $('#triage-esp').innerHTML = `<div class="scroll" style="margin-top:14px"><table class="t"><thead><tr><th>Triage</th><th>Atenciones</th><th>Espera mediana</th></tr></thead><tbody>${t.map((x) => `<tr><td>${x.nivel}</td><td>${fmt(x.atenciones, 0)}</td><td>${fmt(x.espera_mediana_min, 0)} min</td></tr>`).join('')}</tbody></table></div>`;
  }

  /* ------------------------------------------------------------------ 4. coordinador */
  const demo = { ips: null, dias: [], idx: 0, esc: { lluvia: null, temp: null, nivel: 100 }, timer: null, req: 0 };
  function coordinador() {
    const sel = $('#d-ips');
    sel.innerHTML = est.modelables.map((i) => `<option value="${i.nombre}">${NOMBRE(i.nombre)}</option>`).join('');
    const poner = () => {
      demo.ips = sel.value;
      const r = est.modelables.find((i) => i.nombre === demo.ips).rango_pronostico;
      demo.dias = []; for (let d = new Date(r.desde); d <= new Date(r.hasta); d.setDate(d.getDate() + 1)) demo.dias.push(d.toISOString().slice(0, 10));
      const sl = $('#d-fecha'); sl.max = demo.dias.length - 1; sl.value = Math.min(demo.idx, demo.dias.length - 1) || 12; demo.idx = +sl.value;
      cargarDia();
    };
    sel.onchange = poner;
    const salidas = { 'd-fecha': () => { demo.idx = +$('#d-fecha').value; }, 'd-serv': null, 'd-meta': null, 'd-dot': null };
    ['d-fecha', 'd-serv', 'd-meta', 'd-dot'].forEach((id) => $('#' + id).addEventListener('input', () => { if (salidas[id]) salidas[id](); cargarDia(); }));
    [['d-lluvia', 'lluvia'], ['d-temp', 'temp'], ['d-nivel', 'nivel']].forEach(([id, k]) => $('#' + id).addEventListener('input', (e) => { demo.esc[k] = +e.target.value; cargarDia(); }));
    const bt = document.createElement('button'); bt.type = 'button'; bt.className = 'btn small ghost'; bt.style.marginTop = '12px'; bt.textContent = 'Restablecer escenario';
    bt.onclick = () => { demo.esc = { lluvia: null, temp: null, nivel: 100 }; $('#d-nivel').value = 100; cargarDia(); };
    $('#d-esc-ayuda').after(bt);
    if (Api.mode !== 'live') { $$('#d-lluvia,#d-temp,#d-nivel').forEach((n) => (n.disabled = true)); $('#d-esc-ayuda').textContent = 'El escenario con clima y demanda usa el modelo del servidor. Levanta el sistema con docker compose up y esta opción se activa.'; bt.hidden = true; }
    $('#d-play').onclick = () => {
      if (demo.timer) { clearInterval(demo.timer); demo.timer = null; $('#d-play').textContent = '▶ Recorrer los días'; return; }
      $('#d-play').textContent = '⏸ Detener';
      demo.timer = setInterval(() => { demo.idx = (demo.idx + 1) % demo.dias.length; $('#d-fecha').value = demo.idx; cargarDia(); }, 1400);
    };
    const csv = $('#d-csv'), imp = $('#d-print');
    if (csv) csv.onclick = () => {
      const u = demo.ultimo; if (!u) return;
      const f = (v) => (v == null ? '' : String(v).replace('.', ','));
      const filas = [['hora', 'pacientes_pronosticados', 'rango_bajo_80', 'rango_alto_80', 'pacientes_reales', 'personal_necesario', 'dotacion_actual', 'espera_con_dotacion_min', 'estado']];
      u.pr.forEach((h, i) => { const q = u.p.horas[i]; filas.push([pad(h.hora) + ':00', f(h.pronostico == null ? null : Math.round(h.pronostico * 10) / 10), f(h.lo80), f(h.hi80), f(h.real), q.personal_necesario, u.dot, q.saturada ? 'saturada' : f(q.espera_con_dotacion_min), q.saturada ? 'saturada' : q.critica ? 'critica' : 'ok']); });
      const texto = '﻿' + filas.map((r) => r.join(';')).join('\r\n');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' }));
      a.download = `plan_${u.ips.toLowerCase().replace(/\s+/g, '_')}_${u.fecha}.csv`; document.body.appendChild(a); a.click(); a.remove();
    };
    if (imp) imp.onclick = () => window.print();
    $('#d-fecha').value = 12; demo.idx = 12; poner();
  }

  async function cargarDia() {
    const mi = ++demo.req;
    const fecha = demo.dias[demo.idx], serv = +$('#d-serv').value, meta = +$('#d-meta').value, dot = +$('#d-dot').value;
    const dtxt = new Date(fecha + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    $('#o-fecha').textContent = dtxt; $('#o-serv').textContent = serv + ' min'; $('#o-meta').textContent = '≤ ' + meta + ' min'; $('#o-dot').textContent = dot + ' personas';
    $('#o-lluvia').textContent = demo.esc.lluvia == null ? 'dato real' : demo.esc.lluvia + ' mm'; $('#o-temp').textContent = demo.esc.temp == null ? 'dato real' : demo.esc.temp + ' °C'; $('#o-nivel').textContent = demo.esc.nivel === 100 ? 'la real' : demo.esc.nivel + ' %';
    try {
      const [p, pe] = await Promise.all([Api.personalDia(demo.ips, fecha, serv, meta, dot).then((x) => x), Api.pronostico(demo.ips, fecha)]);
      if (mi !== demo.req) return;
      let esc = null;
      const hay = Api.mode === 'live' && (demo.esc.lluvia != null || demo.esc.temp != null || demo.esc.nivel !== 100);
      if (hay) esc = await Api.escenario({ ips: demo.ips, fecha, lluvia_mm: demo.esc.lluvia, temp_media: demo.esc.temp, factor_nivel: demo.esc.nivel / 100 }).catch(() => null);
      if (mi !== demo.req) return;
      const pr = pe.horas;
      demo.ultimo = { fecha, ips: demo.ips, serv, meta, dot, pr, p };
      const quien = $('#d-resumen');
      if (quien) {
        const hp = (h) => `${pad(h)}:00`;
        const horaPico = pr.map((h) => h.pronostico).indexOf(Math.max(...pr.map((h) => h.pronostico)));
        const estado = p.horas_criticas
          ? `Con <b>${dot} ${dot === 1 ? 'persona' : 'personas'}</b> hay <b>${p.horas_criticas} ${p.horas_criticas === 1 ? 'hora' : 'horas'}</b> en las que la espera se dispara. En el pico hacen falta <b>${p.pico_personal}</b>.`
          : `Con <b>${dot} ${dot === 1 ? 'persona' : 'personas'}</b> la espera se mantiene dentro de tu meta de ${meta} minutos. En el pico hacen falta <b>${p.pico_personal}</b>.`;
        quien.innerHTML = `<span class="ico" aria-hidden="true">i</span><div>Se esperan unos <b>${fmt(pe.total_pronosticado, 0)} pacientes</b>, con el pico a las <b>${hp(horaPico)}</b>. ${estado}</div>`;
      }
      const pico = (a) => a.indexOf(Math.max(...a));
      const picoP = pico(pr.map((h) => h.pronostico)), picoR = pico(pr.map((h) => h.real));
      const err = Math.abs(pe.total_pronosticado - pe.total_real) / pe.total_real;
      $('#d-kpis').innerHTML = kpi('Pacientes pronosticados', fmt(pe.total_pronosticado, 0), 'c', `llegaron ${fmt(pe.total_real, 0)} · error de ${pct(err, 0)}`) +
        kpi('Hora pico', `${pad(picoP)}:00`, '', `la real fue a las ${pad(picoR)}:00`) +
        kpi('Horas en rojo', p.horas_criticas + ' h', p.horas_criticas ? 'c' : '', `con ${dot} personas la espera pasa de ${Math.max(meta * 2, 30)} min o se satura`) +
        kpi('Personal en el pico', p.pico_personal, '', `faltan ${fmt(p.horas_persona_que_faltan, 0)} h-persona · sobran ${fmt(p.horas_persona_que_sobran, 0)}`);
      $('#d-sub').textContent = `${dtxt}. El pronóstico se hizo con lo que se sabía hasta las 00:00 de ese día.` + (esc ? ` Escenario: ${esc.cambio_pct >= 0 ? '+' : ''}${String(esc.cambio_pct).replace('.', ',')} % de pacientes.` : '');
      $('#lg-esc').hidden = !esc;
      const series = [
        { name: 'Referencia sin IA', color: C.mute, values: pr.map((h) => h.referencia), dash: '6 5', width: 2 },
        { name: 'Pronóstico', color: C.coral, values: pr.map((h) => h.pronostico), width: 3.5 },
        { name: 'Ocurrió', color: C.ink, values: pr.map((h) => h.real), width: 2, dots: true },
      ];
      if (esc) series.push({ name: 'Escenario', color: '#8A4FD4', values: esc.horas.map((h) => h.escenario), width: 3 });
      Charts.lineChart($('#d-chart'), { labels: pr.map((h) => pad(h.hora)), series, band: { lo: pr.map((h) => h.lo80), hi: pr.map((h) => h.hi80) }, yLabel: 'pacientes por hora', tipTitle: (i) => `${pad(i)}:00`, xEvery: 3, aria: 'Pronóstico de pacientes por hora' });
      $('#d-sub2').textContent = `Para que la espera media no pase de ${meta} minutos con ${serv} minutos por paciente. En rojo, las horas en que la dotación de ${dot} no alcanza.`;
      Charts.staffChart($('#d-staff'), { horas: p.horas, dotacion: dot });
    } catch (e) { $('#d-kpis').innerHTML = `<p class="sub">${e.message}</p>`; }
  }
  const kpi = (l, v, c, s) => `<div class="kpi"><div class="l">${l}</div><div class="v ${c}">${v}</div><div class="s">${s}</div></div>`;

  /* ------------------------------------------------------------------ 5. paciente */
  function paciente() {
    const msgs = $('#msgs');
    const bub = (cls, html) => { const d = document.createElement('div'); d.className = 'bub ' + cls; d.innerHTML = html; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return d; };
    const hora = $('#p-hora');
    const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    const hoy = (new Date().getDay() + 6) % 7;                                    // 0 = lunes
    const vivo = { dia: hoy, datos: null, cache: {} };
    hora.value = new Date().getHours();
    const tipoDe = (d) => (d === 6 ? 'domingo' : d === 5 ? 'sabado' : 'laboral');
    const pintarVivo = () => {
      const d = vivo.datos; if (!d) return;
      const h = +hora.value;
      const lista = d.centros.map((c) => ({ ips: c.ips, w: c.horas[h].espera_min, n: c.horas[h].atenciones })).filter((x) => x.w != null).sort((a, b) => a.w - b.w);
      $('#pv-titulo').textContent = `Si vas el ${DIAS[vivo.dia].toLowerCase()} a las ${pad(h)}:00`;
      const max = Math.max(...lista.map((x) => x.w), 1);
      $('#pv-barras').innerHTML = lista.map((x, i) => `<div class="pv-fila ${i === 0 ? 'mejor' : i === lista.length - 1 && lista.length > 1 ? 'peor' : ''}"><span class="nom">${NOMBRE(x.ips)}${i === 0 ? ' · la más corta' : ''}</span><span class="barra"><i style="width:${Math.max(4, (x.w / max) * 100)}%"></i></span><b>${fmt(x.w, 0)} min</b></div>`).join('') || '<p class="sub">No hay atenciones registradas a esa hora.</p>';
      $('#pv-resumen').textContent = lista.length > 1 ? `Ir a ${NOMBRE(lista[0].ips)} en lugar de ${NOMBRE(lista[lista.length - 1].ips)} te ahorra unos ${fmt(lista[lista.length - 1].w - lista[0].w, 0)} minutos.` : '';
      const pocos = lista.some((x) => x.n != null && x.n < 10);
      $('#pv-nota').textContent = `Promedio real de 2022 para ese día y esa hora.${pocos ? ' A esta hora hubo pocas atenciones: tómalo como una idea general.' : ''}${d.aproximado ? ' Sin la API se muestra el promedio entre semana, sábado o domingo.' : ''}`;
      const colores = [C.coral, C.blue, C.gold, C.ok];
      Charts.lineChart($('#pv-curva'), {
        labels: Array.from({ length: 24 }, (_, i) => pad(i)),
        series: d.centros.map((c, i) => ({ name: NOMBRE(c.ips), color: colores[i % colores.length], values: c.horas.map((x) => x.espera_min), width: 2.5 })),
        yLabel: 'minutos de espera', tipTitle: (i) => `${pad(i)}:00`, xEvery: 3, height: 230, tipDec: 0, aria: 'Espera de cada centro a lo largo del día',
        marks: [{ i: h, text: 'tu hora' }],
      });
    };
    const cargarVivo = async (dia) => {
      vivo.dia = dia;
      $$('#p-dias button').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.d === dia)));
      try {
        if (!vivo.cache[dia]) vivo.cache[dia] = await Api.esperaPorDia(dia);
        vivo.datos = vivo.cache[dia]; pintarVivo();
      } catch (e) { $('#pv-barras').innerHTML = `<p class="sub">No se pudo consultar: ${e.message}</p>`; }
    };
    $('#p-dias').innerHTML = DIAS.map((n, i) => `<button type="button" data-d="${i}" aria-pressed="${i === hoy}" title="${n}${i === hoy ? ' (hoy)' : ''}" class="${i === hoy ? 'hoy' : ''}">${n.slice(0, 3)}</button>`).join('');
    $('#p-dias').onclick = (e) => { const b = e.target.closest('button'); if (b) cargarVivo(+b.dataset.d); };
    const ver = () => { $('#o-phora').textContent = pad(+hora.value) + ':00'; pintarVivo(); };
    hora.oninput = ver; $('#o-phora').textContent = pad(+hora.value) + ':00';
    cargarVivo(hoy);
    const quick = (lista) => { const q = document.createElement('div'); q.className = 'quick'; lista.forEach((t) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = t; b.onclick = () => enviar(t); q.appendChild(b); }); msgs.appendChild(q); msgs.scrollTop = msgs.scrollHeight; };
    const bienvenida = () => { msgs.innerHTML = ''; bub('bot', 'Hola, soy el asistente de VitalData. Te cuento qué tan llenas están las urgencias cerca de ti. <b>¿Qué te pasa?</b>'); quick(['Tengo gripa y tos', 'Me duele el pecho', 'Dolor de estómago', 'Me torcí el tobillo']); };
    async function enviar(texto) {
      texto = texto.trim(); if (!texto) return;
      $$('.quick', msgs).forEach((q) => q.remove());
      bub('me', texto.replace(/</g, '&lt;'));
      try {
        const r = await Api.orientar(texto, +hora.value, tipoDe(vivo.dia), vivo.dia);
        bub(r.accion === 'urgencias_ya' ? 'bot alert' : 'bot', r.mensaje);
        if (r.ranking && r.ranking.length) {
          const mejor = r.ranking[0].espera_esperada_min;
          bub('rank', `<b>El ${DIAS[vivo.dia].toLowerCase()} a las ${pad(+hora.value)}:00 la espera esperada es:</b>` + r.ranking.map((x, i) => `<div class="row ${i === 0 ? 'best' : ''}"><span>${NOMBRE(x.ips)}${i === 0 ? ' · la más corta' : ''}</span><b>${fmt(x.espera_esperada_min, 0)} min</b></div>`).join('') + `<p class="nota" style="margin:6px 0 0">Promedio real de 2022. ${fmt(r.ranking[r.ranking.length - 1].espera_esperada_min - mejor, 0)} min de diferencia entre la más corta y la más larga.</p>`);
        }
      } catch (e) { bub('bot', 'No pude consultar: ' + e.message); }
      quick(['Empezar de nuevo']);
      $$('.quick button', msgs).forEach((b) => { if (b.textContent === 'Empezar de nuevo') b.onclick = bienvenida; });
    }
    $('#chat-form').onsubmit = (e) => { e.preventDefault(); const i = $('#chat-in'); enviar(i.value); i.value = ''; };
    bienvenida();
    const t = est.resumen.por_triage, tot = t.reduce((a, x) => a + x.atenciones, 0), leves = t.filter((x) => x.nivel === 'IV' || x.nivel === 'V'), iii = t.find((x) => x.nivel === 'III');
    const nl = leves.reduce((a, x) => a + x.atenciones, 0), ml = leves.reduce((a, x) => a + x.espera_mediana_min * x.atenciones, 0) / nl;
    $('#p-dato').innerHTML = `${pct(nl / tot, 0)} de las atenciones son urgencias menores (triage IV o V) y esperan una mediana de <b>${fmt(ml, 0)} minutos</b>, frente a <b>${fmt(iii.espera_mediana_min, 0)} minutos</b> en triage III. Orientarlas a una cita prioritaria o a una teleconsulta libera la sala para quienes más lo necesitan.`;
  }

  /* ------------------------------------------------------------------ 6. modelo */
  function modelo() {
    const niv = { hora: 'por hora', '3h': 'por franja de 3 horas', dia: 'por día' };
    let nivel = '3h';
    const dibujar = () => {
      const ms = est.metricas; if (!ms.length) return;
      const lista = ['b_nivel', 'b_semana_anterior', 'b_media_4s', 'vitaldata_sin_clima', 'vitaldata'];
      Charts.groupedBars($('#m-chart'), { groups: ms.map((m) => ({ label: NOMBRE(m.ips), bars: lista.map((k) => { const x = m.metricas.metricas[nivel][k]; const dif = nivel === '3h' ? m.metricas.vs_referencia_3h : nivel === 'dia' ? m.metricas.vs_referencia_dia : null; return { name: NOMBRES_M[k], value: x.precision, color: COLORES[k], note: k === 'vitaldata' && dif ? `Mejora frente a la mejor referencia: ${fmt(dif.mejora_media * 100, 1)} puntos (IC 95 %: ${fmt(dif.ic95[0] * 100, 1)} a ${fmt(dif.ic95[1] * 100, 1)})` : '' }; }) })), yMax: 1, line: nivel === '3h' ? { value: 0.85, label: 'Meta del proyecto: 85 %' } : null, aria: 'Precisión por modelo ' + niv[nivel] });
      $('#m-leg').innerHTML = lista.slice().reverse().map((k) => `<span><i style="background:${COLORES[k]};height:10px"></i>${NOMBRES_M[k]}</span>`).join('');
      const v = ms[0]; $('#m-ventana').textContent = `Periodo de prueba: ${v.test_desde.slice(0, 10)} a ${v.test_hasta.slice(0, 10)} · precisión = 1 − error porcentual absoluto ponderado`;
      const fila = (txt, cls) => `<p><span class="pill ${cls}">${txt[0]}</span> ${txt[1]}</p>`;
      $('#m-gana').innerHTML = ms.map((m) => { const d = nivel === 'dia' ? m.metricas.vs_referencia_dia : m.metricas.vs_referencia_3h; const nv = nivel === 'dia' ? 'dia' : '3h'; const ok = d.ic95[0] > 0; return fila([ok ? 'sí' : d.ic95[1] < 0 ? 'no' : 'empate', `<b>${NOMBRE(m.ips)}</b>: ${fmt(d.mejora_media * 100, 1)} puntos de mejora ${nv === 'dia' ? 'por día' : 'por franja'} (IC 95 %: ${fmt(d.ic95[0] * 100, 1)} a ${fmt(d.ic95[1] * 100, 1)}).`], ok ? 'ok' : d.ic95[1] < 0 ? 'no' : 'wait'); }).join('') + '<p class="nota">El intervalo se calcula remuestreando días completos 2.000 veces. Si incluye el cero, la mejora no es distinguible del azar.</p>';
      $('#m-clima').innerHTML = ms.map((m) => { const a = m.metricas.metricas[nivel].vitaldata.precision, b = m.metricas.metricas[nivel].vitaldata_sin_clima.precision; return `<p><b>${NOMBRE(m.ips)}</b>: ${(a - b) >= 0 ? '+' : ''}${fmt((a - b) * 100, 1)} puntos con lluvia y temperatura.</p>`; }).join('') + '<p class="nota">Usamos el clima observado ese día. En producción vendría de un pronóstico, así que la ganancia real sería menor.</p>';
      $('#m-cob').innerHTML = ms.map((m) => { const c = m.metricas.metricas.cobertura_80; return `<p><b>${NOMBRE(m.ips)}</b>: ${pct(c, 0)} de las horas cayeron dentro del rango.</p>`; }).join('') + '<p class="nota">Un rango del 80 % bien calibrado debería contener cerca de 80 % de los datos.</p>';
      const h = precisionPromedio('hora'), t3 = precisionPromedio('3h'), d1 = precisionPromedio('dia');
      $('#m-honesto').innerHTML = `<ul><li>Hora por hora, el modelo acierta en promedio <b>${pct(h, 0)}</b>: con dos o tres pacientes por hora, el azar pesa mucho y ningún modelo lo elimina.</li><li>Por franja de 3 horas llega a <b>${pct(t3, 0)}</b> y por día a <b>${pct(d1, 0)}</b>. La meta de 85 % por franja la definimos pensando en hospitales más grandes y aquí no se cumple.</li><li>La ganancia sobre la mejor referencia es real pero modesta. Lo que más aporta es adaptarse rápido al nivel de la última semana, que cambió de forma brusca en mayo de 2022.</li><li>Todo está calculado con datos de 2020 a 2022. Con un hospital cliente hay que repetir la validación.</li></ul>`;
    };
    $('#sel-nivel').onclick = (e) => { const b = e.target.closest('button'); if (!b) return; nivel = b.dataset.n; $$('#sel-nivel button').forEach((x) => x.setAttribute('aria-pressed', x === b)); dibujar(); };
    dibujar();
  }

  /* ------------------------------------------------------------------ 7. arquitectura */
  function arquitectura() { D.arquitectura($('#arq'), $('#arq-det')); D.er($('#er')); }

  /* ------------------------------------------------------------------ 8. calidad */
  async function calidad() {
    const [pr, af, co] = await Promise.all([Api.evidencias('pruebas'), Api.evidencias('airflow'), Api.evidencias('consultas')]);
    $('#ev-pruebas').innerHTML = pr ? `<div class="kpis" style="grid-template-columns:repeat(2,1fr)"><div class="kpi"><div class="l">Pasaron</div><div class="v c">${pr.passed}/${pr.total}</div></div><div class="kpi"><div class="l">Cobertura</div><div class="v">${fmt(pr.cobertura, 0)} %</div></div></div>
      <ul class="check">${pr.por_archivo.map((x) => `<li><span class="ic ${x.failed ? 'no' : 'ok'}">${x.failed ? '✗' : '✓'}</span><div><code>${x.archivo}</code><br><span class="nota">${x.passed} pruebas</span></div></li>`).join('')}</ul><p class="nota">Ejecutadas ${pr.fecha}. Unitarias, de integración con PostgreSQL real y de límites.</p>` : '<p class="sub">Sin evidencia exportada todavía.</p>';
    $('#ev-airflow').innerHTML = af ? `<p><span class="pill ${af.estado === 'success' ? 'ok' : 'no'}">${af.estado === 'success' ? 'corrida exitosa' : af.estado}</span> <span class="nota">${af.dag_id} · ${af.inicio}</span></p>
      <ul class="check">${af.tareas.map((t) => `<li><span class="ic ${t.estado === 'success' ? 'ok' : 'no'}">${t.estado === 'success' ? '✓' : '✗'}</span><div><code>${t.id}</code><br><span class="nota">${fmt(t.segundos, 1)} s</span></div></li>`).join('')}</ul>` : '<p class="sub">Sin evidencia exportada todavía.</p>';
    $('#ev-consultas').innerHTML = co ? co.consultas.map((c) => { const mx = Math.max(c.sin_indice_ms, c.con_indice_ms); return `<p><b>${c.nombre}</b><br><span class="nota">${c.descripcion}</span></p>
      <div style="display:grid;grid-template-columns:90px 1fr 70px;gap:6px;align-items:center;font-size:.85rem"><span>sin índice</span><div style="background:var(--panel);border-radius:6px"><div style="width:${c.sin_indice_ms / mx * 100}%;background:#9AA4AB;height:12px;border-radius:6px"></div></div><b>${fmt(c.sin_indice_ms, 1)} ms</b><span>con índice</span><div style="background:var(--panel);border-radius:6px"><div style="width:${c.con_indice_ms / mx * 100}%;background:var(--coral);height:12px;border-radius:6px"></div></div><b>${fmt(c.con_indice_ms, 1)} ms</b></div>`; }).join('<hr style="border:0;border-top:1px solid var(--hair);margin:14px 0">') : '<p class="sub">Sin evidencia exportada todavía.</p>';
    const runs = await Api.corridas();
    $('#tabla-corridas tbody').innerHTML = (runs || []).map((r) => `<tr><td>${r.etl_run_id}</td><td>${r.flujo}</td><td><span class="pill ${r.estado === 'ok' ? 'ok' : r.estado === 'error' ? 'no' : 'wait'}">${r.estado}</span></td><td>${r.filas_extraidas == null ? '–' : fmt(r.filas_extraidas, 0)}</td><td>${r.filas_cargadas == null ? '–' : fmt(r.filas_cargadas, 0)}</td><td>${(r.inicio || '').slice(0, 19)}</td></tr>`).join('');
    const imgs = [['assets/evidencias/airflow-grafo.png', 'El DAG en Airflow', 'Las siete tareas del flujo diario, en verde después de una corrida real.'], ['assets/evidencias/pytest.png', 'Pruebas', 'Salida real de pytest con la cobertura.'], ['assets/evidencias/api-docs.png', 'API interactiva', 'Los endpoints documentados automáticamente en /docs.']];
    $('#galeria-ev').innerHTML = imgs.map(([s, t, d]) => `<figure><img src="${s}" alt="${t}: ${d}" loading="lazy" onerror="this.closest('figure').remove()"><figcaption><b>${t}.</b> ${d}</figcaption></figure>`).join('');
  }

  /* ------------------------------------------------------------------ 9. finanzas */
  const PLANES = [
    { n: 'Esencial', p: 480000, s: 3750000, a: 9510000, v: 167504, d: 'IPS pequeña, una sede. Tablero con pronóstico y personal recomendado.' },
    { n: 'Completo', p: 780000, s: 7450000, a: 16810000, v: 270016, d: 'IPS mediana. Agrega el asistente del paciente por WhatsApp y el informe mensual.', hot: true },
    { n: 'Red', p: 2000000, s: 14900000, a: 38900000, v: 699306, d: 'Tres sedes y redirección de pacientes entre ellas.' },
  ];
  function finanzas() {
    const cop = (v) => '$' + fmt(v, 0);
    $('#planes').innerHTML = PLANES.map((p) => `<div class="card revelar vis" style="${p.hot ? 'border:2px solid var(--coral)' : ''}"><div class="pill ${p.hot ? 'no' : ''}">${p.hot ? 'Recomendado' : 'Plan'}</div><h3 style="margin-top:8px">${p.n}</h3><div class="v" style="font-family:var(--head);font-size:2.1rem;color:var(--coral-d)">${cop(p.p)}<span style="font-size:1rem;color:var(--gray)"> al mes</span></div><p class="sub">${p.d}</p><p class="nota">Implementación: ${cop(p.s)} · primer año: ${cop(p.a)} · costo variable: ${cop(p.v)} (margen 65 %, sin IVA)</p></div>`).join('');
    const ids = { 'f-precio': 'o-fprecio', 'f-var': 'o-fvar', 'f-fijo': 'o-ffijo', 'f-hrs': 'o-fhrs' };
    const calc = () => {
      const precio = +$('#f-precio').value, vr = +$('#f-var').value, fijo = +$('#f-fijo').value, hrs = +$('#f-hrs').value;
      $('#o-fprecio').textContent = cop(precio); $('#o-fvar').textContent = cop(vr); $('#o-ffijo').textContent = cop(fijo); $('#o-fhrs').textContent = hrs + ' h';
      const contrib = precio - vr, eq = contrib > 0 ? Math.ceil(fijo / contrib) : null, valor = hrs * 28277;
      $('#f-kpis').innerHTML = kpi('Clientes de equilibrio', eq == null ? '–' : eq, 'c', `contribución de ${cop(contrib)} por cliente`) + kpi('Valor para el hospital', cop(valor) , '', `${hrs} h evitadas × $28.277 por hora extra`) + kpi('Recupera el hospital', precio ? fmt(valor / precio, 2) + ' ×' : '–', valor >= precio ? '' : 'c', valor >= precio ? 'lo que paga' : 'menos de lo que paga') + kpi('Margen', precio ? pct(contrib / precio, 0) : '–', '', 'de cada peso cobrado');
      const n = 30; const lab = Array.from({ length: n + 1 }, (_, i) => String(i));
      Charts.lineChart($('#f-chart'), { labels: lab, series: [{ name: 'Resultado mensual (millones)', color: C.coral, values: lab.map((_, i) => (i * contrib - fijo) / 1e6), width: 3.5 }], yMax: Math.max(2, Math.ceil((n * contrib - fijo) / 1e6)), yFmt: (v) => fmt(v, 0), yLabel: 'millones de pesos al mes', tipTitle: (i) => `${i} clientes`, xEvery: 5, tipDec: 2, aria: 'Resultado mensual segun numero de clientes' });
    };
    Object.keys(ids).forEach((i) => $('#' + i).addEventListener('input', calc));
    calc();
  }

  /* ------------------------------------------------------------------ 10. usuarios */
  const SUS = ['Creo que me gustaría usar este sistema con frecuencia.', 'Encontré el sistema innecesariamente complejo.', 'Pensé que el sistema era fácil de usar.', 'Creo que necesitaría el apoyo de una persona técnica para usarlo.', 'Encontré que las funciones del sistema estaban bien integradas.', 'Pensé que había demasiada inconsistencia en el sistema.', 'Imagino que la mayoría de la gente aprendería a usarlo muy rápido.', 'Encontré el sistema muy incómodo de usar.', 'Me sentí muy seguro/a usando el sistema.', 'Necesité aprender muchas cosas antes de empezar a usarlo.'];
  let cron = null, t0 = 0, segundos = 0;
  function usuarios() {
    const proto = [['assets/proto/lofi.svg', 'Nivel 1 · Lo-Fi', 'Boceto a lápiz de la pantalla del coordinador. Respondía: ¿qué se muestra y dónde?'], ['assets/proto/mefi.svg', 'Nivel 2 · Me-Fi', 'Maqueta con jerarquía de color y datos de ejemplo. Respondía: ¿se entiende y se ve confiable?'], ['assets/proto/pf.png', 'Nivel 3 · Producto funcional', 'La aplicación funcionando, con la API, la base de datos y datos reales.']];
    $('#galeria-proto').innerHTML = proto.map(([s, t, d]) => `<figure><img src="${s}" alt="${t}. ${d}" loading="lazy" onerror="this.closest('figure').remove()"><figcaption><b>${t}.</b> ${d}</figcaption></figure>`).join('');
    $('#u-sus').innerHTML = SUS.map((q, i) => `<fieldset class="sus-q" style="border:0;padding:10px 0;margin:0"><legend style="font-size:.93rem;padding:0">${i + 1}. ${q}</legend><div class="opts">${[1, 2, 3, 4, 5].map((v) => `<label><input type="radio" name="sus${i}" value="${v}" required>${v}</label>`).join('')}<span class="nota" style="align-self:center;margin-left:8px">1 = muy en desacuerdo · 5 = muy de acuerdo</span></div></fieldset>`).join('');
    $('#u-cron').onclick = () => {
      if (cron) { clearInterval(cron); cron = null; $('#u-cron').textContent = '▶ Empezar a medir el tiempo'; return; }
      t0 = Date.now(); $('#u-cron').textContent = '⏸ Detener el cronómetro';
      cron = setInterval(() => { segundos = Math.round((Date.now() - t0) / 1000); $('#u-tiempo').textContent = `${Math.floor(segundos / 60)}:${pad(segundos % 60)}`; }, 500);
    };
    $('#u-form').onsubmit = async (e) => {
      e.preventDefault();
      const sus = SUS.map((_, i) => { const r = $(`input[name=sus${i}]:checked`); return r ? +r.value : null; });
      const ok = parseInt($('#u-ok').value, 10);
      const out = $('#u-res');
      if (sus.some((x) => x == null)) { out.textContent = 'Falta responder todas las preguntas.'; return; }
      if (isNaN(ok) || ok < 0 || ok > 5) { out.textContent = 'Las tareas logradas van de 0 a 5.'; return; }
      if (cron) { clearInterval(cron); cron = null; }
      try {
        const r = await Api.enviarUsabilidad({ rol: $('#u-rol').value, tareas_ok: ok, tareas_total: 5, segundos: Math.min(segundos, 7200), comentario: $('#u-com').value.trim() || null, sus });
        out.textContent = `Gracias. Su puntaje SUS fue ${fmt(r.sus_puntaje, 1)}.` + (r.local ? ' (guardado solo en este navegador)' : '');
        $('#u-form').reset(); resumenUsab();
      } catch (er) { out.textContent = 'No se pudo enviar: ' + er.message; }
    };
    resumenUsab();
  }
  async function resumenUsab() {
    let r = await Api.usabilidad();
    if (Api.mode !== 'live') {
      const l = JSON.parse(localStorage.getItem('vd_usab') || '[]');
      if (l.length) { const s = l.map((x) => Api.sus(x.sus)), m = s.reduce((a, b) => a + b, 0) / s.length; r = { sesiones: l.length, sus_media: Math.round(m * 10) / 10, sus_ic95: [m, m], tareas_completadas: l.reduce((a, x) => a + x.tareas_ok, 0) / l.reduce((a, x) => a + x.tareas_total, 0), segundos_mediana: l.map((x) => x.segundos).sort((a, b) => a - b)[Math.floor(l.length / 2)], local: true }; }
    }
    $('#u-resumen').innerHTML = !r || !r.sesiones ? '<p class="sub">Todavía no hay sesiones registradas. Quien haga la prueba aparecerá aquí, y las cifras se calculan con las respuestas reales. No inventamos resultados.</p>'
      : `<div class="kpis"><div class="kpi"><div class="l">Personas</div><div class="v">${r.sesiones}</div></div><div class="kpi"><div class="l">SUS promedio</div><div class="v c">${fmt(r.sus_media, 1)}</div><div class="s">${r.sesiones > 1 ? `IC 95 %: ${fmt(r.sus_ic95[0], 1)} a ${fmt(r.sus_ic95[1], 1)}` : 'con una sola persona no hay intervalo'}</div></div><div class="kpi"><div class="l">Tareas logradas</div><div class="v">${pct(r.tareas_completadas, 0)}</div></div><div class="kpi"><div class="l">Tiempo mediano</div><div class="v">${Math.floor(r.segundos_mediana / 60)}:${pad(Math.round(r.segundos_mediana % 60))}</div></div></div><p class="nota">Un puntaje SUS de 68 es el promedio de la industria y sobre 80 se considera muy bueno. ${r.sesiones < 5 ? 'Con menos de cinco personas, tómelo como una señal y no como una conclusión.' : ''}${r.local ? ' Estas cifras son de este navegador.' : ''}</p>`;
  }

  function equipo() { $('#repo-link').addEventListener('click', (e) => { if (e.target.getAttribute('href') === '#') e.preventDefault(); }); }

  main().catch((e) => { console.error(e); document.body.insertAdjacentHTML('afterbegin', `<p style="padding:20px;background:#FFE7E4">No se pudieron cargar los datos: ${e.message}</p>`); });
})();
