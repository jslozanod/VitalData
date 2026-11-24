/* Graficas en SVG sin librerias externas (la pagina funciona sin internet). */
const NS = 'http://www.w3.org/2000/svg';
const cssv = (n, d) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
const C = {
  coral: '#FF4438', coralD: '#D9382B', gold: '#E0A100', ok: '#2E9E6B', blue: '#3B6FD4',
  get ink() { return cssv('--ink', '#22282D'); }, get gray() { return cssv('--gray', '#5E6770'); }, get mute() { return cssv('--mute', '#8A939B'); },
  get hair() { return cssv('--hair', '#E6DED0'); }, get band() { return cssv('--band', '#FFD4CF'); }, get panel() { return cssv('--panel', '#F2ECE1'); },
  get card() { return cssv('--card', '#FFFEFB'); }, get barra() { return cssv('--barra', '#9AA4AB'); },
};

function el(tag, attrs, kids) {
  const n = document.createElementNS(NS, tag);
  for (const k in (attrs || {})) n.setAttribute(k, attrs[k]);
  (kids || []).forEach((c) => n.appendChild(c instanceof Node ? c : document.createTextNode(String(c))));
  return n;
}
const fmt = (v, d = 1) => (v == null || isNaN(v) ? '–' : Number(v).toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: d }));
const niceMax = (v) => { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; };

const tip = (() => {
  let t;
  return {
    show(html, ev) { if (!t) { t = document.createElement('div'); t.className = 'tip'; t.setAttribute('role', 'tooltip'); document.body.appendChild(t); } t.innerHTML = html; t.style.opacity = 1; this.move(ev); },
    move(ev) { if (!t) return; const w = t.offsetWidth; let x = ev.clientX + 14, y = ev.clientY - 12 - t.offsetHeight; if (x + w > innerWidth - 8) x = ev.clientX - w - 14; if (y < 8) y = ev.clientY + 16; t.style.left = x + 'px'; t.style.top = y + 'px'; },
    hide() { if (t) t.style.opacity = 0; },
  };
})();

function axes(svg, o) {
  const { W, H, l, r, t, b, yMax, ticks = 4, yFmt = (v) => fmt(v, 1), yLabel } = o;
  for (let i = 0; i <= ticks; i++) {
    const v = (yMax * i) / ticks, y = t + (H - t - b) * (1 - i / ticks);
    svg.appendChild(el('line', { x1: l, x2: W - r, y1: y, y2: y, stroke: C.hair, 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: l - 8, y: y + 4, 'text-anchor': 'end', 'font-size': 12, fill: C.gray }, [yFmt(v)]));
  }
  if (yLabel) svg.appendChild(el('text', { x: l, y: t - 10, 'font-size': 12, fill: C.gray, 'font-weight': 600 }, [yLabel]));
}

/* Lineas con banda opcional y cursor que muestra todos los valores del punto. */
function lineChart(host, o) {
  const W = 760, H = o.height || 320, l = 46, r = 16, t = 26, b = 38;
  const n = o.labels.length;
  const all = [];
  o.series.forEach((s) => s.values.forEach((v) => v != null && all.push(v)));
  if (o.band) o.band.hi.forEach((v) => v != null && all.push(v));
  const yMax = o.yMax || niceMax(Math.max(...all, 1) * 1.05);
  const X = (i) => l + ((W - l - r) * i) / Math.max(1, n - 1), Y = (v) => t + (H - t - b) * (1 - v / yMax);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.aria || 'Grafica de lineas' });
  axes(svg, { W, H, l, r, t, b, yMax, yFmt: o.yFmt, yLabel: o.yLabel });
  const step = o.xEvery || Math.ceil(n / 8);
  o.labels.forEach((lab, i) => { if (i % step === 0) svg.appendChild(el('text', { x: X(i), y: H - 12, 'text-anchor': 'middle', 'font-size': 12, fill: C.gray }, [lab])); });
  if (o.band) {
    const up = [], dn = [];
    o.band.hi.forEach((v, i) => { if (v != null) { up.push(`${X(i)},${Y(v)}`); dn.unshift(`${X(i)},${Y(o.band.lo[i])}`); } });
    svg.appendChild(el('polygon', { points: up.concat(dn).join(' '), fill: C.band, opacity: 0.55 }));
  }
  (o.marks || []).forEach((m) => {
    svg.appendChild(el('line', { x1: X(m.i), x2: X(m.i), y1: t, y2: H - b, stroke: C.mute, 'stroke-dasharray': '4 4' }));
    svg.appendChild(el('text', { x: X(m.i) + 6, y: t + 12, 'font-size': 12, fill: C.gray }, [m.text]));
  });
  o.series.forEach((s) => {
    const pts = s.values.map((v, i) => (v == null ? null : `${X(i)},${Y(v)}`)).filter(Boolean).join(' ');
    svg.appendChild(el('polyline', { points: pts, fill: 'none', stroke: s.color, 'stroke-width': s.width || 3, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'stroke-dasharray': s.dash || '' }));
    if (s.dots) s.values.forEach((v, i) => v != null && svg.appendChild(el('circle', { cx: X(i), cy: Y(v), r: 4, fill: C.card, stroke: s.color, 'stroke-width': 2.5 })));
  });
  const cur = el('line', { y1: t, y2: H - b, stroke: C.ink, 'stroke-width': 1, opacity: 0 });
  const hit = el('rect', { x: l, y: t, width: W - l - r, height: H - t - b, fill: 'transparent', tabindex: 0 });
  svg.appendChild(cur); svg.appendChild(hit);
  const show = (i, ev) => {
    i = Math.max(0, Math.min(n - 1, i));
    cur.setAttribute('x1', X(i)); cur.setAttribute('x2', X(i)); cur.setAttribute('opacity', 0.5);
    let html = `<b>${o.tipTitle ? o.tipTitle(i) : o.labels[i]}</b>`;
    o.series.forEach((s) => { if (s.values[i] != null) html += `<br><span style="color:${s.color === C.ink ? '#fff' : s.color}">●</span> ${s.name}: ${fmt(s.values[i], o.tipDec ?? 1)}`; });
    if (o.band && o.band.hi[i] != null) html += `<br>Rango probable: ${fmt(o.band.lo[i], 0)} a ${fmt(o.band.hi[i], 0)}`;
    tip.show(html, ev);
  };
  hit.addEventListener('mousemove', (ev) => { const bx = svg.getBoundingClientRect(); const i = Math.round(((ev.clientX - bx.left) / bx.width * W - l) / (W - l - r) * (n - 1)); show(i, ev); });
  hit.addEventListener('mouseleave', () => { cur.setAttribute('opacity', 0); tip.hide(); });
  hit.addEventListener('focus', () => { const bx = svg.getBoundingClientRect(); show(0, { clientX: bx.left + 40, clientY: bx.top + 40 }); });
  host.innerHTML = '';
  host.appendChild(svg);
}

/* Barras agrupadas (modelos frente a referencias) con intervalo opcional. */
function groupedBars(host, o) {
  const W = 760, H = o.height || 320, l = 46, r = 12, t = 26, b = 56;
  const yMax = o.yMax || 1;
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.aria || 'Grafica de barras' });
  axes(svg, { W, H, l, r, t, b, yMax, yFmt: o.yFmt || ((v) => fmt(v * 100, 0) + ' %'), yLabel: o.yLabel });
  const gw = (W - l - r) / o.groups.length;
  const Y = (v) => t + (H - t - b) * (1 - v / yMax);
  o.groups.forEach((g, gi) => {
    const bw = Math.min(46, (gw - 22) / g.bars.length);
    const x0 = l + gi * gw + (gw - bw * g.bars.length) / 2;
    g.bars.forEach((bar, bi) => {
      const x = x0 + bi * bw, y = Y(bar.value);
      const rect = el('rect', { x: x + 2, y, width: bw - 4, height: Math.max(0, H - b - y), rx: 5, fill: bar.color, tabindex: 0, 'aria-label': `${g.label}, ${bar.name}: ${fmt(bar.value * 100, 1)} por ciento` });
      const html = `<b>${g.label}</b><br>${bar.name}: ${fmt(bar.value * 100, 1)} %` + (bar.note ? `<br>${bar.note}` : '');
      rect.addEventListener('mousemove', (ev) => tip.show(html, ev)); rect.addEventListener('mouseleave', () => tip.hide());
      rect.addEventListener('focus', () => { const bx = rect.getBoundingClientRect(); tip.show(html, { clientX: bx.left + bx.width / 2, clientY: bx.top }); }); rect.addEventListener('blur', () => tip.hide());
      svg.appendChild(rect);
      svg.appendChild(el('text', { x: x + bw / 2, y: y - 6, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 700, fill: C.ink }, [fmt(bar.value * 100, 0)]));
    });
    svg.appendChild(el('text', { x: l + gi * gw + gw / 2, y: H - 30, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 700, fill: C.ink }, [g.label]));
  });
  if (o.line) {
    svg.appendChild(el('line', { x1: l, x2: W - r, y1: Y(o.line.value), y2: Y(o.line.value), stroke: C.gray, 'stroke-width': 2, 'stroke-dasharray': '7 5' }));
    svg.appendChild(el('text', { x: W - r, y: Y(o.line.value) - 7, 'text-anchor': 'end', 'font-size': 12, 'font-weight': 700, fill: C.gray }, [o.line.label]));
  }
  host.innerHTML = '';
  host.appendChild(svg);
}

/* Personal necesario por hora frente a la dotacion fija. */
function staffChart(host, o) {
  const W = 760, H = 300, l = 46, r = 16, t = 26, b = 38;
  const yMax = Math.max(4, ...o.horas.map((h) => h.personal_necesario), o.dotacion) + 1;
  const bw = (W - l - r) / 24;
  const Y = (v) => t + (H - t - b) * (1 - v / yMax);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Personal necesario por hora frente a la dotacion fija' });
  axes(svg, { W, H, l, r, t, b, yMax, ticks: Math.min(yMax, 6), yFmt: (v) => fmt(v, 0), yLabel: 'personas' });
  o.horas.forEach((h, i) => {
    const falta = h.personal_necesario > o.dotacion;
    const rect = el('rect', { x: l + i * bw + 2, y: Y(h.personal_necesario), width: bw - 4, height: H - b - Y(h.personal_necesario), rx: 3, fill: falta ? C.coral : C.barra });
    const html = `<b>${String(i).padStart(2, '0')}:00</b><br>Llegadas esperadas: ${fmt(h.llegadas_esperadas, 1)}<br>Personal necesario: ${h.personal_necesario}<br>Espera con ${o.dotacion} personas: ${h.saturada ? 'saturada' : fmt(h.espera_con_dotacion_min, 0) + ' min'}`;
    rect.addEventListener('mousemove', (ev) => tip.show(html, ev)); rect.addEventListener('mouseleave', () => tip.hide());
    svg.appendChild(rect);
    if (i % 3 === 0) svg.appendChild(el('text', { x: l + i * bw + bw / 2, y: H - 12, 'text-anchor': 'middle', 'font-size': 12, fill: C.gray }, [String(i).padStart(2, '0')]));
  });
  svg.appendChild(el('line', { x1: l, x2: W - r, y1: Y(o.dotacion), y2: Y(o.dotacion), stroke: C.ink, 'stroke-width': 3 }));
  svg.appendChild(el('text', { x: l + 6, y: Y(o.dotacion) - 7, 'font-size': 12, 'font-weight': 700, fill: C.ink }, [`Dotación actual: ${o.dotacion}`]));
  host.innerHTML = '';
  host.appendChild(svg);
}

/* Espera media segun la carga de la hora, con intervalo de confianza. */
function curvaEspera(host, o) {
  const W = 760, H = 300, l = 46, r = 16, t = 26, b = 50;
  const pts = o.curva;
  const yMax = niceMax(Math.max(...pts.map((p) => p.ic95[1]), 10) * 1.05);
  const bw = (W - l - r) / pts.length;
  const Y = (v) => t + (H - t - b) * (1 - v / yMax);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Espera media segun llegadas en la hora' });
  axes(svg, { W, H, l, r, t, b, yMax, yFmt: (v) => fmt(v, 0), yLabel: 'minutos de espera (media)' });
  const line = [];
  pts.forEach((p, i) => {
    const x = l + i * bw + bw / 2, y = Y(p.espera_media_min);
    line.push(`${x},${y}`);
    svg.appendChild(el('line', { x1: x, x2: x, y1: Y(p.ic95[0]), y2: Y(p.ic95[1]), stroke: o.color || C.coralD, 'stroke-width': 3, opacity: 0.45 }));
    const c = el('circle', { cx: x, cy: y, r: 7, fill: o.color || C.coralD, tabindex: 0, 'aria-label': `${p.llegadas_en_la_hora} llegadas: ${p.espera_media_min} minutos` });
    const html = `<b>${p.llegadas_en_la_hora} llegada(s) en la hora</b><br>Espera media: ${fmt(p.espera_media_min, 1)} min<br>IC 95 %: ${fmt(p.ic95[0], 0)} a ${fmt(p.ic95[1], 0)}<br>${fmt(p.horas, 0)} horas observadas`;
    c.addEventListener('mousemove', (ev) => tip.show(html, ev)); c.addEventListener('mouseleave', () => tip.hide());
    svg.appendChild(c);
    svg.appendChild(el('text', { x, y: H - 24, 'text-anchor': 'middle', 'font-size': 13, fill: C.ink, 'font-weight': 600 }, [p.llegadas_en_la_hora]));
  });
  svg.insertBefore(el('polyline', { points: line.join(' '), fill: 'none', stroke: o.color || C.coralD, 'stroke-width': 3 }), svg.children[svg.children.length - pts.length * 3]);
  svg.appendChild(el('text', { x: (W + l - r) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 12, fill: C.gray }, ['personas que llegaron en esa misma hora']));
  host.innerHTML = '';
  host.appendChild(svg);
}

/* Histograma simple. */
function histograma(host, o) {
  const W = 760, H = 260, l = 46, r = 12, t = 26, b = 40;
  const yMax = niceMax(Math.max(...o.bins.map((x) => x.n)) * 1.05);
  const bw = (W - l - r) / o.bins.length;
  const Y = (v) => t + (H - t - b) * (1 - v / yMax);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Distribucion de la espera' });
  axes(svg, { W, H, l, r, t, b, yMax, yFmt: (v) => fmt(v / 1000, 0) + ' mil', yLabel: 'atenciones' });
  o.bins.forEach((x, i) => {
    const hot = x.desde >= (o.marca ?? 1e9);
    const rect = el('rect', { x: l + i * bw + 1, y: Y(x.n), width: bw - 2, height: H - b - Y(x.n), fill: hot ? C.coral : C.barra, rx: 2 });
    const html = `<b>${x.desde} a ${x.desde + 15} min</b><br>${fmt(x.n, 0)} atenciones`;
    rect.addEventListener('mousemove', (ev) => tip.show(html, ev)); rect.addEventListener('mouseleave', () => tip.hide());
    svg.appendChild(rect);
    if (i % 2 === 0) svg.appendChild(el('text', { x: l + i * bw + bw / 2, y: H - 20, 'text-anchor': 'middle', 'font-size': 11, fill: C.gray }, [x.desde]));
  });
  svg.appendChild(el('text', { x: (W + l - r) / 2, y: H - 3, 'text-anchor': 'middle', 'font-size': 12, fill: C.gray }, ['minutos entre que llega y lo atienden']));
  host.innerHTML = '';
  host.appendChild(svg);
}

window.Charts = { lineChart, groupedBars, staffChart, curvaEspera, histograma, C, fmt, tip, el };
