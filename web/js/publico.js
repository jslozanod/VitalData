/* Sitio para pacientes: asistente, a donde ir, reserva de citas, verificador de urgencias, preguntas y opiniones.
   Todo viene de la API; sin ella solo funciona la orientacion basica con la copia exportada. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const pad = (n) => String(n).padStart(2, '0');
  const fmt = (v) => Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  const NOMBRE = (s) => s.toLowerCase().replace(/(^|\s)\S/g, (m) => m.toUpperCase()).replace(/\bCs\b/, 'CS');
  const esc = (t) => String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const TEMAS = ['Tengo fiebre', 'Gripa o tos', 'Dolor de cabeza', 'Dolor de estómago', 'Me torcí el tobillo', 'Tengo una alergia', 'Dolor de garganta', 'Quiero pedir una cita'];
  const hoy = (new Date().getDay() + 6) % 7; // 0 = lunes
  const estado = { dia: hoy, hora: new Date().getHours(), datos: null, cache: {}, guia: null, ips: [], esp: 'Medicina general' };
  const tipoDe = (d) => (d === 6 ? 'domingo' : d === 5 ? 'sabado' : 'laboral');
  const hora12 = (h, m = 0) => `${h % 12 || 12}:${pad(m)} ${h < 12 ? 'a. m.' : 'p. m.'}`;
  const franjaDe = (h) => (h < 6 ? 'Madrugada' : h < 12 ? 'Mañana' : h < 18 ? 'Tarde' : 'Noche');
  const fechaLarga = (iso) => { const [a, m, d] = iso.split('-').map(Number); const f = new Date(a, m - 1, d); return `${DIAS[(f.getDay() + 6) % 7]} ${d} de ${MESES[m - 1]}`; };

  async function http(url, opciones) {
    const r = await fetch(url, opciones);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      let m = j.detalle;
      if (!m && Array.isArray(j.detail) && j.detail.length) m = j.detail.map((d) => String(d.msg).replace(/^Value error, /, '')).join('. ');
      const e = new Error(m || 'No se pudo completar la solicitud'); e.status = r.status; throw e;
    }
    return j;
  }
  const enJson = (cuerpo) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) });

  /* ------------------------------------------------------------------ tema claro / oscuro */
  function tema() {
    const b = $('#btn-tema'); if (!b) return;
    const poner = () => { b.textContent = document.documentElement.dataset.theme === 'dark' ? 'Modo claro' : 'Modo oscuro'; };
    b.onclick = () => {
      const nuevo = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = nuevo;
      try { localStorage.setItem('vd_tema', nuevo); } catch (e) { /* sin almacenamiento */ }
      poner();
    };
    poner();
  }

  /* ------------------------------------------------------------------ chat */
  const msgs = $('#msgs');
  const burbuja = (cls, html) => { const d = document.createElement('div'); d.className = 'bub ' + cls; d.innerHTML = html; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return d; };
  const lista = (items) => '<ul>' + items.map((x) => `<li>${esc(x)}</li>`).join('') + '</ul>';
  const quitarChips = () => $$('.quick', msgs).forEach((q) => q.remove());
  const chips = (etiquetas) => {
    quitarChips();
    if (!etiquetas.length) return;
    const q = document.createElement('div'); q.className = 'quick';
    etiquetas.forEach((t) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = t; b.onclick = () => accion(t); q.appendChild(b); });
    msgs.appendChild(q); msgs.scrollTop = msgs.scrollHeight;
  };
  const guiaChips = () => ['Qué hacer en casa', 'Qué puedo tomar', 'Cuándo consultar', 'Señales de alarma', 'Reservar cita', 'Nueva consulta'];
  const EXPLORA = ['Para qué sirve el acetaminofén', '¿Qué es el triage?', '¿Qué debo llevar a mi cita?', 'Mis derechos en urgencias', '¿Cuál es la hora con más gente?', '¿Qué tan preciso es el pronóstico?', '¿Cuándo ir a urgencias o a cita prioritaria?', 'Quiero un chequeo preventivo'];

  function bienvenida() {
    msgs.innerHTML = '';
    burbuja('bot', 'Hola, soy el asistente de VitalData. Cuéntame qué sientes y te digo qué puedes hacer en casa, qué se suele tomar y a qué centro te conviene ir. <b>¿Qué te pasa?</b>');
    estado.guia = null;
    chips(TEMAS.concat(['Más preguntas']));
  }

  function irAReservar(especialidad) {
    if (especialidad) { const s = $('#r-esp'); if ([...s.options].some((o) => o.value === especialidad)) { s.value = especialidad; estado.esp = especialidad; } }
    $('#reservar').scrollIntoView({ behavior: 'smooth' });
  }

  function accion(etiqueta) {
    const g = estado.guia;
    const mostrar = (cls, html) => { quitarChips(); burbuja('me', esc(etiqueta)); burbuja(cls, html); chips(guiaChips()); };
    if (etiqueta === 'Nueva consulta') return bienvenida();
    if (etiqueta === 'Más preguntas') { quitarChips(); burbuja('bot', 'También puedo ayudarte con medicamentos, trámites y datos reales del sistema. Elige una opción o escribe tu pregunta:'); return chips(EXPLORA.concat(['Nueva consulta'])); }
    if (etiqueta === 'Reservar cita') { burbuja('me', 'Reservar cita'); burbuja('bot', `Te llevo al calendario${g ? ` con la especialidad sugerida: <b>${esc(g.especialidad)}</b>` : ''}.`); irAReservar(g && g.especialidad); return; }
    if (g && etiqueta === 'Qué hacer en casa') return mostrar('bot lista', `<span class="t">Qué hacer en casa</span>${lista(g.casa)}`);
    if (g && etiqueta === 'Qué puedo tomar') return mostrar('bot lista', `<span class="t">Qué se suele tomar</span>${lista(g.medicamentos)}<span class="pie-b">${esc(g.aviso_medicamentos)}</span>`);
    if (g && etiqueta === 'Cuándo consultar') return mostrar('bot lista', `<span class="t">Pide una cita o consulta si…</span>${lista(g.consultar_si)}`);
    if (g && etiqueta === 'Señales de alarma') return mostrar('bot lista alert', `<span class="t">Ve a urgencias o llama al 123 si…</span>${lista(g.alarma)}`);
    enviar(etiqueta);
  }

  async function enviar(texto) {
    texto = (texto || '').trim(); if (!texto) return;
    quitarChips();
    burbuja('me', esc(texto));
    const espera = burbuja('bot', '<span class="puntos">···</span>');
    try {
      const r = await Api.orientar(texto, estado.hora, tipoDe(estado.dia), estado.dia, estado.guia ? estado.guia.id : null);
      espera.remove();
      if (r.mensaje && !(r.ficha && r.accion === 'datos')) burbuja(r.accion === 'urgencias_ya' ? 'bot alert' : 'bot', esc(r.mensaje));
      if (r.guia) estado.guia = r.guia; else if (!['contexto', 'medicamento', 'informacion', 'datos', 'conversacion'].includes(r.accion)) estado.guia = null;
      if (r.accion === 'urgencias_ya') { burbuja('bot lista alert', '<span class="t">Mientras llega la ayuda</span><ul><li>Mantén la calma y no te quedes solo/a.</li><li>No comas ni tomes nada.</li><li>Si es posible, ten a mano tus documentos y tus medicamentos.</li></ul>'); return chips(['Nueva consulta']); }
      if (r.ficha) burbuja('bot lista', `<span class="t">${esc(r.ficha.titulo)}</span>${r.ficha.subtitulo ? `<span class="sub-b">${esc(r.ficha.subtitulo)}</span>` : ''}${lista(r.ficha.items)}${r.ficha.aviso ? `<span class="pie-b">${esc(r.ficha.aviso)}</span>` : ''}`);
      if (r.guia) return chips(guiaChips());
      if (r.accion === 'orientacion_cita') return chips(['Reservar cita', 'Nueva consulta']);
      chips((r.sugerencias && r.sugerencias.length ? r.sugerencias : []).concat(r.accion === 'conversacion' ? [] : ['Nueva consulta']));
    } catch (e) {
      espera.remove();
      burbuja('bot', 'No pude consultar en este momento. Si es urgente, llama al 123. ' + esc(e.message || ''));
      chips(['Nueva consulta']);
    }
  }
  function preguntarDesdeFuera(texto) {
    $('#orientacion').scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => enviar(texto), 350);
  }

  /* ------------------------------------------------------------------ a donde ir */
  async function cargarDia(dia) {
    estado.dia = dia;
    $$('#p-dias button').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.d === dia)));
    try {
      if (!estado.cache[dia]) estado.cache[dia] = await Api.esperaPorDia(dia);
      estado.datos = estado.cache[dia];
      pintar();
    } catch (e) { $('#pv-reco').textContent = 'No se pudo consultar: ' + e.message; }
  }

  function pintar() {
    const d = estado.datos; if (!d) return;
    const h = estado.hora;
    const centros = d.centros.map((c) => ({ ips: c.ips, w: c.horas[h].espera_min, n: c.horas[h].atenciones })).filter((x) => x.w != null).sort((a, b) => a.w - b.w);
    if (!centros.length) { $('#pv-reco').textContent = 'No hay atenciones registradas a esa hora.'; $('#pv-barras').innerHTML = ''; $('#pv-mejores').innerHTML = ''; return; }
    const mejor = centros[0], peor = centros[centros.length - 1], max = Math.max(...centros.map((x) => x.w), 1);
    $('#pv-reco').innerHTML = `El ${DIAS[estado.dia].toLowerCase()} a las ${hora12(h)} (${franjaDe(h).toLowerCase()}), la mejor opción es <b>${NOMBRE(mejor.ips)}</b>, con una espera de unos <b>${fmt(mejor.w)} minutos</b>.` +
      (centros.length > 1 ? ` Ir ahí en lugar de ${NOMBRE(peor.ips)} te ahorra unos ${fmt(peor.w - mejor.w)} minutos.` : '');
    $('#pv-barras').innerHTML = centros.map((x, i) => `<div class="pv-fila ${i === 0 ? 'mejor' : i === centros.length - 1 && centros.length > 1 ? 'peor' : ''}"><span class="nom">${NOMBRE(x.ips)}${i === 0 ? ' · la más corta' : ''}</span><span class="barra"><i style="width:${Math.max(4, (x.w / max) * 100)}%"></i></span><b>${fmt(x.w)} min</b></div>`).join('');
    // el mejor momento de cada franja del dia
    const rangos = [['Mañana', 6, 11], ['Tarde', 12, 17], ['Noche', 18, 20]];
    const filas = rangos.map(([nombre, a, b]) => {
      let mejorHora = null;
      for (let hh = a; hh <= b; hh++) for (const c of d.centros) { const w = c.horas[hh].espera_min; if (w != null && (!mejorHora || w < mejorHora.w)) mejorHora = { hh, ips: c.ips, w }; }
      return mejorHora ? `<li><b>${nombre}:</b> ${hora12(mejorHora.hh)} en ${NOMBRE(mejorHora.ips)}, espera de unos ${fmt(mejorHora.w)} minutos</li>` : '';
    }).join('');
    $('#pv-mejores').innerHTML = filas ? `<h3>El mejor momento de cada parte del día</h3><ul>${filas}</ul>` : '';
    const pocos = centros.some((x) => x.n != null && x.n < 10);
    $('#pv-nota').textContent = (pocos ? 'A esta hora hubo pocas atenciones: tómalo como una idea general. ' : '') + (d.aproximado ? 'Sin conexión al sistema se muestra el promedio entre semana, sábado o domingo.' : '');
  }

  function iniciarDonde() {
    $('#p-dias').innerHTML = DIAS.map((n, i) => `<button type="button" data-d="${i}" aria-pressed="${i === hoy}" title="${n}${i === hoy ? ' (hoy)' : ''}" class="${i === hoy ? 'hoy' : ''}">${n.slice(0, 3)}</button>`).join('');
    $('#p-dias').onclick = (e) => { const b = e.target.closest('button'); if (b) cargarDia(+b.dataset.d); };
    const sel = $('#p-hora-sel');
    const grupo = (nombre, a, b) => `<optgroup label="${nombre}">${Array.from({ length: b - a + 1 }, (_, k) => `<option value="${a + k}">${hora12(a + k)}</option>`).join('')}</optgroup>`;
    sel.innerHTML = grupo('Madrugada', 0, 5) + grupo('Mañana', 6, 11) + grupo('Tarde', 12, 17) + grupo('Noche', 18, 23);
    sel.value = estado.hora;
    sel.onchange = () => { estado.hora = +sel.value; pintar(); };
    return cargarDia(hoy);
  }

  /* ------------------------------------------------------------------ reserva de citas */
  const cal = { ips: null, mes: null, datos: null, fecha: null, hora: null, franjas: null };
  const mesActual = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`; };
  const sumarMes = (mes, n) => { const [a, m] = mes.split('-').map(Number); const d = new Date(a, m - 1 + n, 1); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`; };

  async function cargarCalendario() {
    const cont = $('#cal-dias');
    try {
      cal.datos = await http(`/api/citas/calendario?ips=${encodeURIComponent(cal.ips)}&mes=${cal.mes}`);
    } catch (e) { cont.innerHTML = `<p class="sub">${esc(e.message)}</p>`; return; }
    const [a, m] = cal.mes.split('-').map(Number);
    $('#cal-mes').textContent = `${MESES[m - 1][0].toUpperCase()}${MESES[m - 1].slice(1)} de ${a}`;
    $('#cal-prev').disabled = cal.mes <= mesActual();
    $('#cal-next').disabled = cal.mes >= sumarMes(mesActual(), 3);
    const vacios = '<span class="cal-vacio"></span>'.repeat(cal.datos.primer_dia_semana);
    cont.innerHTML = vacios + cal.datos.dias.map((d) => {
      const n = +d.fecha.slice(8);
      const tip = d.disponible ? `${d.libres} cupos libres${d.espera_tipica_min ? ` · espera típica de ${fmt(d.espera_tipica_min)} min` : ''}` : 'Sin cupos';
      return `<button type="button" class="cal-dia n-${d.nivel}${d.fecha === cal.fecha ? ' sel' : ''}" data-f="${d.fecha}" ${d.disponible ? '' : 'disabled'} title="${tip}" aria-label="${fechaLarga(d.fecha)}. ${tip}"><span>${n}</span></button>`;
    }).join('');
  }

  async function elegirFecha(f) {
    cal.fecha = f; cal.hora = null;
    $$('#cal-dias .cal-dia').forEach((b) => b.classList.toggle('sel', b.dataset.f === f));
    $('#r-form').hidden = true; $('#r-ok').hidden = true;
    const cont = $('#r-franjas');
    cont.innerHTML = '<p class="sub">Buscando horarios…</p>';
    try {
      cal.franjas = await http(`/api/citas/franjas?ips=${encodeURIComponent(cal.ips)}&fecha=${f}`);
    } catch (e) { cont.innerHTML = `<p class="sub">${esc(e.message)}</p>`; return; }
    const grupos = {};
    cal.franjas.franjas.forEach((x) => { (grupos[x.franja] = grupos[x.franja] || []).push(x); });
    const reco = cal.franjas.franjas.filter((x) => x.recomendada).map((x) => hora12(+x.hora.slice(0, 2), +x.hora.slice(3))).join(', ');
    cont.innerHTML = `<h3>${fechaLarga(f)}</h3><p class="sub">${NOMBRE(cal.ips)} · ${esc(estado.esp)}</p>` +
      (reco ? `<p class="reco-txt">Horarios con menos espera: <b>${reco}</b></p>` : '') +
      Object.entries(grupos).map(([nombre, xs]) => `<div class="franja-grupo"><span class="etiqueta">${nombre[0].toUpperCase()}${nombre.slice(1)}</span><div class="chips-hora">${xs.map((x) => {
        const [hh, mm] = [+x.hora.slice(0, 2), +x.hora.slice(3)];
        return `<button type="button" class="hora${x.recomendada ? ' reco' : ''}" data-h="${x.hora}" ${x.disponible ? '' : 'disabled'}>${hora12(hh, mm)}<small>${x.disponible ? (x.espera_min != null ? `≈ ${fmt(x.espera_min)} min` : `${x.libres} cupos`) : 'Lleno'}</small>${x.recomendada ? '<em>Recomendada</em>' : ''}</button>`;
      }).join('')}</div></div>`).join('');
  }

  function elegirHora(h) {
    cal.hora = h;
    $$('#r-franjas .hora').forEach((b) => b.classList.toggle('sel', b.dataset.h === h));
    const f = $('#r-form'); f.hidden = false; $('#r-ok').hidden = true; $('#r-error').textContent = '';
    $('#r-resumen').textContent = `${fechaLarga(cal.fecha)} · ${hora12(+h.slice(0, 2), +h.slice(3))} · ${NOMBRE(cal.ips)}`;
    f.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    $('#r-nombre').focus({ preventScroll: true });
  }

  function ics(c) {
    const [y, m, d] = c.fecha.split('-'); const [hh, mm] = c.hora.split(':');
    const ini = `${y}${m}${d}T${hh}${mm}00`; const fin = new Date(+y, +m - 1, +d, +hh, +mm + 30); const f2 = `${fin.getFullYear()}${pad(fin.getMonth() + 1)}${pad(fin.getDate())}T${pad(fin.getHours())}${pad(fin.getMinutes())}00`;
    return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//VitalData//Citas//ES', 'BEGIN:VEVENT', `UID:${c.codigo}@vitaldata`, `DTSTAMP:${ini}`, `DTSTART:${ini}`, `DTEND:${f2}`,
      `SUMMARY:Cita de ${c.especialidad} - ${NOMBRE(c.ips)}`, `DESCRIPTION:Código de la cita: ${c.codigo}. Llega 10 minutos antes.`, `LOCATION:${NOMBRE(c.ips)}`, 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
  }
  function descargarIcs(c) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([ics(c)], { type: 'text/calendar' })); a.download = `cita-${c.codigo}.ics`;
    document.body.appendChild(a); a.click(); a.remove();
  }
  const tarjetaCita = (c, titulo) => `<h3>${titulo}</h3><div class="codigo">${esc(c.codigo)}</div>
    <p><b>${fechaLarga(c.fecha)}</b> a las <b>${hora12(+c.hora.slice(0, 2), +c.hora.slice(3))}</b></p><p>${NOMBRE(c.ips)} · ${esc(c.especialidad)}</p>
    <p class="nota">Llega 10 minutos antes. Guarda el código para consultar o cancelar la cita.</p>
    <div class="cta"><button type="button" class="boton-sec" data-a="ics">Agregar a mi calendario</button><button type="button" class="boton-sec" data-a="copiar">Copiar código</button><button type="button" class="boton-sec peligro" data-a="cancelar">Cancelar cita</button></div>`;

  function conectarTarjeta(cont, c) {
    cont.onclick = async (e) => {
      const b = e.target.closest('button[data-a]'); if (!b) return;
      if (b.dataset.a === 'ics') return descargarIcs(c);
      if (b.dataset.a === 'copiar') { try { await navigator.clipboard.writeText(c.codigo); b.textContent = 'Código copiado'; } catch (er) { b.textContent = c.codigo; } return; }
      if (b.dataset.a === 'cancelar') {
        if (!confirm('¿Seguro que quieres cancelar esta cita?')) return;
        try { const r = await http(`/api/citas/${c.codigo}/cancelar`, { method: 'POST' }); cont.innerHTML = `<h3>Cita cancelada</h3><p>La cita <b>${esc(r.codigo)}</b> quedó cancelada y el horario volvió a quedar libre.</p>`; cargarCalendario(); if (cal.fecha) elegirFecha(cal.fecha); }
        catch (er) { alert(er.message); }
      }
    };
  }

  async function enviarCita(e) {
    e.preventDefault();
    const err = $('#r-error'); err.textContent = '';
    const nombre = $('#r-nombre').value.trim(), contacto = $('#r-contacto').value.trim();
    if (nombre.length < 2) return (err.textContent = 'Escribe tu nombre.');
    if (!contacto) return (err.textContent = 'Escribe un celular o un correo.');
    if (!$('#r-acepta').checked) return (err.textContent = 'Debes aceptar el uso de tus datos para reservar.');
    const boton = $('#r-form button[type=submit]'); boton.disabled = true;
    try {
      const c = await http('/api/citas', enJson({ ips: cal.ips, fecha: cal.fecha, hora: cal.hora, especialidad: estado.esp, motivo: $('#r-motivo').value.trim() || null, nombre, contacto, acepta_datos: true }));
      try { localStorage.setItem('vd_cita', c.codigo); } catch (er) { /* sin almacenamiento */ }
      $('#r-form').hidden = true; $('#r-form').reset();
      const ok = $('#r-ok'); ok.hidden = false; ok.innerHTML = tarjetaCita(c, 'Tu cita quedó reservada'); conectarTarjeta(ok, c); ok.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      cargarCalendario(); elegirFecha(cal.fecha);
    } catch (er2) {
      err.textContent = er2.message;
      if (er2.status === 409) elegirFecha(cal.fecha);
    } finally { boton.disabled = false; }
  }

  async function consultarCita(e) {
    e.preventDefault();
    const cod = $('#m-codigo').value.trim(); const cont = $('#m-res');
    if (!cod) return;
    try {
      const c = await http(`/api/citas/${encodeURIComponent(cod)}`);
      if (c.estado === 'cancelada') { cont.innerHTML = `<div class="cita-ok"><h3>Cita cancelada</h3><p>La cita <b>${esc(c.codigo)}</b> fue cancelada.</p></div>`; cont.onclick = null; return; }
      cont.innerHTML = `<div class="cita-ok" id="m-tarjeta">${tarjetaCita(c, `Cita de ${esc(c.nombre)}`)}</div>`; conectarTarjeta($('#m-tarjeta'), c);
    } catch (er) { cont.innerHTML = `<p class="error">${esc(er.message)}</p>`; }
  }

  async function iniciarReserva() {
    if (Api.mode !== 'live') { $('#reservar .reserva').innerHTML = '<p class="sub">La reserva de citas necesita el sistema en marcha (docker compose up).</p>'; $('.mi-cita').hidden = true; return; }
    let info; try { info = await http('/api/citas/especialidades'); } catch (e) { $('#reservar .reserva').innerHTML = `<p class="sub">${esc(e.message)}</p>`; return; }
    const lista = await Api.ips().catch(() => []);
    estado.ips = (lista || []).filter((i) => i.modelable).map((i) => i.nombre);
    if (!estado.ips.length) estado.ips = estado.datos ? estado.datos.centros.map((c) => c.ips) : [];
    if (estado.datos) {                                   // el centro con menos espera tipica queda de primero
      const media = (n) => { const c = estado.datos.centros.find((x) => x.ips === n); const v = c ? c.horas.slice(7, 19).map((h) => h.espera_min).filter((x) => x != null) : []; return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 1e9; };
      estado.ips.sort((a, b) => media(a) - media(b));
    }
    $('#r-ips').innerHTML = estado.ips.map((n, i) => `<option value="${esc(n)}">${NOMBRE(n)}${i === 0 && estado.ips.length > 1 ? ' · menos espera' : ''}</option>`).join('');
    $('#r-esp').innerHTML = info.especialidades.map((n) => `<option>${esc(n)}</option>`).join('');
    cal.ips = $('#r-ips').value; cal.mes = mesActual();
    $('#r-ips').onchange = () => { cal.ips = $('#r-ips').value; cal.fecha = null; $('#r-franjas').innerHTML = '<p class="sub">Elige un día en el calendario para ver los horarios.</p>'; $('#r-form').hidden = true; cargarCalendario(); };
    $('#r-esp').onchange = () => { estado.esp = $('#r-esp').value; if (cal.fecha) elegirFecha(cal.fecha); };
    $('#cal-prev').onclick = () => { cal.mes = sumarMes(cal.mes, -1); cargarCalendario(); };
    $('#cal-next').onclick = () => { cal.mes = sumarMes(cal.mes, 1); cargarCalendario(); };
    $('#cal-dias').onclick = (e) => { const b = e.target.closest('.cal-dia'); if (b && !b.disabled) elegirFecha(b.dataset.f); };
    $('#r-franjas').onclick = (e) => { const b = e.target.closest('.hora'); if (b && !b.disabled) elegirHora(b.dataset.h); };
    $('#r-form').onsubmit = enviarCita;
    $('#m-form').onsubmit = consultarCita;
    try { const ult = localStorage.getItem('vd_cita'); if (ult) $('#m-codigo').value = ult; } catch (e) { /* sin almacenamiento */ }
    await cargarCalendario();
    const primero = cal.datos && cal.datos.dias.find((d) => d.disponible);
    if (primero) elegirFecha(primero.fecha);
  }

  /* ------------------------------------------------------------------ verificador de urgencias y primeros auxilios */
  const GRUPOS = [
    ['Respiración y pecho', [['u', 'Dificultad para respirar o falta de aire'], ['u', 'Labios o cara morados'], ['u', 'Dolor fuerte u opresión en el pecho']]],
    ['Cabeza y sistema nervioso', [['u', 'Desmayo o pérdida del conocimiento'], ['u', 'Convulsiones'], ['u', 'Debilidad súbita de un lado del cuerpo, cara caída o dificultad para hablar'], ['u', 'El peor dolor de cabeza de mi vida, o uno que empezó de golpe'], ['u', 'Confusión o mucho sueño difícil de despertar']]],
    ['Sangrado y heridas', [['u', 'Sangrado que no para después de 10 minutos de presión'], ['u', 'Vómito con sangre o heces negras'], ['p', 'Herida profunda o sucia, sin sangrado fuerte']]],
    ['Alergias y envenenamiento', [['u', 'Hinchazón de labios, lengua o garganta'], ['u', 'Intoxicación o envenenamiento']]],
    ['Bebés, niños y embarazo', [['u', 'Bebé menor de 3 meses con fiebre'], ['u', 'Embarazada con sangrado o dolor fuerte'], ['p', 'Niño con fiebre y muy decaído']]],
    ['Salud mental', [['u', 'Pensamientos de hacerme daño o de morir']]],
    ['Otros síntomas', [['p', 'Fiebre de más de 3 días'], ['p', 'Vómito o diarrea que no me deja tomar líquidos'], ['p', 'Dolor de abdomen que empeora'], ['p', 'Dolor al orinar con fiebre'], ['p', 'Torcedura o golpe y no puedo apoyar'], ['p', 'Dolor que no cede con analgésicos simples']]],
  ];
  const AUXILIOS = [
    ['Atragantamiento (adulto o niño mayor)', ['Pregunta si se está atragantando. Si no puede toser, hablar ni respirar, llama al 123 o pide que lo hagan.', 'Colócate detrás y rodéalo con los brazos.', 'Pon un puño sobre el abdomen, por encima del ombligo, y presiona con fuerza hacia adentro y hacia arriba (maniobra de Heimlich).', 'Repite hasta que expulse el objeto. Si pierde el conocimiento, acuéstalo y empieza las compresiones del pecho.', 'En bebés menores de 1 año no uses esta maniobra: llama al 123 y alterna 5 palmadas en la espalda con 5 compresiones en el pecho.']],
    ['Paro cardíaco: compresiones en el pecho', ['Si la persona no responde y no respira con normalidad, llama al 123 o pide que lo hagan y que traigan un desfibrilador (DEA) si hay uno.', 'Acuéstala boca arriba sobre una superficie firme.', 'Entrelaza las manos en el centro del pecho y comprime fuerte y rápido: unos 5 a 6 cm de profundidad, de 100 a 120 veces por minuto.', 'Deja que el pecho suba entre compresión y compresión.', 'No pares hasta que llegue la ayuda o la persona reaccione.']],
    ['Sangrado', ['Presiona directamente sobre la herida con una gasa o tela limpia y no la retires.', 'Si se empapa, agrega otra encima y sigue presionando.', 'Si es posible, eleva la zona.', 'Si no para en 10 minutos o es abundante, llama al 123.']],
    ['Quemaduras', ['Enfría con agua fría (no helada) durante 10 a 20 minutos.', 'Quita anillos o pulseras antes de que se hinche.', 'Cubre con una gasa limpia, sin pegar.', 'No uses hielo, pasta de dientes ni aceite, y no revientes las ampollas.', 'Ve a urgencias si es grande, en la cara, las manos o los genitales, o si fue por electricidad o químicos.']],
    ['Convulsiones', ['Mantén la calma, aparta los objetos y protege la cabeza con algo blando.', 'No sujetes a la persona ni le metas nada en la boca.', 'Cuando termine, colócala de lado.', 'Llama al 123 si dura más de 5 minutos, es la primera vez, hay lesiones o no recupera el conocimiento.']],
    ['Desmayo', ['Acuesta a la persona boca arriba y eleva las piernas.', 'Afloja la ropa y verifica que respira.', 'Si no reacciona en un minuto o no respira con normalidad, llama al 123.', 'Al despertar, que se siente despacio. No le des de comer ni de beber de inmediato.']],
    ['Reacción alérgica grave', ['Si hay hinchazón de labios o lengua o dificultad para respirar después de una picadura, un alimento o un medicamento, llama al 123 de inmediato.', 'Si la persona tiene un autoinyector de adrenalina indicado por su médico, úsalo.', 'Acuéstala con las piernas elevadas.']],
  ];

  AUXILIOS.push(
    ['Infarto o dolor fuerte de pecho', ['Llama al 123 de inmediato.', 'Siéntate o recuéstate con la espalda apoyada y no hagas ningún esfuerzo.', 'Afloja la ropa y mantén la calma.', 'No te quedes solo/a ni comas o bebas nada.', 'Si pierde el conocimiento y no respira con normalidad, empieza las compresiones del pecho. El personal de emergencia te indicará si debe tomar algún medicamento.']],
    ['Derrame cerebral (ACV): CARA, BRAZO, HABLA, TIEMPO', ['Cara: pídele que sonría. ¿Un lado de la cara cae?', 'Brazos: pídele que levante ambos. ¿Uno cae o está débil?', 'Habla: pídele que repita una frase. ¿Arrastra las palabras o no puede?', 'Tiempo: si hay cualquiera de estos signos, llama al 123 ya y anota la hora en que empezó.', 'No le des comida, agua ni medicamentos.']],
    ['Fracturas y golpes en huesos', ['No muevas la zona ni intentes acomodar el hueso.', 'Inmoviliza como está, con una tabla, una revista enrollada o una férula improvisada, sin apretar.', 'Aplica hielo envuelto en un paño y eleva la zona si puedes.', 'Ve a urgencias. Si el hueso sale por la piel o hay mucho sangrado, llama al 123.']],
    ['Golpe en la cabeza', ['Aplica frío sobre el golpe y mantén a la persona en reposo.', 'Vigílala durante las siguientes 24 horas.', 'Ve a urgencias si hay vómito repetido, confusión, mucho sueño, convulsión, dolor de cabeza que aumenta o salida de sangre o líquido por la nariz o el oído.', 'En niños pequeños, consulta siempre.']],
    ['Quemadura solar o por calor extremo (golpe de calor)', ['Lleva a la persona a un lugar fresco y a la sombra.', 'Afloja la ropa y refresca el cuerpo con paños húmedos.', 'Si está consciente, dale agua o suero oral en sorbos.', 'Llama al 123 si hay confusión, desmayo, piel muy caliente y seca o convulsiones.']],
    ['Picadura de abeja o avispa', ['Retira el aguijón raspando con el borde de una tarjeta, sin apretarlo con pinzas.', 'Lava con agua y jabón y aplica frío.', 'Vigila durante 30 minutos.', 'Llama al 123 si hay hinchazón de cara o lengua, dificultad para respirar o mareo.']],
    ['Mordedura de serpiente', ['Mantén a la persona quieta y calmada.', 'Inmoviliza la extremidad a la altura del corazón o más abajo y quita anillos y pulseras.', 'Llama al 123 y llévala a urgencias de inmediato.', 'No cortes la herida, no succiones, no pongas torniquete ni hielo y no des alcohol.']],
    ['Mordedura de perro o gato', ['Lava la herida con agua y jabón durante 10 minutos.', 'Cubre con una gasa limpia.', 'Ve a un centro de salud el mismo día: puede necesitar vacuna antitetánica o antirrábica.', 'Anota si el animal era conocido y si está vacunado.']],
    ['Cuerpo extraño en el ojo', ['No te frotes el ojo.', 'Lava con abundante agua limpia o suero fisiológico y parpadea.', 'Si el objeto está clavado, hay dolor intenso o la vista cambia, cubre el ojo sin presionar y ve a urgencias.', 'Con productos químicos, lava durante 15 minutos y consulta.']],
    ['Azúcar baja en una persona con diabetes', ['Si está consciente, dale algo con azúcar: jugo, gaseosa o un caramelo.', 'Que se siente y espere 15 minutos; vuelve a medir si tiene glucómetro.', 'Cuando mejore, que coma algo con carbohidratos.', 'Si está confundido, desmayado o convulsiona, llama al 123 y no le des nada por la boca.']],
    ['Crisis de asma', ['Siéntalo derecho y tranquilo.', 'Que use su inhalador de rescate como se lo indicó su médico.', 'Aflója la ropa y ventila el espacio.', 'Si no mejora en 10 a 15 minutos, no puede hablar una frase completa o los labios se ven azules, llama al 123.']],
    ['Ahogamiento', ['Saca a la persona del agua sin ponerte en riesgo y llama al 123.', 'Si no respira con normalidad, empieza las compresiones del pecho.', 'Si respira, acuéstala de lado y abrígala.', 'Aunque parezca recuperada, debe valorarla un médico.']],
    ['Electrocución', ['No toques a la persona hasta que la corriente esté cortada.', 'Llama al 123.', 'Si no respira con normalidad, empieza las compresiones del pecho.', 'Cubre las quemaduras con una gasa limpia, sin pegar.']],
    ['Intoxicación o envenenamiento', ['Llama al 123 y cuenta qué se tomó, cuánto y hace cuánto.', 'Guarda el envase para mostrarlo.', 'No provoques el vómito ni des leche o remedios caseros.', 'Si cayó en la piel o los ojos, lava con abundante agua durante 15 minutos.']],
    ['Amputación o corte grave', ['Llama al 123 y aplica presión directa fuerte con una tela limpia.', 'Si hay una parte cortada, envuélvela en una gasa húmeda, guárdala en una bolsa limpia y ponla dentro de otra bolsa con hielo, sin tocar el hielo directamente.', 'Lleva la parte junto con la persona a urgencias.']],
  );
  GRUPOS[0][1].push(['u', 'Atragantamiento: no puede toser ni hablar']);
  GRUPOS[1][1].push(['u', 'Pérdida repentina de la visión']);
  GRUPOS[2][1].push(['u', 'Golpe fuerte en la cabeza con vómito, confusión o mucho sueño']);
  GRUPOS[3][1].push(['u', 'Quemadura extensa, en la cara o por electricidad o químicos'], ['u', 'Herida por arma blanca o de fuego, o accidente de tránsito con golpe fuerte']);
  GRUPOS[4][1].push(['p', 'Sangrado vaginal fuera de la regla'], ['u', 'Dolor repentino e intenso en los testículos']);
  GRUPOS[6][1].push(['u', 'Dolor de abdomen muy fuerte y repentino'], ['u', 'Fiebre alta con rigidez de cuello o manchas moradas en la piel'], ['p', 'Orina con sangre'], ['p', 'Una pierna hinchada, roja y dolorosa'], ['p', 'Ojo rojo con dolor'], ['p', 'Mareos que se repiten']);

  function iniciarVerificador() {
    const cont = $('#verif-lista');
    cont.innerHTML = GRUPOS.map(([nombre, items], g) => `<fieldset><legend>${nombre}</legend>${items.map(([tipo, texto], i) => `<label><input type="checkbox" data-t="${tipo}" value="${esc(texto)}" id="v${g}-${i}"><span>${esc(texto)}</span></label>`).join('')}</fieldset>`).join('');
    const res = $('#verif-res');
    const evaluar = () => {
      const marcados = $$('#verif-lista input:checked');
      const urg = marcados.filter((x) => x.dataset.t === 'u').map((x) => x.value), pro = marcados.filter((x) => x.dataset.t === 'p').map((x) => x.value);
      if (urg.length) res.innerHTML = `<div class="res-urgente"><h3>Llama al 123 o ve a urgencias ya</h3><p>No esperes ni pidas una cita. Lo que marcaste necesita atención inmediata:</p>${lista(urg)}<p class="nota">Mientras llega la ayuda: mantén la calma, no te quedes solo/a, no comas ni tomes nada.</p></div>`;
      else if (pro.length) res.innerHTML = `<div class="res-pronto"><h3>Conviene que te vea un profesional hoy</h3><p>Pide una cita prioritaria o una teleconsulta. Si aparece alguno de los signos de alarma, ve a urgencias.</p>${lista(pro)}<a class="boton-sec chico" href="#reservar" data-esp="Cita prioritaria">Reservar cita prioritaria</a></div>`;
      else res.innerHTML = '<div class="res-casa"><h3>Marca lo que esté pasando</h3><p>Si no tienes ninguno de estos signos, cuéntale al asistente qué sientes para recibir orientación sobre qué hacer en casa y cuándo consultar.</p><a class="boton-sec chico" href="#orientacion">Hablar con el asistente</a></div>';
    };
    cont.onchange = evaluar; evaluar();
    res.onclick = (e) => { const a = e.target.closest('a[data-esp]'); if (a) { e.preventDefault(); irAReservar(a.dataset.esp); } };
    $('#auxilios').innerHTML = AUXILIOS.map(([t, pasos]) => `<details data-t="${esc((t + ' ' + pasos.join(' ')).toLowerCase())}"><summary>${t}</summary><ol>${pasos.map((p) => `<li>${esc(p)}</li>`).join('')}</ol></details>`).join('');
    const filtrar = () => {
      const q = $('#aux-buscar').value.trim().toLowerCase(); let n = 0;
      $$('#auxilios details').forEach((d) => { const ok = !q || d.dataset.t.includes(q); d.hidden = !ok; if (ok) n++; });
      $('#aux-n').textContent = q ? `${n} ${n === 1 ? 'resultado' : 'resultados'}` : `${AUXILIOS.length} guías`;
    };
    $('#aux-buscar').oninput = filtrar; filtrar();
  }

  /* ------------------------------------------------------------------ preguntas frecuentes */
  const FAQ = [
    ['¿El asistente reemplaza a un médico?', 'No. Da orientación general de autocuidado y te dice cuándo consultar. No diagnostica ni receta, y ante señales de alarma te manda a urgencias o a llamar al 123.'],
    ['¿Qué temas conoce el asistente?', 'Más de 90 temas de muchas especialidades: síntomas comunes, pediatría, ginecología, dermatología, ortopedia, salud mental, enfermedades crónicas y más. Si no conoce un tema, lo dice y te ayuda a reservar con un profesional.'],
    ['¿De dónde salen las esperas que muestran?', 'De los datos abiertos de la E.S.E. Pasto Salud (datos.gov.co) de 2022: promedio de lo que esperaron los pacientes en cada centro, según el día y la hora. Son una guía y no una garantía.'],
    ['¿Cómo funciona la reserva de citas?', 'Eliges el centro, la especialidad, el día y la hora. Recibes un código para consultar o cancelar la cita, y puedes agregarla a tu calendario. Cada horario tiene un número limitado de cupos.'],
    ['¿Cómo cancelo una cita?', 'En «¿Ya tienes una cita?», escribe tu código y pulsa «Cancelar cita». El horario queda libre para otra persona.'],
    ['¿Qué pasa con mis datos?', 'Para reservar guardamos solo tu nombre, tu celular o correo y el motivo. Se usan únicamente para gestionar la cita, no se comparten y en la pantalla de consulta se muestran parcialmente ocultos.'],
    ['¿Cuánto cuesta?', 'Para el paciente es gratis. El servicio se ofrece a los hospitales para organizar mejor su personal.'],
    ['¿Qué hago si el centro con menos espera está lejos?', 'La espera es una guía, no la única razón. Elige el centro más cercano si lo necesitas, y recuerda que en una emergencia debes ir al más cercano o llamar al 123.'],
    ['¿Puedo reservar para otra persona?', 'Sí: escribe el nombre de quien va a asistir y un contacto con el que podamos avisarle.'],
  ];
  function iniciarFaq() {
    $('#faq').innerHTML = FAQ.map(([q, a]) => `<details><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join('');
  }

  /* ------------------------------------------------------------------ opiniones */
  const estrellas = (n) => '★'.repeat(Math.round(n)) + '☆'.repeat(5 - Math.round(n));
  async function cargarOpiniones() {
    if (Api.mode !== 'live') { $('#opiniones .opiniones').innerHTML = '<p class="sub">Las opiniones necesitan el sistema en marcha.</p>'; return; }
    let r; try { r = await http('/api/resenas'); } catch (e) { $('#op-lista').innerHTML = `<p class="sub">${esc(e.message)}</p>`; return; }
    const max = Math.max(1, ...Object.values(r.distribucion));
    $('#op-resumen').innerHTML = r.total
      ? `<div class="prom"><b>${String(r.promedio).replace('.', ',')}</b><span class="est-g" aria-hidden="true">${estrellas(r.promedio)}</span><small>${r.total} ${r.total === 1 ? 'opinión' : 'opiniones'}</small></div>` +
        [5, 4, 3, 2, 1].map((k) => `<div class="dist"><span>${k} ★</span><span class="barra"><i style="width:${(r.distribucion[k] / max) * 100}%"></i></span><span>${r.distribucion[k]}</span></div>`).join('')
      : '<div class="prom"><b>–</b><small>Aún no hay opiniones</small></div><p class="sub">Sé la primera persona en contarnos qué te pareció.</p>';
    $('#op-lista').innerHTML = r.resenas.map((x) => `<article class="op"><div class="op-cab"><span class="est-g" aria-label="${x.estrellas} de 5 estrellas">${estrellas(x.estrellas)}</span><b>${esc(x.nombre)}</b><small>${esc(x.fecha)}</small></div><p>${esc(x.comentario)}</p></article>`).join('');
  }
  function iniciarOpiniones() {
    $('#op-form').onsubmit = async (e) => {
      e.preventDefault();
      const msg = $('#op-msg'); msg.textContent = ''; msg.className = 'error';
      const est = $('input[name=est]:checked'); const texto = $('#op-texto').value.trim();
      if (!est) return (msg.textContent = 'Elige cuántas estrellas das.');
      if (texto.length < 5) return (msg.textContent = 'Cuéntanos un poco más (mínimo 5 letras).');
      try {
        await http('/api/resenas', enJson({ estrellas: +est.value, nombre: $('#op-nombre').value.trim() || null, comentario: texto }));
        $('#op-form').reset(); msg.className = 'ok'; msg.textContent = '¡Gracias por tu opinión!'; cargarOpiniones();
      } catch (er) { msg.textContent = er.message; }
    };
    cargarOpiniones();
  }

  /* ------------------------------------------------------------------ hospitales */
  const cop = (v) => '$' + Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  async function iniciarHospitales() {
    // cifras reales del sistema
    const ev = (window.SNAPSHOT || {});
    const celdas = [];
    try { const r = await http('/api/resumen'); celdas.push([fmt(r.atenciones), 'atenciones reales analizadas'], [fmt(r.espera_mediana_min) + ' min', 'espera mediana en los datos']); } catch (e) { /* sin API */ }
    try {
      const m = await http('/api/metricas');
      const p3 = m.map((x) => x.metricas.metricas['3h'].vitaldata.precision), pd = m.map((x) => x.metricas.metricas.dia.vitaldata.precision);
      celdas.push([`${Math.round(100 * pd.reduce((a, b) => a + b, 0) / pd.length)} %`, 'precisión del pronóstico por día'], [`${Math.round(100 * Math.min(...p3))} a ${Math.round(100 * Math.max(...p3))} %`, 'precisión por franja de 3 horas']);
    } catch (e) { /* sin API */ }
    if (ev.ev_benchmark) celdas.push([`${fmt(ev.ev_benchmark.p95_ms)} ms`, 'respuesta de la API (percentil 95)']);
    if (ev.ev_pruebas) celdas.push([fmt(ev.ev_pruebas.total), 'pruebas automáticas, todas pasan']);
    $('#hosp-cifras').innerHTML = celdas.map(([n, t]) => `<div><b>${n}</b><span>${t}</span></div>`).join('');

    // vista previa real del panel
    try {
      const ips = 'HOSPITAL LOCAL CIVIL', f = '2022-08-20';
      const [pr, pe] = await Promise.all([http(`/api/pronostico?ips=${encodeURIComponent(ips)}&fecha=${f}`), http(`/api/personal?ips=${encodeURIComponent(ips)}&fecha=${f}&dotacion=3`)]);
      const pico = pr.horas.map((h) => h.pronostico).indexOf(Math.max(...pr.horas.map((h) => h.pronostico)));
      const k = (l, v, s2) => `<div class="vp-k"><span>${l}</span><b>${v}</b><small>${s2}</small></div>`;
      $('#vp-kpis').innerHTML = k('Pacientes pronosticados', fmt(pr.total_pronosticado), `llegaron ${fmt(pr.total_real)}`) + k('Hora pico', `${pad(pico)}:00`, 'según el pronóstico') + k('Personal en el pico', pe.pico_personal, 'para una espera de 15 min') + k('Horas críticas', `${pe.horas_criticas} h`, 'con 3 personas');
      $('#vp-nota').textContent = 'Con 3 personas hay horas en las que la espera se dispara; con una más, ninguna. En el panel puedes explorar 53 días por centro.';
    } catch (e) { $('#vista-previa').hidden = true; }

    // simulador de ahorro
    const calc = () => {
      const horas = +$('#roi-extra').value || 0, costo = +$('#roi-costo').value || 0, precio = +$('#roi-precio').value || 0, red = +$('#roi-red').value / 100;
      $('#roi-red-v').textContent = Math.round(red * 100) + ' %';
      const gasto = horas * costo, ahorro = gasto * red, neto = ahorro - precio, equilibrio = gasto > 0 ? precio / gasto : null;
      $('#roi-res').innerHTML = `<div class="roi-k"><span>Gasto actual en horas extra</span><b>${cop(gasto)}</b></div><div class="roi-k"><span>Ahorro mensual estimado</span><b>${cop(ahorro)}</b></div>
        <div class="roi-k ${neto >= 0 ? 'bien' : 'mal'}"><span>${neto >= 0 ? 'Ahorro neto después del plan' : 'Diferencia frente al plan'}</span><b>${neto >= 0 ? '' : '−'}${cop(Math.abs(neto))}</b></div>
        <p class="roi-eq">${equilibrio == null ? 'Escribe tus horas extra para calcular.' : equilibrio > 1 ? 'Solo con horas extra no alcanzaría a cubrir el plan: el valor está también en esperas más cortas y mejor servicio.' : `El plan se paga solo si reduces tus horas extra en al menos <b>${(equilibrio * 100).toFixed(1).replace('.', ',')} %</b>.`}</p>`;
    };
    $('#roi').oninput = calc; $('#roi').onsubmit = (e) => e.preventDefault(); calc();

    // solicitud de demostracion
    $('#demo-hosp').onsubmit = async (e) => {
      e.preventDefault();
      const m = $('#dh-msj'); m.className = 'error'; m.textContent = '';
      const inst = $('#dh-inst').value.trim(), nombre = $('#dh-nombre').value.trim(), contacto = $('#dh-contacto').value.trim();
      if (inst.length < 2) return (m.textContent = 'Escribe el nombre de tu institución.');
      if (nombre.length < 2) return (m.textContent = 'Escribe tu nombre.');
      if (!contacto) return (m.textContent = 'Escribe un correo o un celular.');
      if (!$('#dh-acepta').checked) return (m.textContent = 'Debes aceptar el uso de tus datos para que podamos contactarte.');
      try {
        const r = await http('/api/hospitales/contacto', enJson({ institucion: inst, nombre, cargo: $('#dh-cargo').value.trim() || null, contacto, mensaje: $('#dh-msg').value.trim() || null, acepta_datos: true }));
        $('#demo-hosp').reset(); m.className = 'ok'; m.textContent = r.mensaje;
      } catch (er) { m.textContent = er.message; }
    };
  }

  /* ------------------------------------------------------------------ arranque */
  async function main() {
    tema();
    await Api.init();
    $('#temas').innerHTML = TEMAS.map((t) => `<button type="button">${t}</button>`).join('');
    $('#temas').onclick = (e) => { const b = e.target.closest('button'); if (b) { $('#chat-in').scrollIntoView({ behavior: 'smooth', block: 'center' }); accion(b.textContent); } };
    $('#form-hero').onsubmit = (e) => { e.preventDefault(); const i = $('#hero-in'); const t = i.value; i.value = ''; if (t.trim()) { $('#msgs').scrollIntoView({ behavior: 'smooth', block: 'center' }); enviar(t); } };
    $('#chat-form').onsubmit = (e) => { e.preventDefault(); const i = $('#chat-in'); const t = i.value; i.value = ''; enviar(t); };
    bienvenida();
    if (Api.mode !== 'live') burbuja('bot', 'Estás viendo una copia sin conexión. La orientación completa, las citas y las opiniones necesitan el sistema en marcha (docker compose up).');
    await iniciarDonde();
    iniciarVerificador();
    iniciarFaq();
    iniciarOpiniones();
    iniciarHospitales();
    await iniciarReserva();
    $('#ir-reservar').onclick = (e) => { e.preventDefault(); irAReservar(); };
  }
  main().catch((e) => { console.error(e); document.body.insertAdjacentHTML('afterbegin', `<p style="padding:16px;background:#FFE7E4;color:#7A1F18">No se pudo cargar la página: ${esc(e.message)}</p>`); });
})();
