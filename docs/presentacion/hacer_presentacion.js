// Presentacion de la entrega final de VitalData (Data Thinking, UAO).
// Las cifras salen de datos.json, que se genera desde la misma base de la aplicacion.
const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');
const SKILL = process.env.SKILL_DIR;
const { applyTheme } = require(path.join(SKILL, 'scripts', 'apply_theme.js'));

const D = JSON.parse(fs.readFileSync(path.join(__dirname, 'datos.json'), 'utf-8'));
const IMG = (n) => path.join(__dirname, 'img', n);
const ratio = (n) => { const b = fs.readFileSync(IMG(n)); return b.readUInt32BE(20) / b.readUInt32BE(16); }; // alto / ancho del PNG
const SALIDA = path.join(__dirname, 'VitalData_Entrega_Final.pptx');
const fmt = (v, d = 0) => Number(v).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v, d = 0) => fmt(v * 100, d) + ' %';

const THEME = {
  name: 'VitalData',
  headFontFace: 'Cambria',
  bodyFontFace: 'Calibri',
  colors: { dk1: '22282D', lt1: 'FFFFFF', dk2: '5E6770', lt2: 'F3F4F5', accent1: 'FF4438', accent2: 'E0A100', accent3: '2E9E6B', accent4: '3B6FD4', accent5: '8A939B', accent6: '8A4FD4', hlink: 'D9382B', folHlink: '5E6770' },
};
const HEX = { ink: '22282D', gray: '5E6770', mute: '8A939B', coral: 'FF4438', coralD: 'D9382B', coralT: 'FFE7E4', gold: 'E0A100', ok: '2E9E6B', blue: '3B6FD4', panel: 'F3F4F5', line: 'E3E5E8', white: 'FFFFFF' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 x 5.625 pulgadas
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'VitalData · Entrega final';
pres.author = 'Sebastian Lozano y Julian David Cuellar';
pres.company = 'Universidad Autónoma de Occidente';
const C = pres.SchemeColor;

// ---------------------------------------------------------------- plantillas (layouts)
pres.defineSlideMaster({
  title: 'TITULO', background: { color: HEX.ink },
  objects: [],
  slideNumber: undefined,
});
pres.defineSlideMaster({
  title: 'CONTENIDO', background: { color: HEX.white },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.3, w: 9, h: 0.85, fontFace: 'Cambria', fontSize: 26, bold: true, color: C.text1, valign: 'top', align: 'left', margin: 0 }, text: '' } },
    { text: { text: 'VitalData · Data Thinking · Universidad Autónoma de Occidente', options: { x: 0.5, y: 5.25, w: 6, h: 0.25, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 9.0, y: 5.25, w: 0.5, h: 0.25, fontSize: 10, color: C.accent5, align: 'right', margin: 0 },
});
pres.defineSlideMaster({ title: 'CIERRE', background: { color: HEX.ink }, objects: [] });

const note = (s, t) => s.addNotes(t);

function titulo(s, texto) { s.addText(texto, { placeholder: 'title' }); }

function tarjeta(s, x, y, w, h, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: o.fill || C.background2 }, line: { color: o.line || HEX.line, width: o.line ? 1 : 0.5 }, objectName: o.name || 'tarjeta' });
}
function cifra(s, x, y, w, numero, rotulo, o = {}) {
  s.addText(numero, { x, y, w, h: 0.7, fontFace: 'Cambria', fontSize: o.size || 36, bold: true, color: o.color || C.accent1, margin: 0, valign: 'bottom', isTextBox: true, objectName: 'cifra' });
  s.addText(rotulo, { x, y: y + 0.72, w, h: o.hr || 0.55, fontSize: 12, color: o.rc || C.text2, margin: 0, valign: 'top', isTextBox: true, objectName: 'rotulo' });
}
function circulo(s, x, y, n, color) {
  s.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: color || C.accent1 }, line: { color: color || C.accent1 }, objectName: 'numero' });
  s.addText(String(n), { x, y, w: 0.42, h: 0.42, align: 'center', valign: 'middle', fontSize: 14, bold: true, color: C.background1, margin: 0, isTextBox: true });
}
function caja(s, x, y, w, h, t1, t2, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.07, fill: { color: o.fill || C.background2 }, line: { color: o.line || HEX.line, width: 1 }, objectName: 'caja' });
  s.addText([{ text: t1, options: { bold: true, fontSize: o.f1 || 12, color: o.c1 || C.text1, breakLine: !!t2 } }].concat(t2 ? [{ text: t2, options: { fontSize: o.f2 || 10, color: o.c2 || C.text2 } }] : []),
    { x, y, w, h, align: 'center', valign: 'middle', margin: 0.04, isTextBox: true });
}
function flecha(s, x1, y1, x2, y2, color) {
  s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1), flipH: x2 < x1, flipV: y2 < y1, line: { color: color || HEX.mute, width: 1.5, endArrowType: 'triangle' }, objectName: 'flecha' });
}
const estiloGrafica = () => ({
  catAxisLabelColor: HEX.gray, valAxisLabelColor: HEX.gray, catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  valGridLine: { color: HEX.line, size: 0.5 }, catGridLine: { style: 'none' }, dataLabelFontFace: '+mn-lt', dataLabelFontSize: 11, dataLabelColor: HEX.ink,
  legendFontFace: '+mn-lt', legendFontSize: 11, legendColor: HEX.gray, titleFontFace: '+mn-lt', titleColor: HEX.ink, titleFontSize: 12,
});

// ================================================================ 1. PORTADA
pres.addSection({ title: 'Inicio' });
let s = pres.addSlide({ masterName: 'TITULO', sectionTitle: 'Inicio' });
s.addText('ENTREGA FINAL · DATA THINKING · UNIVERSIDAD AUTÓNOMA DE OCCIDENTE', { x: 0.6, y: 0.55, w: 6, h: 0.3, fontSize: 11, bold: true, color: 'FF8A80', charSpacing: 2, margin: 0, isTextBox: true });
s.addText('VitalData', { x: 0.6, y: 1.05, w: 6, h: 0.9, fontFace: 'Cambria', fontSize: 54, bold: true, color: C.background1, margin: 0, isTextBox: true });
s.addText('Saber cuántos van a llegar a urgencias antes de que lleguen', { x: 0.6, y: 2.05, w: 5.6, h: 1.1, fontFace: 'Cambria', fontSize: 24, color: 'FFD4CF', margin: 0, valign: 'top', isTextBox: true });
s.addText('Pronóstico por hora, personal recomendado y orientación al paciente, con datos abiertos reales de tres centros de salud de Pasto.', { x: 0.6, y: 3.3, w: 5.4, h: 0.8, fontSize: 14, color: 'C8CFD4', margin: 0, valign: 'top', isTextBox: true });
s.addText('Sebastian Lozano · Julian David Cuellar', { x: 0.6, y: 4.75, w: 5.6, h: 0.3, fontSize: 13, bold: true, color: C.background1, margin: 0, isTextBox: true });
s.addImage({ path: IMG('sitio_movil.png'), x: 6.95, y: 0.55, w: 2.2, h: 2.2 * ratio('sitio_movil.png'), altText: 'El sitio VitalData en un teléfono: pregunta qué sientes y orienta', objectName: 'captura movil' });
note(s, 'Buenos días. Somos Sebastian Lozano y Julian David Cuellar y presentamos VitalData. Es un sistema que le dice a un hospital cuántos pacientes van a llegar a urgencias cada hora y cuántas personas hacen falta, y que le dice al paciente a qué urgencia le conviene ir. Lo que van a ver hoy no es una maqueta: es una aplicación que funciona con datos reales de tres centros de salud de Pasto.');

// ================================================================ 2. PROBLEMA
pres.addSection({ title: 'Problema' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema' });
titulo(s, 'Las urgencias se planean sin mirar hacia adelante');
cifra(s, 0.5, 1.45, 2.7, '79.521', 'atenciones reales de urgencias analizadas, 2020 a 2022');
cifra(s, 0.5, 2.85, 2.7, '39 min', 'es lo que espera la mitad de los pacientes');
cifra(s, 0.5, 4.2, 2.7, `${D.mas2h_txt} %`, 'espera más de dos horas', { size: 36 });
tarjeta(s, 3.45, 1.4, 6.05, 3.7, { name: 'tarjeta grafica' });
const bins = D.hist;
s.addChart(pres.charts.BAR, [{ name: 'Atenciones', labels: bins.map((b) => String(b.desde)), values: bins.map((b) => b.n) }], {
  x: 3.55, y: 1.5, w: 5.85, h: 3.5, barDir: 'col', barGapWidthPct: 20,
  chartColors: bins.map((b) => (b.desde >= 120 ? HEX.coral : HEX.mute)),
  showTitle: true, title: 'Minutos entre que el paciente llega y lo atienden (en rojo, más de dos horas)', showLegend: false, showValue: false,
  catAxisLabelFrequency: 2, showCatAxisTitle: true, catAxisTitle: 'minutos', catAxisTitleColor: HEX.gray, catAxisTitleFontSize: 10, valAxisLabelFormatCode: '#,##0', ...estiloGrafica(),
});
note(s, 'Escogimos este problema porque cualquier colombiano lo ha vivido: la sala de urgencias llena. Los datos para anticiparlo ya existen, porque cada atención guarda la hora de llegada, el triage y la hora en que lo atendieron, pero casi siempre se usan para facturar. En las casi ochenta mil atenciones que analizamos, la mitad espera menos de cuarenta minutos, pero hay un grupo que espera más de dos horas.');

// ================================================================ 3. DISEÑO ESTRATÉGICO
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Problema' });
titulo(s, 'Dos usuarios y cuatro niveles de prototipo');
const usuarios = [
  ['Quien coordina', 'Organiza turnos sin saber cuántos llegarán. Necesita un pronóstico por hora y el personal que hace falta.', HEX.coral],
  ['Quien espera', 'No sabe cuánto va a tardar ni si hay otra urgencia más vacía cerca. Necesita orientación antes de salir de casa.', HEX.blue],
];
usuarios.forEach(([t, d, col], i) => {
  const y = 1.45 + i * 1.7;
  tarjeta(s, 0.5, y, 3.9, 1.5);
  s.addShape(pres.shapes.OVAL, { x: 0.7, y: y + 0.2, w: 0.55, h: 0.55, fill: { color: col }, line: { color: col }, objectName: 'icono usuario' });
  s.addText(t, { x: 1.4, y: y + 0.18, w: 2.9, h: 0.4, fontFace: 'Cambria', fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: 0.7, y: y + 0.8, w: 3.55, h: 0.65, fontSize: 12, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
});
s.addText('Cómo llegamos al producto', { x: 4.75, y: 1.4, w: 4.7, h: 0.3, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
const pasos = [['Lo-Fi', 'boceto a lápiz de la pantalla del coordinador', 'lofi.png'], ['Me-Fi', 'maqueta con jerarquía de color y datos de ejemplo', 'mefi.png']];
pasos.forEach(([t, d, im], i) => {
  const x = 4.75 + i * 2.4;
  s.addImage({ path: IMG(im), x, y: 1.8, w: 2.3, h: 2.3 * 487 / 754, altText: `Prototipo ${t}: ${d}`, objectName: 'prototipo ' + t });
  s.addText([{ text: t + '. ', options: { bold: true, color: C.text1 } }, { text: d, options: { color: C.text2 } }], { x, y: 3.35, w: 2.3, h: 0.55, fontSize: 11, margin: 0, valign: 'top', isTextBox: true });
});
s.addImage({ path: IMG('sitio_inicio.png'), x: 4.75, y: 3.95, w: 1.7, h: 1.7 * ratio('sitio_inicio.png'), altText: 'Producto funcional: el sitio para pacientes con datos reales', objectName: 'producto' });
s.addText([{ text: 'Producto funcional. ', options: { bold: true, color: C.text1 } }, { text: 'El sitio que verán hoy: asistente, API, base de datos y datos reales.', options: { color: C.text2 } }], { x: 6.9, y: 4.0, w: 2.6, h: 1.0, fontSize: 11, margin: 0, valign: 'top', isTextBox: true });
note(s, 'Diseñamos para dos personas. Quien coordina el servicio necesita saber cuántos llegan y con cuánto personal responder. Quien espera necesita saber si le conviene ir ahora o a otro centro. Con siete técnicas de ideación escogimos el concepto y lo fuimos mejorando: boceto a lápiz, maqueta con color y por último el producto funcional que vamos a demostrar.');

// ================================================================ 4. DATOS
pres.addSection({ title: 'Datos y backend' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Datos y backend' });
titulo(s, 'Datos abiertos y reales, con cada fila contada');
const fuentes = [
  ['E.S.E. Pasto Salud', 'Clasificación en triage de urgencias', 'datos.gov.co · vt5n-eu2r', '89.453 filas, 2020 a 2022'],
  ['IDEAM', 'Precipitación y temperatura de la estación de Pasto', 'datos.gov.co · s54a-sgyg y sbwg-7ju4', 'Lluvia cada 10 minutos'],
  ['SECOP II y TRM', 'Precios de proveedores y tasa de cambio para el modelo financiero', 'datos.gov.co', 'Consultados el 9 de noviembre'],
];
fuentes.forEach(([t, d, f, n], i) => {
  const x = 0.5 + i * 3.05;
  tarjeta(s, x, 1.4, 2.9, 1.95);
  s.addText(t, { x: x + 0.18, y: 1.5, w: 2.55, h: 0.35, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: x + 0.18, y: 1.88, w: 2.55, h: 0.6, fontSize: 12, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
  s.addText(f, { x: x + 0.18, y: 2.55, w: 2.6, h: 0.3, fontSize: 10, color: HEX.coralD, bold: true, margin: 0, isTextBox: true });
  s.addText(n, { x: x + 0.18, y: 2.85, w: 2.6, h: 0.3, fontSize: 11, color: C.text2, margin: 0, isTextBox: true });
});
tarjeta(s, 0.5, 3.6, 9.0, 1.45, { fill: C.text1, line: HEX.ink, name: 'conciliacion' });
s.addText('LA CARGA CONCILIA', { x: 0.75, y: 3.7, w: 4, h: 0.28, fontSize: 10, bold: true, color: 'FF8A80', charSpacing: 2, margin: 0, isTextBox: true });
[['89.453', 'bajaron de la API'], ['− 9.932', 'duplicadas'], ['− 0', 'rechazadas'], ['= 79.521', 'quedaron en la base']].forEach(([n, r], i) => {
  const x = 0.75 + i * 2.2;
  s.addText(n, { x, y: 4.0, w: 2.0, h: 0.55, fontFace: 'Cambria', fontSize: 26, bold: true, color: i === 3 ? '6FE3A8' : C.background1, margin: 0, isTextBox: true });
  s.addText(r, { x, y: 4.58, w: 2.0, h: 0.3, fontSize: 12, color: 'C8CFD4', margin: 0, isTextBox: true });
});
note(s, 'No inventamos ningún dato. Bajamos las atenciones de urgencias de la E.S.E. Pasto Salud y el clima del IDEAM directamente de datos.gov.co. En cada carga hacemos la cuenta: lo que bajó, menos las filas duplicadas y las rechazadas, tiene que ser igual a lo que quedó en la base. Hoy esa cuenta cuadra.');

// ================================================================ 5. ARQUITECTURA
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Datos y backend' });
titulo(s, 'Un solo comando levanta todo el sistema');
const bx = [['datos.gov.co', 'API Socrata'], ['ETL', 'extraer, validar, cargar'], ['PostgreSQL 16', 'esquema vd'], ['Modelos', 'Poisson y Erlang C'], ['FastAPI', '14 endpoints'], ['Aplicación', 'tablero y asistente']];
const colores = [HEX.blue, HEX.coral, HEX.ok, HEX.gold, HEX.coralD, HEX.ink];
bx.forEach(([t, d], i) => {
  const x = 0.5 + i * 1.55;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.35, w: 1.3, h: 1.0, rectRadius: 0.08, fill: { color: colores[i] }, line: { color: colores[i] }, objectName: 'bloque ' + t });
  s.addText([{ text: t, options: { bold: true, fontSize: 12, color: C.background1, breakLine: true } }, { text: d, options: { fontSize: 10, color: C.background1 } }], { x, y: 2.35, w: 1.3, h: 1.0, align: 'center', valign: 'middle', margin: 0.04, isTextBox: true });
  if (i < bx.length - 1) flecha(s, x + 1.32, 2.85, x + 1.53, 2.85);
});
// airflow arriba
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.05, y: 1.4, w: 4.55, h: 0.6, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: HEX.mute, width: 1, dashType: 'dash' }, objectName: 'airflow' });
s.addText([{ text: 'Apache Airflow', options: { bold: true, color: C.text1, fontSize: 12 } }, { text: '  orquesta 7 tareas todos los días a las 5:00', options: { color: C.text2, fontSize: 11 } }], { x: 2.05, y: 1.4, w: 4.55, h: 0.6, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
flecha(s, 4.3, 2.02, 4.3, 2.33);
// pytest abajo
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.05, y: 3.7, w: 4.55, h: 0.6, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: HEX.mute, width: 1, dashType: 'dash' }, objectName: 'pytest' });
s.addText([{ text: 'pytest', options: { bold: true, color: C.text1, fontSize: 12 } }, { text: '  293 pruebas sobre ETL, modelo, base y API', options: { color: C.text2, fontSize: 11 } }], { x: 2.05, y: 3.7, w: 4.55, h: 0.6, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
flecha(s, 4.3, 3.68, 4.3, 3.37);
s.addText('Todo corre en contenedores con docker compose up: base de datos, API con la página y Airflow.', { x: 0.5, y: 4.55, w: 8.9, h: 0.5, fontSize: 13, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
note(s, 'Así está armado. Los datos entran por un ETL, se guardan en PostgreSQL, los modelos aprenden de ahí y publican sus pronósticos, y una API en FastAPI los entrega a la aplicación web. Airflow ejecuta todo el flujo cada día y las pruebas automáticas cubren cada parte. Todo se levanta con un solo comando de Docker.');

// ================================================================ 6. ETL
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Datos y backend' });
titulo(s, 'El ETL se puede repetir sin duplicar ni perder filas');
const etl = [
  ['Extraer', 'Reintentos con espera creciente. El token de la API va en una variable de entorno, nunca en el código.'],
  ['Validar', 'Reglas explícitas. Cada fila lleva una huella md5 para detectar duplicados; lo que se rechaza se guarda con su motivo.'],
  ['Cargar', 'COPY a una tabla temporal y ON CONFLICT DO NOTHING: correr dos veces la misma carga deja la base igual.'],
  ['Auditar', 'Cada corrida deja su registro, también las que fallan: filas, duplicadas, rechazadas y tiempo.'],
];
etl.forEach(([t, d], i) => {
  const y = 1.4 + i * 0.9;
  circulo(s, 0.5, y + 0.05, i + 1);
  s.addText(t, { x: 1.05, y, w: 1.3, h: 0.35, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: 1.05, y: y + 0.33, w: 3.7, h: 0.55, fontSize: 11, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
});
tarjeta(s, 5.0, 1.4, 4.5, 3.65, { name: 'tarjeta serie' });
const meses = []; for (let y = 2020; y <= 2022; y++) for (let m = 1; m <= 12; m++) { const k = `${y}-${String(m).padStart(2, '0')}`; if (k <= '2022-09') meses.push(k); }
s.addChart(pres.charts.LINE, [{ name: 'Llegadas por mes', labels: meses.map((k) => k.slice(2)), values: meses.map((k) => D.mensual[k] || 0) }], {
  x: 5.05, y: 1.45, w: 4.4, h: 2.55, chartColors: [HEX.coral], lineSize: 2.5, lineDataSymbol: 'none', showLegend: false, showTitle: true,
  title: 'Llegadas por mes, Hospital Local Civil', catAxisLabelFrequency: 4, valAxisLabelFormatCode: '#,##0', ...estiloGrafica(),
});
s.addText([
  { text: 'Dos hallazgos que condicionan el modelo. ', options: { bold: true, color: C.text1 } },
  { text: 'Un año sin registros (abril de 2020 a marzo de 2021): entrenamos solo desde abril de 2021. Y un salto en mayo de 2022: usamos el nivel de la última semana, no un promedio de toda la historia.', options: { color: C.text2 } },
], { x: 5.2, y: 4.0, w: 4.15, h: 1.0, fontSize: 11, margin: 0, valign: 'top', isTextBox: true });
note(s, 'El ETL está pensado para fallar bien. Si se repite una carga no duplica nada, porque cada fila tiene una huella única. Todo lo que se rechaza queda guardado con su motivo. Al mirar las series descubrimos dos cosas que cambiaron el modelo: la fuente no trae registros durante un año, y desde mayo de 2022 las llegadas casi se duplican. Por eso entrenamos solo con el periodo continuo y usamos el nivel reciente.');

// ================================================================ 7. POSTGRES
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Datos y backend' });
titulo(s, 'Una base con reglas propias y consultas medidas');
// estrella
const cx = 2.55, cy = 3.15;
caja(s, cx - 0.95, cy - 0.4, 1.9, 0.8, 'fact_atencion', '79.521 filas', { fill: HEX.coral, line: HEX.coral, c1: C.background1, c2: C.background1, f1: 13, f2: 11 });
[['dim_ips', 1.2, 1.5], ['dim_triage', 3.6, 1.5], ['dim_estacion', 0.65, 4.4]].forEach(([t, x, y]) => { caja(s, x, y, 1.45, 0.5, t, null, { f1: 11 }); });
caja(s, 3.55, 4.4, 1.5, 0.5, 'clima_diario', null, { f1: 11 });
flecha(s, 1.95, 2.0, 2.15, 2.75); flecha(s, 4.0, 2.0, 3.2, 2.75); flecha(s, 1.4, 4.4, 2.05, 3.55); flecha(s, 4.1, 4.4, 3.2, 3.55);
s.addText('Esquema en estrella con llaves foráneas', { x: 0.5, y: 1.35, w: 4.6, h: 0.3, fontSize: 11, color: C.text2, margin: 0, isTextBox: true });
s.addText([
  { text: 'Integridad en la base, no solo en el código', options: { bold: true, color: C.text1, breakLine: true } },
  { text: 'atención ≥ ingreso · espera entre 0 y 1.440 min · huella única', options: { color: C.text2, breakLine: true } },
  { text: 'Más tablas de auditoría (etl_run, dq_issue), de modelos y de usabilidad.', options: { color: C.text2 } },
], { x: 5.4, y: 1.4, w: 4.1, h: 1.1, fontSize: 11, margin: 0, valign: 'top', paraSpaceAfter: 4, isTextBox: true });
const cons = D.ev.ev_benchmark ? null : null;
tarjeta(s, 5.4, 2.55, 4.1, 2.5, { name: 'tarjeta indices' });
s.addChart(pres.charts.BAR, [
  { name: 'Sin índice', labels: ['Llegadas de una IPS en un mes', 'Espera típica por hora'], values: [3.14, 3.5] },
  { name: 'Con índice', labels: ['Llegadas de una IPS en un mes', 'Espera típica por hora'], values: [0.56, 2.4] },
], { x: 5.45, y: 2.6, w: 4.0, h: 2.4, barDir: 'bar', barGrouping: 'clustered', chartColors: [HEX.mute, HEX.coral], showLegend: true, legendPos: 'b', showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0.0 "ms"', valAxisHidden: true, valAxisMaxVal: 4.6, valAxisMinVal: 0, valGridLine: { style: 'none' }, showTitle: true, title: 'Tiempo de consulta (EXPLAIN ANALYZE)', catAxisLabelColor: HEX.gray, catAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 10, dataLabelFontFace: '+mn-lt', dataLabelFontSize: 10, dataLabelColor: HEX.ink, legendFontFace: '+mn-lt', legendFontSize: 10, legendColor: HEX.gray, titleFontFace: '+mn-lt', titleColor: HEX.ink, titleFontSize: 11, catGridLine: { style: 'none' } });
s.addText('El índice en (IPS, ingreso) hace la consulta del modelo 5,6 veces más rápida.', { x: 0.5, y: 5.0, w: 4.6, h: 0.25, fontSize: 10, color: C.text2, margin: 0, isTextBox: true });
note(s, 'La base es un esquema en estrella: una tabla de hechos con cada atención y tablas pequeñas para el centro, el nivel de triage y la estación del clima. Las reglas de calidad viven en la base: no se puede guardar una atención anterior a su ingreso ni una espera absurda. Medimos las consultas con EXPLAIN ANALYZE: el índice por centro y fecha hace la consulta que usa el modelo más de cinco veces más rápida.');

// ================================================================ 8. HALLAZGO
pres.addSection({ title: 'Modelo' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Modelo' });
titulo(s, 'Cuando llegan más, se espera más');
const cen = [['hospital_local_civil', 'Hospital Local Civil'], ['centro_hospital_la_rosa', 'Centro Hospital La Rosa'], ['cs_san_vicente', 'CS San Vicente']];
s.addChart(pres.charts.BAR, [
  { name: '1 llegada en la hora', labels: cen.map((c) => c[1]), values: cen.map((c) => D.espera[c[0]].a) },
  { name: '7 o más llegadas en la hora', labels: cen.map((c) => c[1]), values: cen.map((c) => D.espera[c[0]].z) },
], { x: 0.5, y: 1.4, w: 5.4, h: 3.7, barDir: 'col', barGapWidthPct: 60, chartColors: [HEX.mute, HEX.coral], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0', showLegend: true, legendPos: 'b', showTitle: true, title: 'Espera media en minutos', valAxisLabelFormatCode: '0', ...estiloGrafica() });
tarjeta(s, 6.15, 1.4, 3.35, 3.7, { name: 'tarjeta prueba' });
s.addText('La prueba', { x: 6.35, y: 1.5, w: 3, h: 0.3, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
const cors = cen.map((c) => D.espera[c[0]].cor.spearman);
s.addText([
  { text: `Correlación de Spearman entre llegadas y espera: de ${fmt(Math.min(...cors), 2)} a ${fmt(Math.max(...cors), 2)} según el centro.`, options: { breakLine: true } },
  { text: 'Prueba de permutación: p menor que 0,001 en los tres. No depende de una distribución supuesta.', options: { breakLine: true } },
  { text: 'Además, el triage IV y V espera una mediana de 79 a 82 minutos; el triage III, 37. Por eso el asistente orienta los casos leves.', options: {} },
], { x: 6.35, y: 1.85, w: 3.0, h: 2.2, fontSize: 11, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
s.addText('La relación es moderada: la espera también depende del triage y del personal, que la fuente no trae.', { x: 6.35, y: 4.2, w: 3.0, h: 0.8, fontSize: 11, italic: true, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
note(s, 'Nuestra hipótesis era que cuando llegan más pacientes en una hora, la espera sube. Los datos lo confirman en los tres centros y lo comprobamos con una prueba de permutación, que no depende de supuestos. Somos cuidadosos: la relación es moderada, porque la espera también depende del triage y del personal, y la fuente no trae el personal por turno.');

// ================================================================ 9. MODELO
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Modelo' });
titulo(s, 'Un modelo sencillo, medido contra rivales justos');
s.addText('Qué hace', { x: 0.5, y: 1.4, w: 4.3, h: 0.3, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
s.addText([
  { text: 'Regresión de Poisson por hora con el perfil del tipo de día, el nivel de la última semana, la lluvia y la temperatura.', options: { bullet: true, breakLine: true } },
  { text: 'Rango probable del 80 % con binomial negativa.', options: { bullet: true, breakLine: true } },
  { text: 'Teoría de colas (Erlang C) convierte el pronóstico en personal necesario para una espera objetivo.', options: { bullet: true } },
], { x: 0.5, y: 1.75, w: 4.3, h: 1.9, fontSize: 12, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
s.addText('Cómo lo comprobamos', { x: 0.5, y: 3.5, w: 4.3, h: 0.3, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
s.addText('Una librería distinta (statsmodels) da el mismo ajuste. Es una verificación cruzada que corre en las pruebas.', { x: 0.5, y: 3.85, w: 4.3, h: 0.9, fontSize: 12, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
tarjeta(s, 5.1, 1.4, 4.4, 3.65, { name: 'tarjeta evaluacion' });
s.addText('La evaluación', { x: 5.3, y: 1.5, w: 4, h: 0.3, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
[
  ['1', 'Ventana que avanza: cada semana se reentrena solo con lo que ya había pasado.'],
  ['2', 'Los parámetros se eligen en una ventana de validación; 53 días de prueba nunca se usaron para escoger nada.'],
  ['3', 'Tres referencias sin IA: media de 4 semanas, misma hora de la semana anterior y nivel de la última semana.'],
  ['4', 'Intervalos de confianza por bootstrap sobre los días.'],
].forEach(([n, t], i) => {
  const y = 1.9 + i * 0.75;
  circulo(s, 5.3, y, n);
  s.addText(t, { x: 5.85, y: y - 0.04, w: 3.5, h: 0.7, fontSize: 11, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
});
note(s, 'El modelo es deliberadamente sencillo y por eso se puede explicar. Pronosticamos con una regresión de Poisson por hora y convertimos el pronóstico en personal con teoría de colas. Lo importante es cómo lo evaluamos: reentrenamos semana a semana solo con el pasado, escogimos los parámetros en una ventana aparte y lo comparamos con tres referencias sin inteligencia artificial.');

// ================================================================ 10. RESULTADOS
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Modelo' });
titulo(s, 'Le ganamos a las referencias, pero sin llegar al 85 %');
const orden = ['HOSPITAL LOCAL CIVIL', 'CENTRO HOSPITAL LA ROSA', 'CS SAN VICENTE'];
const nom = { 'HOSPITAL LOCAL CIVIL': 'Hospital Local Civil', 'CENTRO HOSPITAL LA ROSA': 'Centro Hospital La Rosa', 'CS SAN VICENTE': 'CS San Vicente' };
const serie = (k) => orden.map((i) => Math.round(D.metricas[i]['3h'][k] * 1000) / 10);
s.addChart(pres.charts.BAR, [
  { name: 'Nivel de la última semana', labels: orden.map((o) => nom[o]), values: serie('b_nivel') },
  { name: 'Misma hora, semana anterior', labels: orden.map((o) => nom[o]), values: serie('b_semana_anterior') },
  { name: 'Media de 4 semanas', labels: orden.map((o) => nom[o]), values: serie('b_media_4s') },
  { name: 'VitalData', labels: orden.map((o) => nom[o]), values: serie('vitaldata') },
], { x: 0.5, y: 1.35, w: 5.7, h: 3.75, barDir: 'col', barGapWidthPct: 40, chartColors: ['CBD2D7', 'A9B2B9', '7C8790', HEX.coral], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0', valAxisMaxVal: 100, valAxisMinVal: 0, valAxisLabelFormatCode: '0', showLegend: true, legendPos: 'b', showTitle: true, title: 'Precisión por franja de 3 horas, % (53 días de prueba)', ...estiloGrafica() });
const lc = D.vs3h['CENTRO HOSPITAL LA ROSA'], sv = D.vs3h['CS SAN VICENTE'], hl = D.vs3h['HOSPITAL LOCAL CIVIL'];
const pts = (v) => fmt(v.mejora_media * 100, 1);
const ic = (v) => `${fmt(v.ic95[0] * 100, 1)} a ${fmt(v.ic95[1] * 100, 1)}`;
tarjeta(s, 6.45, 1.4, 3.05, 3.7, { name: 'tarjeta lectura' });
s.addText([
  { text: 'Cómo leerlo', options: { fontFace: 'Cambria', bold: true, fontSize: 14, color: C.text1, breakLine: true } },
  { text: `Mejora clara en La Rosa (+${pts(lc)} puntos, IC 95 % ${ic(lc)}) y San Vicente (+${pts(sv)}, ${ic(sv)}).`, options: { breakLine: true } },
  { text: `En Hospital Local Civil la mejora es de ${pts(hl)} puntos y el intervalo incluye el cero.`, options: { breakLine: true } },
  { text: 'Por día no hay diferencia con la media de 4 semanas: todos rondan el 85 a 87 %.', options: { breakLine: true } },
  { text: 'La meta de 85 % por franja no se cumple; por día sí se alcanza.', options: { bold: true, color: HEX.coralD } },
], { x: 6.6, y: 1.5, w: 2.8, h: 3.5, fontSize: 11, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 5, isTextBox: true });
note(s, 'Este es el resultado y preferimos contarlo tal cual. En la franja de tres horas el modelo le gana a las tres referencias en los tres centros, con una mejora clara en La Rosa y San Vicente, y más modesta en el Hospital Local Civil. Por día no hay diferencia con la media de cuatro semanas. La meta que nos pusimos, 85 por ciento por franja, no se cumple: estamos entre 70 y 74. Por día sí llegamos. Lo que sí aporta valor es traducir el pronóstico a personal y mostrar el rango probable, que cubre cerca del 90 por ciento de los casos.');

// ================================================================ 11. SITIO Y ASISTENTE
pres.addSection({ title: 'Producto' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producto' });
titulo(s, 'El sitio para pacientes y su asistente');
s.addImage({ path: IMG('chat_fiebre.png'), x: 0.5, y: 1.3, w: 2.05, h: 2.05 * ratio('chat_fiebre.png'), altText: 'El asistente responde a «tengo fiebre y dolor de garganta» con qué hacer en casa y qué se suele tomar', objectName: 'captura fiebre' });
s.addImage({ path: IMG('chat_alarma.png'), x: 2.75, y: 1.3, w: 2.05, h: 2.05 * ratio('chat_alarma.png'), altText: 'Ante «me duele el pecho» el asistente indica llamar al 123 y no compara centros', objectName: 'captura alarma' });
s.addText('Responde lo que la persona escribe', { x: 5.15, y: 1.3, w: 4.35, h: 0.35, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, isTextBox: true });
s.addText([
  { text: 'Entiende más de 90 temas de 15 especialidades, además de medicamentos, trámites y datos del sistema, y cuenta qué hacer en casa, qué se suele tomar sin fórmula y cuándo consultar.', options: { bullet: true, breakLine: true } },
  { text: 'Con señales de alarma, como dolor de pecho, dice que llame al 123 y no compara centros.', options: { bullet: true, breakLine: true } },
  { text: 'Para una cita, muestra qué centro tiene menos espera según el día y la hora, con datos reales de 2022.', options: { bullet: true, breakLine: true } },
  { text: 'No diagnostica ni receta: son reglas de orientación, y siempre lo avisa.', options: { bullet: true } },
], { x: 5.15, y: 1.7, w: 4.35, h: 2.75, fontSize: 12, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
tarjeta(s, 5.15, 4.35, 4.35, 0.7, { fill: HEX.coralT, line: HEX.coralT, name: 'dato triage' });
s.addText('Una persona con una urgencia menor espera una mediana de 79 minutos, frente a 37 en triage III.', { x: 5.3, y: 4.35, w: 4.05, h: 0.7, fontSize: 11, bold: true, color: HEX.coralD, margin: 0, valign: 'middle', isTextBox: true });
note(s, 'Este es el producto que usa el paciente. Escribe con sus palabras lo que siente y el asistente le responde: qué puede hacer en casa, qué se suele tomar sin fórmula y cuándo conviene consultar. Si lo que cuenta suena grave, como un dolor de pecho, no pierde tiempo comparando: le dice que llame al ciento veintitrés. Y para pedir una cita, le muestra a qué centro le conviene ir según el día y la hora. Son reglas de orientación, no un diagnóstico, y lo decimos siempre en pantalla.');

// ================================================================ 12. RESERVAS Y MÁS
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producto' });
titulo(s, 'Reserva de citas, verificador de urgencias y opiniones');
const wRes = 3.75 / ratio('reserva.png');
s.addImage({ path: IMG('reserva.png'), x: 0.5, y: 1.3, w: Math.min(wRes, 5.0), h: Math.min(wRes, 5.0) * ratio('reserva.png'), altText: 'Reserva de citas: calendario del mes y horarios libres con la espera típica de cada uno', objectName: 'captura reserva' });
const xr = 0.5 + Math.min(wRes, 5.0) + 0.35;
s.addText([
  { text: 'Calendario por mes con cupos libres y color según la disponibilidad.', options: { bullet: true, breakLine: true } },
  { text: 'Horarios de 30 minutos con la espera típica de cada uno; marca los tres con menos espera.', options: { bullet: true, breakLine: true } },
  { text: 'Código para consultar o cancelar la cita y archivo para el calendario del celular. La base impide que dos personas tomen el mismo cupo.', options: { bullet: true, breakLine: true } },
  { text: '¿Es urgente?: lista de signos de alarma que dice si llamar al 123 o pedir una cita hoy, y primeros auxilios paso a paso.', options: { bullet: true, breakLine: true } },
  { text: 'Opiniones reales de quienes lo usan, con promedio y distribución.', options: { bullet: true, breakLine: true } },
  { text: 'Para hospitales: cifras reales, vista previa del panel, simulador de ahorro y solicitud de demostración.', options: { bullet: true } },
], { x: xr, y: 1.3, w: 9.5 - xr, h: 3.75, fontSize: 12, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
note(s, 'Además de orientar, el sitio permite reservar. El paciente elige el centro y la especialidad, ve en el calendario qué días tienen cupos, y para cada horario le mostramos la espera típica, de modo que pueda escoger los de menos espera. Recibe un código para consultar o cancelar y puede agregar la cita a su calendario. La base de datos impide que dos personas tomen el mismo cupo. También hay un verificador que le dice si debe llamar al ciento veintitrés o pedir una cita hoy, con primeros auxilios básicos, y una sección de opiniones que escriben los propios usuarios.');

// ================================================================ 13. PANEL PARA HOSPITALES
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Producto' });
titulo(s, 'Lo que le ofrecemos al hospital');
const wPanel = 3.75 / ratio('panel_tablero.png');
s.addImage({ path: IMG('panel_tablero.png'), x: 0.5, y: 1.3, w: wPanel, h: 3.75, altText: 'Panel para coordinadores: pronóstico por hora, rango probable y personal necesario', objectName: 'captura panel' });
const xh = 0.5 + wPanel + 0.3, wh = 9.5 - xh;
s.addImage({ path: IMG('hosp_cifras.png'), x: xh, y: 1.3, w: wh, h: wh * ratio('hosp_cifras.png'), altText: 'Cifras reales del sistema: atenciones, espera, precisión, velocidad y pruebas', objectName: 'cifras hospital' });
const hDoble = wh * ratio('hosp_doble.png');
s.addImage({ path: IMG('hosp_doble.png'), x: xh, y: 1.3 + wh * ratio('hosp_cifras.png') + 0.15, w: wh, h: hDoble, altText: 'Vista previa real del panel y simulador de ahorro con los supuestos del hospital', objectName: 'vista previa y simulador' });
s.addText([
  { text: 'Panel: pronóstico por hora, personal necesario, horas críticas y escenarios de lluvia y demanda.', options: { bullet: true, breakLine: true } },
  { text: 'Simulador de ahorro con los supuestos de cada hospital, y solicitud de demostración en la misma página.', options: { bullet: true } },
], { x: xh, y: 1.3 + wh * ratio('hosp_cifras.png') + 0.15 + hDoble + 0.12, w: wh, h: 0.8, fontSize: 11, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 3, isTextBox: true });
note(s, 'Esto es lo que le vendemos al hospital. El panel le dice a quien coordina cuántos pacientes llegarán cada hora y cuánto personal hace falta. En la página hay cifras reales del sistema, una vista previa del panel con datos reales y un simulador donde el hospital escribe sus horas extra y su costo para ver cuánto podría ahorrar. Aclaramos que es una simulación con sus supuestos: el efecto real se mide en un piloto. Y desde la misma página puede solicitar una demostración, que queda guardada en nuestra base de datos. Las gráficas están en este panel y no en el sitio del paciente, a propósito.');

// ================================================================ 14. PRUEBAS Y ORQUESTACIÓN
pres.addSection({ title: 'Calidad' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Calidad' });
titulo(s, 'Pruebas automáticas y un flujo diario orquestado');
const ep = D.ev.ev_pruebas, eb = D.ev.ev_benchmark;
const AF = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'evidencias', 'airflow.json'), 'utf-8'));
cifra(s, 0.5, 1.4, 1.9, `${ep.passed}/${ep.total}`, 'pruebas pasan: unitarias, de límites e integración', { size: 32, hr: 0.7 });
cifra(s, 2.6, 1.4, 1.9, `${fmt(ep.cobertura, 1)} %`, 'de cobertura del código', { size: 32, hr: 0.7 });
cifra(s, 0.5, 2.9, 1.9, `${fmt(eb.p95_ms, 0)} ms`, `percentil 95 de la API en ${eb.peticiones} peticiones`, { size: 32, hr: 0.7 });
cifra(s, 2.6, 2.9, 1.9, '7 de 7', `tareas en success en Airflow, ${Math.floor(AF.duracion_total_s / 60)} min ${Math.round(AF.duracion_total_s % 60)} s`, { size: 32, hr: 0.7 });
s.addText('Cada falla tiene su respuesta: la carga no pasa si no concilia y el modelo no se publica si pierde contra la referencia.', { x: 0.5, y: 4.4, w: 4.0, h: 0.65, fontSize: 11, italic: true, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
tarjeta(s, 4.85, 1.4, 4.65, 3.65, { name: 'tarjeta dag' });
s.addText('vitaldata_diario · todos los días a las 5:00', { x: 5.05, y: 1.5, w: 4.3, h: 0.3, fontSize: 11, bold: true, color: C.text1, margin: 0, isTextBox: true });
const bw = 1.35;
caja(s, 4.95, 2.22, bw, 0.45, 'verificar_fuente', null, { f1: 10 });
caja(s, 6.5, 1.95, bw, 0.45, 'cargar_triage', null, { f1: 10 });
caja(s, 6.5, 2.5, bw, 0.45, 'cargar_clima', null, { f1: 10 });
caja(s, 8.05, 2.22, bw, 0.45, 'controles_de_calidad', null, { f1: 9 });
caja(s, 8.05, 3.5, bw, 0.45, 'entrenar_y_publicar', null, { f1: 9 });
caja(s, 6.5, 3.5, bw, 0.45, 'compuerta_del_modelo', null, { f1: 9, fill: HEX.coralT, line: HEX.coralT, c1: HEX.coralD });
caja(s, 4.95, 3.5, bw, 0.45, 'exportar_snapshot', null, { f1: 10 });
flecha(s, 6.32, 2.38, 6.48, 2.2); flecha(s, 6.32, 2.52, 6.48, 2.7);
flecha(s, 7.87, 2.2, 8.03, 2.38); flecha(s, 7.87, 2.72, 8.03, 2.52);
flecha(s, 8.72, 2.69, 8.72, 3.48);
flecha(s, 8.03, 3.72, 7.87, 3.72); flecha(s, 6.48, 3.72, 6.32, 3.72);
s.addText('Dos reintentos con espera creciente en cada tarea.', { x: 4.95, y: 4.3, w: 4.4, h: 0.6, fontSize: 10, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
note(s, 'Las pruebas son parte del producto. Tenemos doscientas noventa y tres pruebas automáticas, unitarias, de límites y de integración contra PostgreSQL, con una cobertura de más del noventa por ciento. La API responde en menos de cien milisegundos. Y todo el flujo corre cada día en Airflow en siete tareas; la corrida que ejecutamos terminó completa en unos nueve minutos: si la carga no concilia, se frena, y si el modelo nuevo pierde contra la referencia, no se publica.');

// ================================================================ 14. USUARIOS
pres.addSection({ title: 'Negocio' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Negocio' });
titulo(s, 'Cómo validamos el producto con personas');
[
  ['5 tareas', 'Elegir un centro y un día, comparar lo pronosticado con lo real, ajustar la dotación, y usar el asistente con un caso leve y uno de alarma.'],
  ['Cuestionario SUS', 'Diez preguntas estándar de usabilidad. Un puntaje de 68 es el promedio de la industria; sobre 80 es muy bueno.'],
  ['Registro anónimo', 'La prueba se hace dentro de la página: se guardan tareas logradas, tiempo y respuestas, sin datos personales.'],
].forEach(([t, d], i) => {
  const y = 1.4 + i * 1.2;
  tarjeta(s, 0.5, y, 5.6, 1.05);
  circulo(s, 0.7, y + 0.3, i + 1);
  s.addText(t, { x: 1.3, y: y + 0.1, w: 4.6, h: 0.3, fontFace: 'Cambria', fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
  s.addText(d, { x: 1.3, y: y + 0.42, w: 4.6, h: 0.6, fontSize: 11, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
});
tarjeta(s, 6.35, 1.4, 3.15, 3.55, { fill: C.text1, line: HEX.ink, name: 'meta usabilidad' });
s.addText('NUESTRA META', { x: 6.55, y: 1.55, w: 2.8, h: 0.3, fontSize: 10, bold: true, color: 'FF8A80', charSpacing: 2, margin: 0, isTextBox: true });
s.addText('SUS ≥ 68', { x: 6.55, y: 1.95, w: 2.8, h: 0.7, fontFace: 'Cambria', fontSize: 34, bold: true, color: C.background1, margin: 0, isTextBox: true });
s.addText('con cinco personas o más del perfil real: coordinadores, personal de salud y pacientes.', { x: 6.55, y: 2.75, w: 2.8, h: 0.9, fontSize: 12, color: 'C8CFD4', margin: 0, valign: 'top', isTextBox: true });
s.addText('Los resultados se calculan solos con las respuestas reales; no los inventamos.', { x: 6.55, y: 3.8, w: 2.8, h: 0.9, fontSize: 11, italic: true, color: 'C8CFD4', margin: 0, valign: 'top', isTextBox: true });
note(s, 'Para validar con personas usamos cinco tareas y el cuestionario SUS, que es el estándar para medir usabilidad. La prueba se hace dentro de la misma página y se guarda de forma anónima. Nuestra meta es un puntaje de 68 o más con al menos cinco personas. [Antes de presentar: si ya hicieron las sesiones, agregar aquí cuántas personas participaron, el puntaje SUS promedio, el porcentaje de tareas logradas y dos cambios que hicieron por lo que vieron.]');

// ================================================================ 15. FINANZAS
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Negocio' });
titulo(s, 'Cuánto cuesta operarlo y cuándo se paga solo');
cifra(s, 0.5, 1.4, 2.2, '$0,78 M', 'plan Completo al mes por IPS, sin IVA', { size: 30, hr: 0.6 });
cifra(s, 2.9, 1.4, 2.2, '$901.237', 'costo fijo mensual de operar', { size: 30, hr: 0.6 });
cifra(s, 0.5, 2.85, 2.2, '2 clientes', 'cubren los costos fijos', { size: 30, hr: 0.6 });
cifra(s, 2.9, 2.85, 2.2, '$86,3 M', 'para construir hasta la versión Beta', { size: 30, hr: 0.6 });
s.addText('Cobramos a la IPS, que es la que ahorra horas extra. El paciente usa el asistente sin pagar.', { x: 0.5, y: 4.3, w: 4.6, h: 0.7, fontSize: 11, italic: true, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
tarjeta(s, 5.4, 1.4, 4.1, 3.65, { name: 'tarjeta costo variable' });
const cv = [['Soporte técnico', 141007], ['Monitoreo', 73500], ['Gestor', 30265], ['WhatsApp', 25245]];
s.addChart(pres.charts.BAR, [{ name: 'COP por mes', labels: cv.map((c) => c[0]), values: cv.map((c) => c[1]) }], {
  x: 5.45, y: 1.45, w: 4.0, h: 3.0, barDir: 'bar', chartColors: [HEX.coral], showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '$#,##0', valAxisHidden: true, valAxisMaxVal: 190000, valAxisMinVal: 0, valGridLine: { style: 'none' }, showLegend: false, showTitle: true, title: 'Costo variable por cliente: $270.016 al mes', catAxisOrientation: 'maxMin', ...estiloGrafica(), valAxisLabelColor: HEX.gray,
});
s.addText('El 91 % son horas de personas. Precios de proveedores consultados el 9 de noviembre de 2026, con la TRM oficial de ese día ($3.237,83).', { x: 5.6, y: 4.45, w: 3.8, h: 0.55, fontSize: 10, color: C.text2, margin: 0, valign: 'top', isTextBox: true });
note(s, 'Le cobramos a la IPS, porque es la que gasta en horas extra cuando el turno se planea mal. El paciente no paga. Operar la plataforma cuesta cerca de novecientos mil pesos al mes, y cada cliente nos cuesta unos doscientos setenta mil. Con un plan de setecientos ochenta mil pesos al mes, dos clientes cubren los costos fijos. Construir hasta la versión Beta nos costaría unos ochenta y seis millones. Todos los precios son de proveedores reales y el modelo financiero está en Excel con sus fórmulas.');

// ================================================================ 16. LECCIONES
pres.addSection({ title: 'Cierre' });
s = pres.addSlide({ masterName: 'CONTENIDO', sectionTitle: 'Cierre' });
titulo(s, 'Lo que aprendimos y hasta dónde llegamos');
[
  ['Lo que logramos', HEX.ok, ['Un sistema completo y reproducible: ETL, base, modelo, API, pruebas, Airflow y aplicación.', 'Un hallazgo comprobado: más llegadas, más espera.', 'Una evaluación honesta, con referencias, intervalos y una meta que reconocemos no cumplida por franja.']],
  ['Lo que declaramos', HEX.gold, ['Los datos son de Pasto, de 2020 a 2022: es un sistema real, no el de un hospital cliente de hoy.', 'La fuente no trae el personal por turno: por eso se recomienda con una meta de espera.', 'El clima del pronóstico es el observado; en producción vendría de un pronóstico externo.']],
  ['Lo que sigue', HEX.blue, ['Probar con coordinadores reales.', 'Un piloto de tres meses con un hospital.', 'Conectar el asistente a WhatsApp.']],
].forEach(([t, col, items], i) => {
  const x = 0.5 + i * 3.05;
  tarjeta(s, x, 1.4, 2.9, 3.65);
  s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 1.58, w: 0.32, h: 0.32, fill: { color: col }, line: { color: col }, objectName: 'marca ' + t });
  s.addText(t, { x: x + 0.62, y: 1.55, w: 2.2, h: 0.38, fontFace: 'Cambria', fontSize: 15, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
  s.addText(items.map((tx, j) => ({ text: tx, options: { bullet: true, breakLine: j < items.length - 1 } })), { x: x + 0.2, y: 2.1, w: 2.55, h: 2.85, fontSize: 11, color: C.text2, margin: 0, valign: 'top', paraSpaceAfter: 6, isTextBox: true });
});
note(s, 'Lo que logramos es un sistema completo que se puede reproducir con un solo comando y que usa datos reales. Lo que declaramos: los datos son de Pasto entre 2020 y 2022, no tenemos el personal por turno y el clima del pronóstico es el observado. Por eso decimos que el siguiente paso es probar con coordinadores reales y hacer un piloto con un hospital.');

// ================================================================ 17. CIERRE
s = pres.addSlide({ masterName: 'CIERRE', sectionTitle: 'Cierre' });
s.addText('Veámoslo funcionando', { x: 0.6, y: 1.4, w: 8.8, h: 0.9, fontFace: 'Cambria', fontSize: 44, bold: true, color: C.background1, margin: 0, isTextBox: true });
s.addText('Tablero del coordinador · Asistente del paciente · Análisis', { x: 0.6, y: 2.4, w: 8.8, h: 0.5, fontSize: 18, color: 'FFD4CF', margin: 0, isTextBox: true });
s.addText('docker compose up  →  http://localhost:8000', { x: 0.6, y: 3.3, w: 8.8, h: 0.45, fontFace: 'Courier New', fontSize: 16, color: 'C8CFD4', margin: 0, isTextBox: true });
s.addText('Sebastian Lozano · Julian David Cuellar', { x: 0.6, y: 4.75, w: 8.8, h: 0.35, fontSize: 14, bold: true, color: C.background1, margin: 0, isTextBox: true });
note(s, 'Gracias. Les mostramos ahora la aplicación funcionando. Empezamos por el tablero del coordinador, después el asistente del paciente y por último el análisis.');

(async () => {
  await pres.writeFile({ fileName: SALIDA });
  await applyTheme(SALIDA, THEME);
  console.log('listo', SALIDA);
})();
