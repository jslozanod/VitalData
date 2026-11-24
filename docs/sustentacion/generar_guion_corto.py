"""Guion corto de la sustentacion de VitalData (unos 9 minutos con la demostracion)."""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SALIDA = Path(__file__).parent / "VitalData_Guion_Corto.docx"
CORAL = RGBColor(0xD9, 0x38, 0x2B)
GRIS = RGBColor(0x5E, 0x67, 0x70)

doc = Document()
s0 = doc.sections[0]
s0.left_margin = s0.right_margin = Cm(2.3)
s0.top_margin = s0.bottom_margin = Cm(1.9)
n = doc.styles["Normal"]
n.font.name, n.font.size = "Calibri", Pt(12)
n.paragraph_format.space_after = Pt(6)
n.paragraph_format.line_spacing = 1.2
for nom, tam in (("Heading 1", 18), ("Heading 2", 13.5)):
    st = doc.styles[nom]
    st.font.name, st.font.size, st.font.bold = "Cambria", Pt(tam), True
    st.font.color.rgb = RGBColor(0x22, 0x28, 0x2D)
    st.paragraph_format.space_before = Pt(12)
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.keep_with_next = True


def sombra(celda, color):
    pr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color)
    pr.append(sh)


def p(t, cursiva=False, color=None, tam=None, negrita=False):
    par = doc.add_paragraph()
    r = par.add_run(t)
    r.italic, r.bold = cursiva, negrita
    if color is not None: r.font.color.rgb = color
    if tam: r.font.size = Pt(tam)
    return par


def meta(texto):
    p(texto, cursiva=True, color=GRIS, tam=10).paragraph_format.space_after = Pt(2)


def tabla(cab, filas, anchos):
    t = doc.add_table(rows=1, cols=len(cab))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(cab):
        ce = t.rows[0].cells[i]; ce.text = ""
        r = ce.paragraphs[0].add_run(c); r.bold = True; r.font.size = Pt(10.5); r.font.color.rgb = RGBColor(255, 255, 255)
        sombra(ce, "22282D")
    for f in filas:
        cs = t.add_row().cells
        for i, v in enumerate(f):
            cs[i].text = ""
            r = cs[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(10.5)
    for f in t.rows:
        for i, w in enumerate(anchos):
            f.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def caja(texto):
    t = doc.add_table(rows=1, cols=1); t.style = "Table Grid"
    c = t.rows[0].cells[0]; sombra(c, "FFF3D4"); c.text = ""
    c.paragraphs[0].add_run(texto).font.size = Pt(10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ------------------------------------------------------------------ portada
t = doc.add_paragraph(); r = t.add_run("VitalData · Guion corto"); r.font.size = Pt(26); r.bold = True; r.font.name = "Cambria"
p("Unos 10 minutos en total: 6 de presentación y 4 de demostración", color=CORAL, tam=13)
p("Sebastian Lozano y Julian David Cuellar · Data Thinking · UAO", color=GRIS, tam=10.5)
p("Lo que dice cada uno está escrito con frases cortas y palabras de todos los días, para que cualquiera en el salón entienda qué problema resolvemos, qué hicimos y qué resultó. Las palabras técnicas que no se pueden evitar están explicadas al final, en el glosario.")

h = doc.add_heading("Qué diapositivas se muestran", level=1)
p("Se muestran 9 de las 18. Las demás se quedan guardadas para las preguntas: no las borren, solo pasen de largo.")
tabla(["Diapositiva", "Tema", "Habla", "Tiempo"], [
    ["1", "Portada", "Sebastian", "15 s"],
    ["2", "El problema", "Sebastian", "40 s"],
    ["4", "Los datos", "Sebastian", "40 s"],
    ["5", "Cómo está armado", "Sebastian", "35 s"],
    ["8", "Cuando llegan más, se espera más", "Julian", "40 s"],
    ["10", "Resultados", "Julian", "60 s"],
    ["Demo", "El sitio funcionando: asistente, a dónde ir, reserva y panel para hospitales (reemplaza las diapositivas 11 a 13)", "Los dos", "4 min"],
    ["14", "Pruebas y Airflow", "Julian", "35 s"],
    ["16", "Costos y precio", "Sebastian", "35 s"],
    ["17", "Lo que aprendimos (y cierre)", "Sebastian", "40 s"],
], [2.4, 8.2, 2.8, 2.2])
p("Se saltan: 3 (prototipos), 6 (carga de datos), 7 (base de datos), 9 (cómo se evalúa el modelo), 11, 12 y 13 (la demo las reemplaza), 15 (usuarios) y 18 (cierre).", cursiva=True)
caja("Si ya hicieron las pruebas de usabilidad con al menos cinco personas, agreguen la diapositiva 15 (30 segundos) después de la demo: cuántas personas lo probaron, qué puntaje dieron y qué cambiaron por eso. Si todavía no, no la muestren y no inventen cifras.")

# ------------------------------------------------------------------ guion
h = doc.add_heading("Lo que se dice", level=1)
guion = [
    ("Diapositiva 1 · Portada", "Sebastian · 15 segundos", [
        "Buenos días. Somos Sebastian y Julian, y les presentamos VitalData.",
        "Es una herramienta que le dice a un hospital cuántos pacientes van a llegar a urgencias en cada hora y cuánto personal necesita. Y le dice al paciente a qué urgencia le conviene ir. Funciona con datos reales, y al final se la mostramos.",
    ]),
    ("Diapositiva 2 · El problema", "Sebastian · 40 segundos", [
        "El problema lo conocemos todos: llegar a urgencias y encontrar la sala llena.",
        "Los hospitales organizan al personal por turnos, pero los pacientes llegan por horas. Y cuando llega el pico, la espera sube.",
        "Analizamos casi ochenta mil atenciones reales. La mitad de los pacientes espera menos de cuarenta minutos, pero hay un grupo que espera más de dos horas. Lo que queremos es que el hospital sepa antes cuándo viene el pico.",
    ]),
    ("Diapositiva 4 · Los datos", "Sebastian · 40 segundos", [
        "Usamos datos públicos de datos.gov.co: las atenciones de urgencias de tres centros de salud de Pasto y el clima del IDEAM.",
        "Elegimos Pasto porque es el único conjunto que encontramos con la hora de llegada de cada paciente. El de Cali solo trae diagnósticos de 2019, sin horas, y con eso no se puede pronosticar por hora. La idea sirve para cualquier hospital que tenga esos datos, y el siguiente paso es probarla con uno de Cali.",
        "Además, cada carga la verificamos: lo que se descargó, menos lo repetido, tiene que ser igual a lo que guardamos. Hoy esa cuenta cuadra.",
    ]),
    ("Diapositiva 5 · Cómo está armado", "Sebastian · 35 segundos", [
        "El sistema tiene cuatro partes. Un proceso que descarga y limpia los datos, una base de datos donde se guardan, un modelo que hace el pronóstico y una página donde se ve.",
        "Un programa que se llama Airflow ejecuta todo eso solo cada día. Y todo se levanta con un solo comando, para que cualquiera pueda repetirlo.",
    ]),
    ("Diapositiva 8 · Cuando llegan más, se espera más", "Julian · 40 segundos", [
        "Antes de construir el modelo comprobamos la idea: cuando llegan más pacientes en una hora, la espera sube.",
        "En el Hospital Local Civil, las horas con un solo paciente tienen una espera de unos setenta minutos, y las horas con siete o más, de casi cien. Lo confirmamos en los tres centros con una prueba estadística.",
        "También vimos que los casos leves esperan más del doble que los moderados. Por eso nuestro asistente ayuda a esos pacientes a elegir a dónde ir.",
    ]),
    ("Diapositiva 10 · Resultados", "Julian · 1 minuto", [
        "Para saber si el modelo sirve, lo comparamos con métodos simples que no usan inteligencia artificial, como repetir lo que pasó la semana anterior. Lo probamos con cincuenta y tres días que el modelo nunca había visto.",
        "Por franja de tres horas, el modelo les gana a los tres métodos en los tres centros, aunque la mejora es pequeña. Por día, no hay diferencia.",
        "Y la meta que nos pusimos, ochenta y cinco por ciento de acierto por franja, no la cumplimos: llegamos a entre setenta y setenta y cuatro. Lo decimos tal como es. La razón es que son centros pequeños, con pocos pacientes por hora, y eso siempre deja un margen de error.",
        "Por eso lo más útil del sistema no es acertar el número exacto, sino mostrar un rango probable y convertirlo en personal necesario.",
    ]),
]
for titulo, quien, parrafos in guion:
    doc.add_heading(titulo, level=2)
    meta(quien)
    for t in parrafos:
        p(t)

# ------------------------------------------------------------------ demo
doc.add_heading("Demostración en vivo · 4 minutos", level=1)
meta("Sebastian maneja el computador y Julian habla. Se hace en http://localhost:8000. Antes de empezar, en la sección «¿A dónde te conviene ir?» dejen el día en Sábado y la hora en 10:00. Hay que cancelar o borrar cualquier cita de prueba antes de presentar.")
doc.add_heading("El sitio del paciente · 2 minutos", level=2)
p("[Mostrar la página principal.]", cursiva=True, color=GRIS, tam=10.5)
p("Este es el sitio que usa el paciente. Pregunta algo muy sencillo: en qué nos puede orientar hoy. Y aquí lo importante: no hay gráficas ni datos técnicos, solo lo que la persona necesita.")
p("[En el chat, escribir «tengo fiebre y dolor de garganta» y enviar.]", cursiva=True, color=GRIS, tam=10.5)
p("La persona escribe con sus palabras lo que siente. El asistente entiende que es fiebre con dolor de garganta y le explica qué hacer. Puede ver qué hacer en casa, qué se suele tomar sin fórmula, cuándo conviene consultar y cuáles son las señales de alarma.")
p("[Pulsar «Qué puedo tomar».]", cursiva=True, color=GRIS, tam=10.5)
p("Por ejemplo, para la fiebre menciona el acetaminofén y avisa que no se debe dar aspirina a niños. No da dosis ni receta, y siempre recuerda que es una orientación general.")
p("Y si quiere pedir cita, puede pulsar «Reservar cita». El asistente solo responde sobre salud: qué hacer en casa, qué se suele tomar y cuándo consultar. Decidir a qué centro ir se hace en otra sección, que vemos enseguida.")
p("[Escribir «me duele el pecho».]", cursiva=True, color=GRIS, tam=10.5)
p("Pero si lo que cuenta suena grave, no compara nada: le dice que llame al ciento veintitrés.")
doc.add_heading("Reservar una cita · 40 segundos", level=2)
p("[Bajar a «Reserva tu cita», elegir un día en el calendario y un horario con la etiqueta «Recomendada».]", cursiva=True, color=GRIS, tam=10.5)
p("Y si la persona necesita una cita, la reserva aquí mismo. Ve en el calendario qué días tienen cupos, y para cada horario le mostramos la espera típica, así puede escoger los de menos espera. Al reservar recibe un código para consultar o cancelar, y puede agregar la cita a su calendario.")
p("[Llenar nombre y celular, aceptar el uso de datos y reservar. Mostrar el código.]", cursiva=True, color=GRIS, tam=10.5)
doc.add_heading("¿Es urgente? y opiniones · 20 segundos", level=2)
p("[Bajar a «¿Es urgente?», marcar «Dificultad para respirar».]", cursiva=True, color=GRIS, tam=10.5)
p("También hay un verificador: la persona marca lo que le pasa y le decimos si debe llamar al ciento veintitrés o pedir una cita hoy, con primeros auxilios paso a paso. Y al final, las opiniones las escriben quienes usan el sitio.")
doc.add_heading("¿A dónde te conviene ir? · 30 segundos", level=2)
p("[Bajar a esa sección y cambiar el día, por ejemplo a Lunes.]", cursiva=True, color=GRIS, tam=10.5)
p("Aquí el paciente elige el día y la hora y ve qué centro suele tener menos espera. El sábado a las diez, San Vicente tiene unos veintinueve minutos de espera, La Rosa cuarenta y seis y el Hospital Local Civil setenta y seis: ir al primero le ahorra más de cuarenta minutos. También le muestra el mejor momento de la mañana, la tarde y la noche.")
doc.add_heading("El panel para hospitales · 30 segundos", level=2)
p("[Pulsar «Para hospitales» y elegir el Hospital Local Civil, sábado 20 de agosto de 2022.]", cursiva=True, color=GRIS, tam=10.5)
p("Y esto es lo que le vendemos al hospital: un panel para quien coordina. Con los mismos datos, pronostica cuántos pacientes llegarán cada hora. Aquí pronosticó sesenta y dos y llegaron sesenta y tres. Con tres personas hay cuatro horas críticas, y con una más, ninguna.")
p("Las gráficas están en este panel y no en el sitio del paciente, a propósito: el paciente solo necesita saber a dónde ir.")

# ------------------------------------------------------------------ resto del guion
doc.add_heading("Para terminar", level=1)
guion2 = [
    ("Diapositiva 14 · Pruebas y Airflow", "Julian · 35 segundos", [
        "Para que no sea una maqueta, el sistema tiene más de cien pruebas automáticas, y todas pasan. Y ejecutamos una corrida completa de Airflow que terminó bien en unos nueve minutos.",
        "Si la carga de datos no cuadra, el sistema se frena. Y si el modelo nuevo resulta peor que el método simple, no se publica.",
    ]),
    ("Diapositiva 16 · Costos y precio", "Sebastian · 35 segundos", [
        "Le cobramos al hospital, porque es el que gasta en horas extra cuando el turno se planea mal. Al paciente no le cobramos.",
        "Operar la plataforma cuesta cerca de novecientos mil pesos al mes, y con un plan de setecientos ochenta mil, dos hospitales cubren esos costos. Construirla hasta la versión Beta costaría unos ochenta y seis millones. Los precios son de proveedores reales, consultados el nueve de noviembre.",
    ]),
    ("Diapositiva 17 · Lo que aprendimos", "Sebastian · 40 segundos", [
        "Para terminar. Logramos un sistema completo, con datos reales, que se puede repetir con un solo comando.",
        "Y decimos con claridad sus límites: los datos son de Pasto, de 2020 a 2022, no tenemos el personal que había en cada turno y el clima que usamos es el que ya ocurrió, no un pronóstico.",
        "El siguiente paso es probarlo con coordinadores reales y con un hospital, idealmente de Cali. Muchas gracias.",
    ]),
]
for titulo, quien, parrafos in guion2:
    doc.add_heading(titulo, level=2)
    meta(quien)
    for t in parrafos:
        p(t)

# ------------------------------------------------------------------ respuestas
doc.add_heading("Cuatro preguntas que seguro hacen", level=1)
for q, a in [
    ("¿Por qué Pasto y no Cali?", "Porque el único conjunto público que encontramos con la hora de llegada de cada paciente es el de Pasto. El de Cali solo trae diagnósticos de 2019 sin horas. La idea sirve para cualquier hospital con esos datos, y el siguiente paso es probarla en uno de Cali."),
    ("¿Por qué no cumplieron el ochenta y cinco por ciento?", "Porque son centros pequeños, con pocos pacientes por hora, y eso deja un margen de error que ningún modelo elimina. Por día sí llegamos. Preferimos decirlo tal como es."),
    ("¿El asistente receta medicamentos?", "No. Da orientación general: qué hacer en casa, qué medicamentos de venta libre se suelen usar, sin dosis, y cuándo consultar. No receta, no diagnostica y siempre avisa que no reemplaza a un médico. Ante señales de alarma manda a urgencias."),
    ("¿Los datos son reales?", "Sí, son públicos y se pueden comprobar en datos.gov.co. Todo lo que vieron sale de ellos."),
    ("¿Lo probaron con usuarios?", "[Contesten con lo que de verdad hicieron.] Si ya lo hicieron: cuántas personas, qué puntaje y qué cambiaron. Si no: «Está en curso. La prueba ya está dentro de la página y se guarda de forma anónima.»"),
]:
    par = doc.add_paragraph(); par.add_run(q).bold = True; par.paragraph_format.space_after = Pt(1); par.paragraph_format.keep_with_next = True
    p(a)

# ------------------------------------------------------------------ glosario
doc.add_heading("Palabras que usamos, en palabras sencillas", level=1)
tabla(["Palabra", "Qué quiere decir"], [
    ["Triage", "El nivel de urgencia con que clasifican a un paciente cuando llega. Va de uno (más grave) a cinco (menos grave)."],
    ["Datos abiertos", "Información pública que cualquier persona puede descargar y comprobar."],
    ["Pronóstico", "Calcular cuántos pacientes llegarán en cada hora de un día."],
    ["Rango probable", "La zona dentro de la cual esperamos que caiga lo que pase; el número exacto casi nunca se acierta."],
    ["Franja de tres horas", "Sumar los pacientes de tres horas seguidas. Es más fácil de acertar que hora por hora, y el personal se organiza así."],
    ["Método simple, sin inteligencia artificial", "Una regla básica, como repetir lo que pasó la semana anterior. Si el modelo no le gana, no vale la pena."],
    ["Dotación", "Cuántas personas están atendiendo a la vez."],
    ["Base de datos", "El lugar donde se guarda toda la información de forma ordenada."],
    ["Airflow", "Un programa que ejecuta todos los pasos del sistema solo, cada día, en el orden correcto."],
    ["Prueba automática", "Un programa que comprueba que otra parte del sistema funciona bien, sin que nadie lo revise a mano."],
], [5.2, 11.2])

doc.save(SALIDA)
print("listo", SALIDA)
