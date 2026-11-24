/* Diagramas interactivos en SVG: flujo de datos, arquitectura y modelo de datos. */
const D = (() => {
  const { el } = Charts;

  function caja(svg, n, tema, onSel) {
    const dark = tema === 'dark';
    const g = el('g', { class: 'nodo', tabindex: 0, role: 'button', 'aria-label': n.t + '. ' + (n.s || '') });
    g.appendChild(el('rect', { x: n.x, y: n.y, width: n.w, height: n.h, rx: 12, fill: n.fill || (dark ? '#2A343B' : '#fff'), stroke: dark ? '#46535C' : '#D8CFBF', 'stroke-width': 2 }));
    g.appendChild(el('text', { x: n.x + n.w / 2, y: n.y + (n.s ? n.h / 2 - 3 : n.h / 2 + 5), 'text-anchor': 'middle', 'font-size': n.fs || 14, 'font-weight': 700, fill: n.color || (dark ? '#fff' : '#22282D'), 'font-family': 'Segoe UI,sans-serif' }, [n.t]));
    if (n.s) g.appendChild(el('text', { x: n.x + n.w / 2, y: n.y + n.h / 2 + 15, 'text-anchor': 'middle', 'font-size': 11.5, fill: n.color2 || (dark ? '#B9C1C7' : '#5E6770'), 'font-family': 'Segoe UI,sans-serif' }, [n.s]));
    const go = () => onSel(n, g);
    g.addEventListener('click', go);
    g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    svg.appendChild(g);
    return g;
  }
  function flecha(svg, a, b, tema, label) {
    const col = tema === 'dark' ? '#6C7A84' : '#9AA4AB';
    const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2;
    svg.appendChild(el('path', { d: `M${x1} ${y1} C ${x1 + 28} ${y1}, ${x2 - 28} ${y2}, ${x2 - 4} ${y2}`, fill: 'none', stroke: col, 'stroke-width': 2.2, 'marker-end': 'url(#fl-' + tema + ')' }));
    if (label) svg.appendChild(el('text', { x: (x1 + x2) / 2, y: (y1 + y2) / 2 - 8, 'text-anchor': 'middle', 'font-size': 11, fill: col }, [label]));
  }
  function defs(svg) {
    ['dark', 'light'].forEach((t) => svg.appendChild(el('defs', {}, [el('marker', { id: 'fl-' + t, markerWidth: 9, markerHeight: 9, refX: 7, refY: 4.5, orient: 'auto' }, [el('path', { d: 'M0 0 L9 4.5 L0 9 z', fill: t === 'dark' ? '#6C7A84' : '#9AA4AB' })])])));
  }
  function montar(host, det, svg, nodos, tema, render) {
    defs(svg);
    const grupos = {};
    const sel = (n, g) => { Object.values(grupos).forEach((x) => x.classList.remove('sel')); g.classList.add('sel'); det.innerHTML = render(n); };
    nodos.forEach((n) => { grupos[n.id] = caja(svg, n, tema, sel); });
    host.innerHTML = '';
    host.appendChild(svg);
    sel(nodos[0], grupos[nodos[0].id]);
  }
  const fmt = (v) => Charts.fmt(v, 0);

  function flujoDatos(host, det, resumen, calidad) {
    const svg = el('svg', { viewBox: '0 0 700 250', role: 'group', 'aria-label': 'Flujo de datos' });
    const c = calidad && calidad.corrida ? calidad.corrida : {};
    const nodos = [
      { id: 'a', x: 8, y: 20, w: 120, h: 62, t: 'Pasto Salud', s: 'triage de urgencias', fill: '#E1EBFB', color: '#22282D', color2: '#3A4249' },
      { id: 'b', x: 8, y: 150, w: 120, h: 62, t: 'IDEAM', s: 'lluvia y temperatura', fill: '#E1EBFB', color: '#22282D', color2: '#3A4249' },
      { id: 'c', x: 175, y: 84, w: 120, h: 62, t: 'ETL', s: 'validar y limpiar', fill: '#FFE7E4', color: '#22282D', color2: '#3A4249' },
      { id: 'd', x: 340, y: 84, w: 120, h: 62, t: 'PostgreSQL', s: 'modelo en estrella', fill: '#DDF3E8', color: '#22282D', color2: '#3A4249' },
      { id: 'e', x: 505, y: 20, w: 130, h: 62, t: 'Modelo', s: 'pronóstico por hora', fill: '#FFF3D4', color: '#22282D', color2: '#3A4249' },
      { id: 'f', x: 505, y: 150, w: 130, h: 62, t: 'API y página', s: 'FastAPI + web', fill: '#EDE4F9', color: '#22282D', color2: '#3A4249' },
    ];
    const ar = [['a', 'c', ''], ['b', 'c', ''], ['c', 'd', ''], ['d', 'e', ''], ['e', 'f', ''], ['d', 'f', '']];
    defs(svg);
    const by = Object.fromEntries(nodos.map((n) => [n.id, n]));
    ar.forEach(([a, b]) => flecha(svg, by[a], by[b], 'light'));
    const info = {
      a: `<b>Fuente 1: atenciones de urgencias.</b><br>datos.gov.co, conjunto <code>vt5n-eu2r</code>, E.S.E. Pasto Salud (Nariño). Cada fila trae ingreso, atención, triage e IPS.<br><b>${fmt(c.filas_extraidas || 0)}</b> filas leídas en la última carga, de enero de 2020 a septiembre de 2022.<br><span class="nota">Código: <code>src/vitaldata/etl/extract.py</code> (reintentos y token por variable de entorno).</span>`,
      b: `<b>Fuente 2: clima.</b><br>IDEAM, estación Universidad de Nariño (Pasto). Se agrega por día en el servidor, un mes por petición, para no bajar millones de lecturas.<br>Lluvia (<code>s54a-sgyg</code>) y temperatura (<code>sbwg-7ju4</code>). Un día con pocas lecturas queda vacío en vez de inventar un valor.<br><span class="nota">Código: <code>etl/extract.py</code> y <code>etl/pipeline.py</code>.</span>`,
      c: `<b>Validar y limpiar.</b><br>Quita <b>${fmt(c.filas_duplicadas || 0)}</b> filas duplicadas exactas, corrige <b>${fmt(c.filas_corregidas || 0)}</b> esperas negativas por redondeo y rechaza lo imposible. Nada se borra en silencio: cada regla deja su conteo.<br><span class="nota">Código: <code>etl/validate.py</code>, con 8 pruebas unitarias.</span>`,
      d: `<b>PostgreSQL.</b><br><b>${fmt(c.filas_cargadas || 0)}</b> atenciones en la tabla de hechos. La carga es idempotente: una huella md5 por fila impide duplicar si se corre dos veces. Restricciones en la base: la atención no puede ser anterior al ingreso, la espera no pasa de 24 h, el triage existe.<br><span class="nota">Código: <code>src/vitaldata/db/schema.sql</code>.</span>`,
      e: `<b>Modelo.</b><br>Regresión de Poisson por hora con perfil por tipo de día, clima y nivel de la última semana. Se reentrena cada semana y se evalúa con ventana que avanza.<br><span class="nota">Código: <code>models/forecast.py</code> y <code>models/backtest.py</code>.</span>`,
      f: `<b>API y página.</b><br>FastAPI con validación de cada parámetro; esta página la consume. Si la API no está, la página lee un archivo exportado de la misma base.<br><span class="nota">Código: <code>api/main.py</code> y <code>web/</code>.</span>`,
    };
    montar(host, det, svg, nodos, 'light', (n) => info[n.id]);
  }

  function arquitectura(host, det) {
    const svg = el('svg', { viewBox: '0 0 960 430', role: 'group', 'aria-label': 'Arquitectura del sistema' });
    svg.appendChild(el('rect', { x: 4, y: 4, width: 952, height: 422, rx: 18, fill: 'none', stroke: '#46535C', 'stroke-dasharray': '8 6' }));
    svg.appendChild(el('text', { x: 20, y: 28, 'font-size': 12.5, fill: '#8FA0AB', 'font-weight': 700 }, ['docker compose']));
    const N = [
      { id: 'fuentes', x: 24, y: 160, w: 150, h: 76, t: 'datos.gov.co', s: 'Pasto Salud · IDEAM', fill: '#27425F' },
      { id: 'airflow', x: 220, y: 54, w: 170, h: 76, t: 'Airflow', s: 'DAG diario · 7 tareas', fill: '#4A3A63' },
      { id: 'etl', x: 220, y: 160, w: 170, h: 76, t: 'ETL', s: 'extraer · validar · cargar', fill: '#5B3A3A' },
      { id: 'pytest', x: 220, y: 290, w: 170, h: 76, t: 'pytest', s: 'unitarias · integración', fill: '#35523F' },
      { id: 'db', x: 440, y: 160, w: 170, h: 76, t: 'PostgreSQL 16', s: 'esquema vd', fill: '#1F5A44' },
      { id: 'modelos', x: 440, y: 54, w: 170, h: 76, t: 'Modelos', s: 'Poisson · backtest', fill: '#6B5521' },
      { id: 'api', x: 660, y: 160, w: 120, h: 76, t: 'FastAPI', s: '14 endpoints', fill: '#4A3A63' },
      { id: 'web', x: 810, y: 160, w: 130, h: 76, t: 'Página web', s: 'JS sin librerías', fill: '#5B3A3A' },
      { id: 'snap', x: 660, y: 290, w: 280, h: 62, t: 'snapshot.js', s: 'modo sin servidor', fill: '#2A343B' },
    ];
    const by = Object.fromEntries(N.map((n) => [n.id, n]));
    [['fuentes', 'etl'], ['airflow', 'etl'], ['etl', 'db'], ['modelos', 'db'], ['db', 'api'], ['api', 'web']].forEach(([a, b]) => flecha(svg, by[a], by[b], 'dark'));
    flecha(svg, by.db, { x: 660, y: 290, w: 0, h: 62 }, 'dark');
    const info = {
      fuentes: 'Dos fuentes abiertas. Se leen por la API de Socrata con reintentos y espera creciente entre intentos. El token opcional va en una variable de entorno y nunca en el código ni en el registro.',
      airflow: 'Orquesta el flujo diario: <code>verificar_fuente → [cargar_triage, cargar_clima] → controles_de_calidad → entrenar_y_publicar → compuerta_del_modelo → exportar_snapshot</code>. Cada tarea reintenta dos veces y la compuerta detiene la publicación si el modelo pierde contra la referencia. <span class="nota">Código: <code>airflow/dags/vitaldata_diario.py</code>.</span>',
      etl: 'Funciones pequeñas y probadas: <code>extract</code>, <code>validate</code>, <code>load</code> y <code>pipeline</code>. Cada corrida se registra en <code>etl_run</code> y cada regla de calidad en <code>dq_issue</code>, aunque falle.',
      pytest: 'Pruebas unitarias (reglas de limpieza, cola de espera, modelo, extracción con servidor simulado) y de integración contra PostgreSQL real y contra la API. Incluyen casos límite: archivos vacíos, 24 horas exactas, parámetros fuera de rango.',
      db: 'Esquema en estrella: <code>fact_atencion</code> con dimensiones <code>dim_ips</code> y <code>dim_triage</code>, el agregado por hora que consume el modelo, el clima, los modelos publicados y las pruebas de usabilidad. Con índices medidos con EXPLAIN ANALYZE.',
      modelos: 'Un modelo por centro de salud. Se comparan con tres referencias sin IA y se publican con sus métricas y su intervalo. El modelo final se guarda en disco para los escenarios.',
      api: 'Todos los parámetros tienen límites (dotación de 1 a 60, meta de 1 a 120 minutos, texto de 1 a 400 caracteres). Los errores devuelven 404 o 422 con un mensaje claro y un fallo de base devuelve 503. Documentación en <code>/docs</code>.',
      web: 'Una sola página, sin librerías externas, con gráficas en SVG y navegación por teclado. Consume la API y, si no está, usa los datos exportados.',
      snap: 'Archivo generado por el último paso del DAG con los mismos datos que sirve la API. Permite abrir la página directamente desde el disco o publicarla como página estática.',
    };
    montar(host, det, svg, N, 'dark', (n) => `<b style="color:#fff">${n.t}</b><br>${info[n.id]}`);
  }

  function er(host) {
    const svg = el('svg', { viewBox: '0 0 760 430', role: 'img', 'aria-label': 'Diagrama entidad-relación' });
    const T = [
      { n: 'dim_ips', x: 20, y: 30, f: ['ips_id PK', 'nombre', 'red'] },
      { n: 'dim_triage', x: 20, y: 170, f: ['triage_id PK', 'nivel I a V'] },
      { n: 'fact_atencion', x: 250, y: 90, w: 200, f: ['atencion_id PK', 'ips_id FK', 'triage_id FK', 'ingreso · atencion', 'espera_min', 'huella UNIQUE'], hot: true },
      { n: 'agg_llegadas_hora', x: 520, y: 30, w: 210, f: ['ips_id FK · hora PK', 'llegadas', 'espera_media · p90'] },
      { n: 'clima_diario', x: 520, y: 160, w: 210, f: ['estacion_id FK · fecha PK', 'lluvia_mm', 'temp_media'] },
      { n: 'model_run', x: 250, y: 290, w: 200, f: ['model_run_id PK', 'ips_id FK', 'metricas JSONB', 'vigente'] },
      { n: 'forecast_hora', x: 520, y: 290, w: 210, f: ['model_run_id FK', 'hora · modelo', 'prediccion · lo80 · hi80 · real'] },
      { n: 'etl_run / dq_issue', x: 20, y: 290, w: 200, f: ['etl_run_id PK', 'estado · filas_*', 'regla · severidad'] },
    ];
    const by = Object.fromEntries(T.map((t) => [t.n, { ...t, w: t.w || 170, h: 28 + t.f.length * 20 }]));
    const link = (a, b) => { const A = by[a], B = by[b]; svg.appendChild(el('line', { x1: A.x + A.w / 2, y1: A.y + A.h / 2, x2: B.x + B.w / 2, y2: B.y + B.h / 2, stroke: '#6C7A84', 'stroke-width': 2, 'stroke-dasharray': '5 4' })); };
    [['dim_ips', 'fact_atencion'], ['dim_triage', 'fact_atencion'], ['fact_atencion', 'agg_llegadas_hora'], ['fact_atencion', 'model_run'], ['model_run', 'forecast_hora'], ['etl_run / dq_issue', 'fact_atencion'], ['clima_diario', 'agg_llegadas_hora']].forEach(([a, b]) => link(a, b));
    Object.values(by).forEach((t) => {
      svg.appendChild(el('rect', { x: t.x, y: t.y, width: t.w, height: t.h, rx: 10, fill: t.hot ? '#3A2A2A' : '#2A343B', stroke: t.hot ? '#FF4438' : '#46535C', 'stroke-width': 2 }));
      svg.appendChild(el('text', { x: t.x + 12, y: t.y + 20, 'font-size': 13.5, 'font-weight': 700, fill: '#fff' }, [t.n]));
      t.f.forEach((f, i) => svg.appendChild(el('text', { x: t.x + 12, y: t.y + 42 + i * 20, 'font-size': 12, fill: '#B9C1C7', 'font-family': 'Consolas,monospace' }, [f])));
    });
    host.innerHTML = '';
    host.appendChild(svg);
  }
  return { flujoDatos, arquitectura, er };
})();
window.D = D;
