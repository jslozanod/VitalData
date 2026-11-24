/* Capa de acceso a datos. Si la API esta en marcha (docker compose up) la usa; si no, lee los datos exportados
de la misma base (data/snapshot.js) y calcula en el navegador lo que no necesita el modelo. */
const Api = (() => {
  let mode = 'static';
  const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  const S = () => window.SNAPSHOT || {};

  async function http(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) { const e = new Error(((await r.json().catch(() => ({}))).detalle) || r.statusText); e.status = r.status; throw e; }
    return r.json();
  }
  const q = (o) => '?' + Object.entries(o).filter(([, v]) => v != null && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

  async function init() {
    if (location.protocol === 'file:') return mode;
    try { const c = new AbortController(); setTimeout(() => c.abort(), 2500); const r = await fetch('/api/health', { signal: c.signal }); if (r.ok) mode = 'live'; } catch (e) { /* sin servidor */ }
    return mode;
  }

  /* ---------- Erlang C y reglas del asistente, iguales a las de Python (pruebas en tests/) ---------- */
  function erlangC(c, a) { if (a === 0) return 0; if (a >= c) return 1; let t = 1, s = 1; for (let k = 1; k < c; k++) { t *= a / k; s += t; } t *= a / c; const cola = t * c / (c - a); return cola / (s + cola); }
  function espera(lam, c, serv) { if (lam <= 0) return 0; const mu = 60 / serv, a = lam / mu; if (a >= c) return Infinity; return erlangC(c, a) / (c * mu - lam) * 60; }
  function personal(lam, serv, meta) { if (lam <= 0) return 1; const mu = 60 / serv; let c = Math.max(1, Math.floor(lam / mu) + 1); while (c <= 80) { if (espera(lam, c, serv) <= meta) return c; c++; } return 80; }
  const norm = (t) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const ALARMA = ['dolor (de|en el) pecho', 'no (puedo|logro) respirar', 'me cuesta respirar', 'ahog', 'desmay', 'convuls', 'sangrado (abundante|que no para)', 'vomit\\w* sangre', 'paralis', 'cara (torcida|caida)', 'perdi (el )?conocimiento', 'inconsciente', 'herida profunda', 'envenen', 'intoxic', '(dolor|presion) (fuerte|intenso) en el pecho'];
  const LEVE = ['\\bgripa\\b', '\\bgripe\\b', 'resfri', 'tos\\b', 'dolor de garganta', 'estornud', 'congestion', 'fiebre leve', 'malestar', 'dolor muscular', 'picadura', 'dolor de oido', 'conjuntivitis'];
  function clasificar(texto) { const t = norm(texto); if (t.trim().length < 3) return 'sin_informacion'; if (ALARMA.some((p) => new RegExp(p).test(t))) return 'alarma'; return LEVE.some((p) => new RegExp(p).test(t)) ? 'leve' : 'indeterminado'; }

  const api = {
    get mode() { return mode; }, init, slug, clasificar, personalNecesario: personal, esperaMedia: espera,

    async resumen() { return mode === 'live' ? http('/api/resumen') : S().resumen; },
    async ips() { return mode === 'live' ? http('/api/ips') : S().ips; },
    async metricas(ips) { if (mode === 'live') return http('/api/metricas' + q({ ips })); const m = S().metricas || []; return ips ? m.filter((x) => x.ips === ips) : m; },
    async calidad() { return mode === 'live' ? http('/api/calidad') : S().calidad; },
    async corridas() { return mode === 'live' ? http('/api/etl/corridas?limite=30') : S().corridas; },
    async usabilidad() { if (mode === 'live') return http('/api/usabilidad/resumen'); return S().usabilidad_resumen || { sesiones: 0 }; },
    async perfil(ips) { return mode === 'live' ? http('/api/perfil' + q({ ips })) : S()['perfil_' + slug(ips)]; },
    async esperaReal(ips) { return mode === 'live' ? http('/api/espera-real' + q({ ips })) : S()['espera_real_' + slug(ips)]; },
    async serieDia(ips) { return mode === 'live' ? http('/api/serie' + q({ ips, nivel: 'dia' })) : S()['serie_dia_' + slug(ips)]; },
    async evidencias(nombre) { return S()['ev_' + nombre] || null; },

    async pronostico(ips, fecha) {
      if (mode === 'live') return http('/api/pronostico' + q({ ips, fecha }));
      const d = (S()['pronostico_' + slug(ips)] || {})[fecha];
      if (!d) { const e = new Error('No hay pronostico para esa fecha'); e.status = 404; throw e; }
      return { ips, fecha, total_pronosticado: d.tp, total_real: d.tr, horas: d.h.map((x, h) => ({ hora: h, pronostico: x[0], lo80: x[1], hi80: x[2], real: x[3], referencia: x[4] })) };
    },

    async personalDia(ips, fecha, serv, meta, dot) {
      if (mode === 'live') return http('/api/personal' + q({ ips, fecha, servicio_min: serv, meta_min: meta, dotacion: dot }));
      const p = await api.pronostico(ips, fecha);
      let faltan = 0, sobran = 0, crit = 0;
      const horas = p.horas.map((h) => {
        const lam = h.pronostico || 0, req = personal(lam, serv, meta), w = espera(lam, dot, serv);
        faltan += Math.max(0, req - dot); sobran += Math.max(0, dot - req);
        const critica = !isFinite(w) || w > Math.max(meta * 2, 30); crit += critica ? 1 : 0;
        return { hora: h.hora, llegadas_esperadas: lam, personal_necesario: req, espera_con_dotacion_min: isFinite(w) ? Math.round(w * 10) / 10 : null, saturada: !isFinite(w), critica };
      });
      return { ips, fecha, total_pronosticado: p.total_pronosticado, total_real: p.total_real, parametros: { servicio_min: serv, meta_min: meta, dotacion: dot }, horas, horas_persona_que_faltan: faltan, horas_persona_que_sobran: sobran, horas_criticas: crit, pico_personal: Math.max(...horas.map((x) => x.personal_necesario)) };
    },

    async escenario(body) {
      if (mode !== 'live') { const e = new Error('El escenario con clima y demanda usa el modelo en el servidor. Levanta el sistema con docker compose up.'); e.status = 501; throw e; }
      return http('/api/escenario', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    },

    async esperaPorDia(dia) {
      if (mode === 'live') return http('/api/espera-tipica?dia_semana=' + dia);
      const tipo = dia === 6 ? 'domingo' : dia === 5 ? 'sabado' : 'laboral';   // sin la API solo se conoce el tipo de dia
      const t = S().espera_tipica || {};
      return { dia_semana: dia, aproximado: true, centros: Object.entries(t).map(([ips, v]) => ({ ips, horas: v[tipo].map((w, h) => ({ hora: h, espera_min: w, atenciones: null })) })) };
    },

    async orientar(texto, hora, tipo, dia, contexto) {
      if (mode === 'live') return http('/api/orientar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto, hora, tipo_dia: tipo, dia_semana: dia, contexto: contexto || null }) });
      const nivel = clasificar(texto), tri = S().espera_triage || {}, tipica = S().espera_tipica || {};
      const ranking = Object.entries(tipica).map(([ips, t]) => ({ ips, espera_esperada_min: t[tipo][hora] })).filter((x) => x.espera_esperada_min != null).sort((a, b) => a.espera_esperada_min - b.espera_esperada_min);
      let accion, mensaje, mostrar = true;
      if (nivel === 'alarma') { accion = 'urgencias_ya'; mostrar = false; mensaje = 'Por lo que cuentas, no esperes ni compares clinicas: llama al 123 o ve de inmediato a la urgencia mas cercana.'; }
      else if (nivel === 'sin_informacion') { accion = 'pedir_mas_datos'; mostrar = false; mensaje = 'Cuentame un poco mas: que sientes y desde cuando.'; }
      else if (nivel === 'leve') { accion = 'orientacion_leve'; mensaje = `Lo que describes parece leve. Antes de ir a urgencias puedes pedir una cita prioritaria o una teleconsulta. En los datos reales, quienes llegan con una urgencia menor (triage IV o V) esperan en promedio ${tri['IV-V']} minutos, frente a ${tri['III']} minutos en triage III. Si empeoras o aparece algun sintoma de alarma, ve a urgencias.`; }
      else { accion = 'orientacion_general'; mensaje = 'No puedo valorar eso por aqui. Si te preocupa, consulta; esta es la urgencia con menos espera esperada ahora. Si hay dificultad para respirar, dolor fuerte en el pecho o perdida de conocimiento, llama al 123.'; }
      return { clasificacion: { nivel }, accion, mensaje, ranking: mostrar ? ranking : [], aviso: 'Prototipo academico: no reemplaza una valoracion medica. Emergencias: 123.' };
    },

    async enviarUsabilidad(body) {
      if (mode === 'live') return http('/api/usabilidad', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const lista = JSON.parse(localStorage.getItem('vd_usab') || '[]'); lista.push(body); localStorage.setItem('vd_usab', JSON.stringify(lista));
      return { sus_puntaje: api.sus(body.sus), local: true };
    },
    sus(r) { return r.reduce((a, v, i) => a + (i % 2 === 0 ? v - 1 : 5 - v), 0) * 2.5; },
  };
  return api;
})();
window.Api = Api;
