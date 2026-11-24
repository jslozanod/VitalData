"""Genera el guion de la sustentacion final de VitalData (Word)."""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SALIDA = Path(__file__).parent / "VitalData_Guion_Sustentacion_Final.docx"
CORAL = RGBColor(0xD9, 0x38, 0x2B)
GRIS = RGBColor(0x5E, 0x67, 0x70)

doc = Document()
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Cm(2.3)
sec.top_margin = sec.bottom_margin = Cm(2.0)
base = doc.styles["Normal"]
base.font.name = "Calibri"
base.font.size = Pt(11.5)
base.paragraph_format.space_after = Pt(6)
base.paragraph_format.line_spacing = 1.2
for nombre, tam in (("Heading 1", 20), ("Heading 2", 14.5), ("Heading 3", 12)):
    st = doc.styles[nombre]
    st.font.name = "Cambria"
    st.font.size = Pt(tam)
    st.font.bold = True
    st.font.color.rgb = RGBColor(0x22, 0x28, 0x2D)
    st.paragraph_format.space_before = Pt(14 if nombre != "Heading 3" else 10)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.keep_with_next = True


def sombreado(celda, color):
    pr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    pr.append(sh)


def h1(t): doc.add_heading(t, level=1)
def h2(t): doc.add_heading(t, level=2)
def h3(t): doc.add_heading(t, level=3)


def p(texto, negrita=False, cursiva=False, color=None, tam=None):
    par = doc.add_paragraph()
    r = par.add_run(texto)
    r.bold, r.italic = negrita, cursiva
    if color is not None:
        r.font.color.rgb = color
    if tam:
        r.font.size = Pt(tam)
    return par


def mixto(partes):
    """partes: lista de (texto, negrita)."""
    par = doc.add_paragraph()
    for t, n in partes:
        par.add_run(t).bold = n
    return par


def lista(items, numerada=False):
    for it in items:
        par = doc.add_paragraph(style="List Number" if numerada else "List Bullet")
        par.paragraph_format.space_after = Pt(3)
        if isinstance(it, tuple):
            par.add_run(it[0]).bold = True
            par.add_run(it[1])
        else:
            par.add_run(it)


def tabla(cabecera, filas, anchos=None):
    t = doc.add_table(rows=1, cols=len(cabecera))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(cabecera):
        celda = t.rows[0].cells[i]
        celda.text = ""
        run = celda.paragraphs[0].add_run(c)
        run.bold = True
        run.font.size = Pt(10.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombreado(celda, "22282D")
    for fila in filas:
        cel = t.add_row().cells
        for i, v in enumerate(fila):
            cel[i].text = ""
            run = cel[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(10.5)
    if anchos:
        for fila in t.rows:
            for i, w in enumerate(anchos):
                fila.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def nota(texto):
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    c = t.rows[0].cells[0]
    sombreado(c, "FFF3D4")
    c.text = ""
    c.paragraphs[0].add_run(texto).font.size = Pt(10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ====================================================================== portada
t = doc.add_paragraph()
r = t.add_run("VitalData")
r.font.size = Pt(34)
r.font.name = "Cambria"
r.bold = True
t = doc.add_paragraph()
r = t.add_run("Guion de la sustentación final")
r.font.size = Pt(18)
r.font.color.rgb = CORAL
p("Data Thinking · Universidad Autónoma de Occidente", color=GRIS)
p("Sebastian Lozano y Julian David Cuellar", color=GRIS)
p("Este documento tiene todo lo que necesitan: la respuesta a la pregunta de Cali, la lista de cosas por abrir, lo que dice cada uno en cada diapositiva, el recorrido de la demostración en la página y las preguntas que probablemente hará el jurado con sus respuestas. Los textos para decir en voz alta están escritos como se habla; léanlos varias veces y háganlos suyos, no los memoricen palabra por palabra.")

# ====================================================================== 1. cali
h1("1. Lo primero: los hospitales son de Pasto, no de Cali")
mixto([("Qué usamos. ", True), ("Los tres centros que aparecen en la aplicación son Hospital Local Civil, Centro Hospital La Rosa y CS San Vicente. Los tres son de la E.S.E. Pasto Salud, en Pasto (Nariño), y salen del conjunto de datos abiertos «Clasificación en Triage Urgencias» de datos.gov.co (identificador vt5n-eu2r). No hay ningún hospital de Cali en el modelo.", False)])
mixto([("Por qué. ", True), ("Buscamos en datos.gov.co datos de urgencias de Cali. El único conjunto que apareció es de la E.S.E. del Centro de Cali (identificador 6ku5-65hk): son 4.617 filas con las primeras causas de consulta de 2019, por diagnóstico y sexo, sin ninguna hora. Con eso no se puede pronosticar cuántos llegan cada hora. El de Pasto es el único que encontramos que trae, de cada paciente, la fecha y hora de llegada, el nivel de triage y la hora de atención. Esos tres datos son los que necesita el modelo.", False)])
mixto([("Qué decir si el jurado pregunta por Cali. ", True), ("Que el método no depende de Pasto: depende de que el hospital tenga esos tres datos en su sistema de información. Que usamos Pasto para validar el método con datos reales y verificables, y que el paso siguiente es probarlo con un hospital de Cali con sus propios datos. Eso está dicho en las diapositivas 4 y 16.", False)])
nota("No digan que los datos son de Cali ni que «representan a Cali». Si el jurado lo pregunta, la respuesta honesta es la de arriba, y es una respuesta fuerte: demuestra que buscaron, que entienden qué datos necesita el modelo y que saben cuál es el siguiente paso.")
p("Sobre cambiar de fuente: el identificador del conjunto de datos y la estación del clima están en un solo archivo de configuración (src/vitaldata/config.py), así que cambiar de fuente es sencillo si el hospital entrega las mismas columnas (fecha y hora de ingreso, fecha y hora de atención, triage e IPS). Si trae otros nombres de columnas, hay que ajustar la lectura en la parte de extracción y validación del flujo (src/vitaldata/etl). El modelo en sí no cambia: se reentrena con los datos nuevos.")

# ====================================================================== 2. antes de entrar
h1("2. Antes de entrar: qué abrir")
p("Dejen todo abierto antes de que empiece su turno, para no perder tiempo buscando ventanas.", cursiva=True)
lista([
    ("Presentación: ", "VitalData_Entrega_Final.pptx, en modo presentación desde la diapositiva 1. Las notas del orador ya tienen un resumen de cada una."),
    ("La aplicación: ", "http://localhost:8000 en el navegador, en una pestaña. En otra pestaña, la documentación técnica: http://localhost:8000/proyecto.html. En una tercera, el Swagger de la API: http://localhost:8000/docs."),
    ("Airflow: ", "http://localhost:8080 (usuario admin; la contraseña es la de AIRFLOW_ADMIN_PASSWORD en el archivo .env). Entren al flujo vitaldata_diario y dejen abierta la pestaña Graph con la última corrida en verde."),
    ("Una terminal ", "abierta en la carpeta del proyecto, con el comando de las pruebas escrito pero sin ejecutar: PYTHONPATH=src pytest tests -q."),
    ("Este guion ", "impreso o en el celular."),
])
h3("Para levantar todo si el computador estaba apagado")
p("docker compose up -d db api airflow-web airflow-scheduler")
p("Esperen un minuto y verifiquen que http://localhost:8000/api/health responde «ok». La base de datos conserva los datos y los modelos entre reinicios, así que no hay que volver a cargar nada.")
h3("Plan B si algo falla")
lista([
    "Si la API no levanta: la página abre igual con una copia de los mismos datos (el distintivo arriba a la derecha dirá «Datos exportados» en vez de «API en vivo»). Todo funciona excepto los escenarios con lluvia y demanda.",
    "Si Docker no levanta: la presentación se sostiene sola y la demostración se hace sobre las capturas de las diapositivas 11 y 12.",
    "Si Airflow tarda en abrir: la diapositiva 13 y la captura en docs/evidencias/capturas/airflow-grafo.png muestran la corrida completa.",
])

# ====================================================================== 3. reparto y tiempos
h1("3. Reparto y tiempos")
p("Son 17 diapositivas y una demostración. Con 15 a 17 minutos de presentación y 5 de demostración, el total ronda los 20 minutos. Si les dan menos tiempo, pasen rápido las diapositivas 3, 6 y 7, y dejen para las preguntas todo lo técnico.")
tabla(["#", "Diapositiva", "Quién", "Minutos"], [
    ["1", "Portada", "Sebastian", "0,5"],
    ["2", "El problema", "Sebastian", "1"],
    ["3", "Dos usuarios y cuatro niveles de prototipo", "Sebastian", "1"],
    ["4", "Datos abiertos y reales", "Sebastian", "1"],
    ["5", "Arquitectura", "Sebastian", "1"],
    ["6", "El ETL", "Sebastian", "1"],
    ["7", "La base de datos", "Sebastian", "1"],
    ["8", "Cuando llegan más, se espera más", "Julian", "1"],
    ["9", "El modelo y cómo se evalúa", "Julian", "1"],
    ["10", "Resultados", "Julian", "1,5"],
    ["11", "Tablero del coordinador", "Julian", "0,5"],
    ["12", "Asistente del paciente", "Julian", "0,5"],
    ["13", "Pruebas y Airflow", "Julian", "1"],
    ["14", "Validación con personas", "Julian", "0,75"],
    ["15", "Finanzas", "Sebastian", "1"],
    ["16", "Lo que aprendimos", "Sebastian", "1"],
    ["17", "Cierre y paso a la demostración", "Sebastian", "0,25"],
    ["", "Demostración en vivo", "Los dos", "5"],
], [1.2, 8.5, 3, 2.3])
p("Pueden cambiar el reparto. Lo importante es que cada uno hable de lo que hizo, para que las preguntas técnicas las responda quien conoce esa parte.", cursiva=True)

# ====================================================================== 4. guion
h1("4. Guion hablado, diapositiva por diapositiva")

guion = [
    ("1. Portada", "Sebastian", [
        "Buenos días. Somos Sebastian Lozano y Julian David Cuellar y vamos a presentarles VitalData.",
        "VitalData le dice a un hospital cuántos pacientes van a llegar a urgencias en cada hora y cuántas personas hacen falta para atenderlos bien. Y le dice al paciente a qué urgencia le conviene ir.",
        "Lo que van a ver hoy no es una maqueta. Es una aplicación que funciona con datos reales, y al final se las mostramos en vivo.",
    ]),
    ("2. El problema", "Sebastian", [
        "Escogimos este problema porque casi todos los colombianos lo hemos vivido de cerca: llegar a urgencias y encontrar la sala llena.",
        "Lo que descubrimos es que a los hospitales no les falta información. Cada atención queda registrada con la hora en que llegó el paciente, su nivel de triage y la hora en que lo atendieron. Pero esa información se usa para facturar y casi nunca para mirar hacia adelante.",
        "Por eso el personal se organiza por turnos, y la gente llega por horas. Cuando llega el pico, la espera sube. En las casi ochenta mil atenciones que analizamos, la mitad de los pacientes espera menos de cuarenta minutos, pero hay un grupo grande que espera más de dos horas. Ese grupo es el que queremos reducir.",
    ]),
    ("3. Dos usuarios y cuatro niveles de prototipo", "Sebastian", [
        "Diseñamos para dos personas. Quien coordina el servicio necesita saber cuántos pacientes van a llegar para organizar el personal. Y quien espera necesita saber si le conviene ir ahora o a otro centro.",
        "Llegamos al producto por etapas. Empezamos con un boceto a lápiz de la pantalla del coordinador, después hicimos una maqueta con color y datos de ejemplo, y por último construimos el producto funcional con datos reales, que es el que van a ver.",
    ]),
    ("4. Datos abiertos y reales", "Sebastian", [
        "Todos los datos son públicos y cualquiera puede comprobarlos. Las atenciones de urgencias son de la E.S.E. Pasto Salud y el clima es del IDEAM, y los dos se descargan directamente de datos.gov.co.",
        "Quiero explicar por qué usamos datos de Pasto y no de Cali. Buscamos datos de urgencias de Cali y lo único que encontramos fue un conjunto de diagnósticos de 2019 sin horas, y con eso no se puede pronosticar cuántos llegan cada hora. El de Pasto es el único que encontramos que trae, de cada paciente, la hora de llegada, el triage y la hora de atención. Por eso validamos el método ahí, y el siguiente paso es probarlo con un hospital de Cali con sus propios datos.",
        "Algo que cuidamos mucho es que cada fila cuente. En la carga bajaron casi noventa mil filas, quitamos las repetidas y quedaron setenta y nueve mil quinientas. Esa cuenta se verifica en cada carga y hoy cuadra.",
    ]),
    ("5. Arquitectura", "Sebastian", [
        "Así está armado el sistema. Los datos entran por un proceso de carga, se guardan en una base de datos PostgreSQL, los modelos aprenden de ahí y publican sus pronósticos, y una API se los entrega a la aplicación web.",
        "Un programador de tareas, Airflow, ejecuta todo ese recorrido cada día, y las pruebas automáticas cubren cada parte. Todo se levanta con un solo comando de Docker, para que cualquiera pueda reproducirlo.",
    ]),
    ("6. El ETL", "Sebastian", [
        "El proceso de carga está pensado para fallar bien. Si se repite una carga, no duplica nada, porque cada fila tiene una huella única. Lo que se rechaza queda guardado con su motivo, y cada corrida deja un registro, también las que fallan.",
        "Al mirar las series descubrimos dos cosas que cambiaron el modelo. La fuente no trae registros durante un año, entre abril de 2020 y marzo de 2021, así que entrenamos solo con el periodo continuo. Y desde mayo de 2022 las llegadas casi se duplican, así que el modelo se apoya en lo ocurrido en la última semana y no en el promedio de toda la historia.",
    ]),
    ("7. La base de datos", "Sebastian", [
        "La base es un esquema en estrella: una tabla con cada atención y tablas pequeñas para el centro, el nivel de triage y la estación del clima, conectadas con llaves foráneas.",
        "Las reglas de calidad viven en la base y no solo en el código. No se puede guardar una atención anterior a su llegada ni una espera imposible.",
        "También medimos las consultas. Con un índice por centro y fecha, la consulta que usa el modelo se hace más de cinco veces más rápido.",
    ]),
    ("8. Cuando llegan más, se espera más", "Julian", [
        "Nuestra hipótesis era que cuando llegan más pacientes en una hora, la espera sube. Y los datos lo confirman en los tres centros. En el Hospital Local Civil, por ejemplo, las horas con un solo paciente tienen una espera media de unos setenta minutos, y las horas con siete o más, de casi cien.",
        "Lo comprobamos con una prueba de permutación, que no depende de supuestos sobre los datos. Y somos cuidadosos al decirlo: la relación es moderada, porque la espera también depende del triage y del personal que había, y la fuente no trae el personal por turno.",
        "Vimos además algo que usamos en el asistente: los pacientes de triage cuatro y cinco, que son urgencias menores, esperan más del doble que los de triage tres. Orientarlos a otra atención libera la sala para quienes más lo necesitan.",
    ]),
    ("9. El modelo y cómo se evalúa", "Julian", [
        "El modelo es sencillo a propósito, porque así se puede explicar. Pronostica las llegadas de cada hora con una regresión de Poisson que tiene en cuenta el tipo de día, el nivel de la última semana, la lluvia y la temperatura. Después convierte ese pronóstico en personal necesario con teoría de colas.",
        "Lo importante es cómo lo evaluamos. Reentrenamos semana a semana usando solo lo que ya había pasado. Escogimos los parámetros en una ventana aparte, y cincuenta y tres días de prueba nunca se usaron para decidir nada. Y lo comparamos con tres métodos simples que no usan inteligencia artificial, porque un modelo que no le gana a eso no vale la pena.",
    ]),
    ("10. Resultados", "Julian", [
        "Este es el resultado y preferimos contarlo tal como es. Por franja de tres horas, el modelo le gana a los tres métodos simples en los tres centros. La mejora es clara en La Rosa y en San Vicente, y más pequeña en el Hospital Local Civil, donde no podemos asegurar que sea real.",
        "Por día no hay diferencia con el promedio de cuatro semanas. Y la meta que nos pusimos, ochenta y cinco por ciento por franja de tres horas, no la cumplimos: estamos entre setenta y setenta y cuatro. Por día sí la alcanzamos.",
        "La razón es que son centros pequeños, con pocos pacientes por hora, y ese ruido no lo elimina ningún modelo. Por eso lo más útil del sistema no es acertar el número exacto, sino mostrar el rango probable y traducirlo a personal.",
    ]),
    ("11. Tablero del coordinador", "Julian", [
        "Este es el tablero del coordinador. Elige un centro y un día, y ve el pronóstico hora por hora con su rango probable, lo que realmente ocurrió y cuántas personas hacían falta. Puede ajustar los minutos por paciente, la espera que acepta y la dotación que tiene, y probar qué pasa si llueve mucho o si sube la demanda. Y se lleva el plan del día en un archivo.",
        "Ahora lo vemos funcionando, pero antes terminamos de mostrar el resto del trabajo.",
    ]),
    ("12. Asistente del paciente", "Julian", [
        "El asistente es para quien espera. Si lo que cuenta suena a una urgencia seria, como un dolor de pecho, no pierde tiempo comparando: le dice que llame al ciento veintitrés. Si es algo leve, le muestra qué centro tiene menos espera a la hora en que piensa ir.",
        "Son reglas simples y transparentes, no un sistema clínico, y lo decimos siempre en pantalla.",
    ]),
    ("13. Pruebas y Airflow", "Julian", [
        "Las pruebas son parte del producto. Tenemos más de cien pruebas automáticas, unitarias, de límites y de integración contra PostgreSQL real, con una cobertura de más del noventa por ciento. La API responde en menos de cien milisegundos.",
        "Y todo el flujo corre cada día en Airflow en siete tareas. Ejecutamos una corrida completa y terminó bien en unos nueve minutos. Si la carga no cuadra, se frena, y si el modelo nuevo pierde contra la referencia, no se publica.",
    ]),
    ("14. Validación con personas", "Julian", [
        "Para validar con personas usamos cinco tareas y el cuestionario SUS, que es el estándar para medir qué tan fácil es usar un sistema. La prueba se hace dentro de la misma página y se guarda de forma anónima. Nuestra meta es un puntaje de sesenta y ocho o más con al menos cinco personas.",
        "[Completar antes de presentar: cuántas personas lo probaron, el puntaje promedio, qué porcentaje de las tareas lograron y dos cambios que hicieron por lo que vieron. Si todavía no se han hecho las sesiones, digan que están en curso y no inventen cifras.]",
    ]),
    ("15. Finanzas", "Sebastian", [
        "Le cobramos al hospital, porque es el que gasta en horas extra cuando el turno se planea mal. El paciente no paga.",
        "Operar la plataforma cuesta cerca de novecientos mil pesos al mes, y cada cliente nos cuesta unos doscientos setenta mil. Con un plan de setecientos ochenta mil al mes, dos clientes cubren los costos fijos. Construir hasta la versión Beta costaría unos ochenta y seis millones.",
        "Los precios son de proveedores reales consultados el nueve de noviembre, con la tasa de cambio de ese día, y el modelo financiero está en Excel con sus fórmulas. El precio del plan todavía no lo hemos validado con un cliente.",
    ]),
    ("16. Lo que aprendimos", "Sebastian", [
        "Lo que logramos es un sistema completo que se reproduce con un comando y usa datos reales, con un hallazgo comprobado y una evaluación honesta.",
        "Y declaramos lo que no hicimos. Los datos son de Pasto, de 2020 a 2022. No tenemos el personal que había en cada turno, y por eso lo recomendamos con una meta de espera. Y el clima que usamos es el observado; en un uso real vendría de un pronóstico, y la precisión sería algo menor.",
        "El siguiente paso es probarlo con coordinadores reales y con un hospital, idealmente de Cali, con un piloto de tres meses.",
    ]),
    ("17. Cierre", "Sebastian", [
        "Gracias. Ahora les mostramos la aplicación funcionando.",
    ]),
]
for titulo, quien, parrafos in guion:
    h2(f"Diapositiva {titulo}")
    p(f"Habla: {quien}", cursiva=True, color=GRIS, tam=10)
    for par in parrafos:
        if par.startswith("["):
            nota(par)
        else:
            p(par)

# ====================================================================== 5. demo
h1("5. La demostración en vivo: cómo funciona la página")
nota("Importante: este recorrido describe el tablero y el asistente como estaban antes de la versión final del sitio. En la versión final la página principal es el sitio para pacientes (asistente que responde síntomas y recomienda a dónde ir) y el tablero con gráficas está en «Para hospitales» (panel.html). Para la demostración usen el recorrido del guion corto (VitalData_Guion_Corto.docx); los números del tablero siguen valiendo.")
p("Duran unos cinco minutos. Se hace en http://localhost:8000. Sebastian maneja el computador y Julian habla, o al revés. Los números de abajo son los reales; verifíquenlos antes con un ensayo, porque si cambian los datos o reentrenan el modelo pueden variar un poco.")

h2("Paso 1. La pantalla de inicio (30 segundos)")
p("Se abre en el Tablero del día. Arriba hay tres pestañas: Tablero del día, Asistente y Análisis. A la derecha dice «API en vivo»: significa que la página está consultando la base de datos en ese momento y no una copia.")
p("Qué decir: «Esta es la aplicación. Arriba están los datos con los que trabaja: casi ochenta mil atenciones reales de ocho centros de salud de Pasto. Tres de ellos tienen suficiente historia para tener modelo, y son los que se pueden elegir aquí.»")

h2("Paso 2. El tablero del coordinador (2 minutos)")
lista([
    ("Dejen el Hospital Local Civil y el sábado 20 de agosto de 2022. ", "Arriba salen cuatro tarjetas: pacientes pronosticados 62, llegaron 63 (error de 2 %), hora pico a las 9 de la mañana (la real fue a las 11) y horas en rojo."),
    ("Señalen la gráfica. ", "La línea roja es el pronóstico, la franja rosada es el rango probable del 80 %, los puntos negros son lo que ocurrió y la línea gris punteada es el método simple sin inteligencia artificial. Qué decir: «El modelo se hizo con lo que se sabía hasta la medianoche de ese día. Esos puntos negros son lo que pasó de verdad, y casi siempre caen dentro del rango.»"),
    ("Miren «horas en rojo» con la dotación de 3 personas: 4 horas. ", "Abajo, en la gráfica de personal, las barras que superan la línea de la dotación son las horas en que no alcanza. Qué decir: «Con tres personas, hay cuatro horas de la mañana en las que la espera se dispara.»"),
    ("Suban la dotación a 4 con el control deslizante. ", "Las horas en rojo pasan a 0. Qué decir: «Con una persona más, ninguna hora queda en rojo. Esa es la decisión que el tablero le ayuda a tomar al coordinador.»"),
    ("Muevan «Espera objetivo» de 15 a 5 minutos. ", "El personal necesario sube. Qué decir: «Si el hospital quiere una espera más corta, el sistema pide más personal.» Devuelvan el control a 15."),
    ("Abran «¿Y si cambia el clima o la demanda?». ", "Pongan lluvia en 25 mm y demanda reciente en 140 %. Aparece una curva morada y el texto dice «+38 % de pacientes» (unos 82 en el día, frente a 62). Qué decir: «Si el día fuera más lluvioso y con más demanda, el modelo esperaría casi cuarenta por ciento más pacientes.» Pulsen «Restablecer escenario»."),
    ("Pulsen «Descargar plan del día (CSV)». ", "Se baja un archivo con el pronóstico, el rango, el personal necesario y el estado de cada hora. Qué decir: «El coordinador se lleva el plan del día en un archivo que abre en Excel.»"),
    ("Pulsen «Recorrer los días». ", "El tablero avanza solo por los días de prueba. Qué decir: «Estos son los cincuenta y tres días que el modelo nunca vio al entrenar.» Detengan con el mismo botón."),
])
nota("Si alguien pregunta por qué solo hay días hasta septiembre de 2022: porque la fuente pública llega hasta ahí. Los días disponibles son los de prueba, que el modelo no vio al entrenar.")

h2("Paso 3. El asistente del paciente (1 minuto)")
lista([
    ("Pasen a la pestaña Asistente. ", "Se ve un teléfono con un chat. Siempre muestra el aviso de que no reemplaza una valoración médica."),
    ("Pulsen «Tengo gripa y tos». ", "Responde con la espera esperada a las 10:00 en cada centro: CS San Vicente 36 minutos (la más corta), Centro Hospital La Rosa 53 y Hospital Local Civil 107. Qué decir: «Para un caso leve, el asistente muestra a dónde ir. La diferencia entre el más corto y el más largo es de más de una hora.»"),
    ("Muevan «A qué hora piensas ir» o cambien el tipo de día. ", "El ranking cambia. Qué decir: «Ese promedio sale de las esperas reales de 2022 a esa hora.»"),
    ("Escriban «Me duele el pecho». ", "No compara centros: responde en rojo que llame al 123 o vaya de inmediato a la urgencia más cercana. Qué decir: «Cuando es una señal de alarma, el asistente no pierde tiempo: manda a pedir ayuda.»"),
    ("Pulsen «Empezar de nuevo» si quieren repetir. ", ""),
])

h2("Paso 4. El análisis de la demanda (45 segundos)")
lista([
    ("Pasen a la pestaña Análisis. ", "Arriba está la curva «cuando llegan más, se espera más». Elijan los tres centros con los botones y muestren que sube en todos. Debajo está el texto con la correlación y la prueba de permutación."),
    ("Bajen a la tabla por triage ", "para mostrar que triage IV y V esperan una mediana de 79 y 82 minutos, frente a 37 en triage III."),
    ("Bajen a «Llegadas por día». ", "Muestren el hueco de un año y el salto de mayo de 2022. Qué decir: «Estas dos cosas cambiaron cómo diseñamos el modelo.»"),
])

h2("Paso 5. La documentación técnica y las evidencias (1 minuto)")
lista([
    ("Abran la pestaña proyecto.html. ", "Vayan a la sección «Pruebas, orquestación y base de datos»: muestra 150 de 293 pruebas, la cobertura, la corrida de Airflow con la duración de cada tarea y los tiempos de las consultas con y sin índice."),
    ("Abran la pestaña de Airflow ", "con la corrida en verde. Qué decir: «Las siete tareas corrieron completas en unos nueve minutos.»"),
    ("Si quieren, ", "abran http://localhost:8000/docs para mostrar la documentación de la API y ejecuten ahí /api/pronostico."),
    ("Terminal: ", "ejecuten PYTHONPATH=src pytest tests -q solo si les sobra tiempo (tarda cerca de un minuto). Si no, basta con mencionar el resultado."),
])
nota("Si el jurado pide ver que no son datos inventados: abran https://www.datos.gov.co, busquen «Clasificación en Triage Urgencias» y muestren que es el mismo conjunto, con identificador vt5n-eu2r.")

h2("Cómo explicarle al jurado la segunda página (proyecto.html)")
p("Esta página no es para el cliente sino para el jurado: reúne las evidencias de todo lo que se dijo en la presentación. Se puede usar de dos formas.")
h3("Versión completa (1 minuto y medio)")
for par in [
    "Además de la aplicación, construimos esta segunda página, y no es para el cliente sino para ustedes. La hicimos porque un sistema que dice que funciona tiene que poder demostrarlo.",
    "Aquí no hay nada escrito a mano. Las cifras se leen directamente de la base de datos y de los resultados de las pruebas, así que si el sistema cambia, la página cambia con él.",
    "Empieza con el problema y con nuestros criterios de éxito, cada uno con su resultado real. Ahí se ve también lo que no cumplimos, que es la meta de ochenta y cinco por ciento por franja de tres horas. Lo dejamos a la vista a propósito, porque preferimos que ustedes lo vean a que parezca que todo salió perfecto.",
    "Después están los datos, de dónde vienen y cómo comprobamos que cada fila quedó explicada. Sigue el hallazgo y el modelo, con la comparación contra los métodos simples. Luego la arquitectura, donde se puede tocar cada paso para ver qué entra, qué sale y en qué archivo está el código.",
    "La sección de calidad es la que más nos importa: muestra las pruebas automáticas, la corrida completa de Airflow con lo que tardó cada tarea y los tiempos de las consultas antes y después del índice. Está también el modelo financiero con precios de proveedores reales.",
    "Y al final, los tres niveles de prototipo y el formulario de la prueba de usabilidad. Cualquier persona que pruebe la aplicación lo responde ahí mismo, se guarda de forma anónima y el resultado aparece en la misma página. Si todavía no hay sesiones, la página lo dice y no inventa cifras.",
]:
    p(par)
h3("Versión corta (20 segundos)")
p("Esta segunda página es la evidencia. Todo lo que dijimos en la presentación se puede comprobar aquí: los resultados contra nuestros criterios, las pruebas, la corrida de Airflow, los tiempos de las consultas y la prueba de usabilidad. Las cifras no están escritas a mano: salen de la base y de los resultados reales.")
h3("Si la usan en vivo: qué abrir y en qué orden (menos de un minuto)")
lista([
    ("Resultados frente a nuestros criterios (arriba): ", "muestra el visto bueno o la cruz de cada meta."),
    ("Datos: ", "la cuenta que cuadra, 89.453 menos las repetidas igual a 79.521."),
    ("Arquitectura: ", "toquen un paso, por ejemplo el ETL o la base, para que vean que se abre el detalle."),
    ("Calidad: ", "las pruebas, la corrida de Airflow con las siete tareas y los tiempos con y sin índice."),
    ("Usuarios: ", "el formulario, si van a hacer la prueba ahí mismo."),
], numerada=True)
h3("Preguntas que pueden salir sobre esta página")
for q, a in [
    ("¿Por qué una segunda página?", "Porque la primera es el producto para quien lo usa, y esta es para quien lo evalúa. Mezclarlas haría la aplicación más pesada y menos clara."),
    ("¿Las cifras son reales o están puestas a mano?", "Son reales. La página las pide a la base de datos y a los archivos de resultados, y cualquiera las puede comprobar corriendo el sistema."),
    ("¿Por qué aparece algo que no cumplieron?", "Porque una evaluación honesta muestra también lo que no se logró. Lo importante es que entendemos por qué y qué haríamos para mejorarlo."),
    ("¿Por qué dice que no hay sesiones de usabilidad? (solo si todavía no las han hecho)", "Porque no queremos mostrar resultados que no existen. El formulario está listo y apenas cinco personas lo respondan, el resultado se calcula solo."),
]:
    mixto([(q, True)])
    p(a)

# ====================================================================== 6. preguntas
h1("6. Preguntas probables del jurado y cómo responder")
p("Respondan corto, en dos o tres frases, y paren. Si no saben algo, digan «eso no lo medimos» y expliquen qué harían; es mejor que inventar.", cursiva=True)

preguntas = [
    ("¿Por qué usaron datos de Pasto y no de Cali?",
     "Porque buscamos datos de Cali y lo único público es un conjunto de diagnósticos de 2019 sin horas, que no sirve para pronosticar por hora. El de Pasto es el único que encontramos con hora de llegada, triage y hora de atención. El método sirve para cualquier hospital que tenga esos tres datos, y el siguiente paso es probarlo con uno de Cali."),
    ("¿Los datos son reales o simulados?",
     "Reales. En una entrega anterior el prototipo usaba datos simulados, y ahora todo viene de datos.gov.co: se pueden comprobar con el identificador del conjunto de datos. Lo único que no es medido es el precio del plan, que es una propuesta."),
    ("¿Por qué no cumplieron la meta del 85 %?",
     "Porque la fijamos antes de ver los datos y los centros son pequeños: con pocos pacientes por hora, hay un ruido que ningún modelo elimina. Por día sí se alcanza. Preferimos reportarlo así a cambiar la meta o la forma de medir."),
    ("¿Por qué un modelo de Poisson y no una red neuronal?",
     "Porque son conteos pequeños por hora y solo tenemos unos dieciséis meses de historia continua, que es poco para que una red neuronal supere a un modelo sencillo. El de Poisson además se puede explicar y se entrena en segundos. Probar modelos más complejos es trabajo futuro, y lo medimos contra tres referencias simples para saber si lo complejo vale la pena."),
    ("¿Cómo evitaron usar datos del futuro al entrenar?",
     "Con tres cosas. El modelo se reentrena cada semana usando solo lo anterior. Los parámetros se eligieron en una ventana de validación distinta a la de prueba. Y hay una prueba automática que cambia los datos del futuro y verifica que los pronósticos anteriores no cambian."),
    ("¿El clima sirve de algo?",
     "Casi nada para la precisión: con y sin clima la diferencia es de décimas. Lo dejamos porque permite probar escenarios, pero no lo vendemos como lo que mejora el modelo."),
    ("¿El personal recomendado es correcto?",
     "Es una recomendación bajo supuestos: llegadas de Poisson, un tiempo de atención por paciente que define quien usa la herramienta y una espera objetivo. No tenemos el personal real de cada turno, así que no pudimos calibrarlo; por eso es el usuario quien fija la meta."),
    ("¿Qué hace el asistente? ¿Da diagnósticos?",
     "No. Son reglas simples: si detecta una señal de alarma, manda a llamar al 123; si es un caso leve, muestra la espera típica de cada centro a esa hora. Siempre dice que no reemplaza una valoración médica."),
    ("¿Qué pasa con la privacidad de los pacientes?",
     "La fuente es pública y no trae datos de identificación: solo la administradora, las fechas y horas, el triage y la IPS. La prueba de usabilidad es anónima. Si se usa con un hospital real habría que firmar un acuerdo de tratamiento de datos y cumplir la Ley 1581 de 2012."),
    ("¿Cómo garantizan la calidad de los datos?",
     "Con reglas explícitas al cargar, una huella única por fila para no duplicar, restricciones dentro de la base de datos y una cuenta de conciliación en cada carga: lo que bajó menos lo repetido y lo rechazado tiene que ser igual a lo que quedó. Todo queda registrado, incluso lo que falla."),
    ("¿Qué pasa si el modelo se equivoca o la carga falla?",
     "La carga se frena si no concilia, la tarea se reintenta dos veces con espera creciente, y el modelo nuevo no se publica si pierde contra la referencia simple. El tablero siempre muestra el rango probable, no solo un número."),
    ("¿Para qué sirve Airflow aquí?",
     "Para que el flujo corra solo cada día en el orden correcto, con reintentos y con controles entre tareas. Hicimos una corrida completa de siete tareas que terminó bien en unos nueve minutos."),
    ("¿Cómo escala a más hospitales?",
     "El esquema ya separa a cada centro y se entrena un modelo por centro. Agregar un hospital es cargar sus datos con el mismo flujo. Lo que cambia es la conexión con su sistema de información, que sería lo primero del piloto."),
    ("¿Por qué eligieron franjas de tres horas?",
     "Porque el personal se organiza por bloques de horas y no por hora exacta, y porque por hora hay mucho ruido: la precisión por hora es de unos cincuenta por ciento y por franja de tres horas sube a unos setenta."),
    ("¿Qué significa «precisión» en sus resultados?",
     "Es uno menos el error porcentual absoluto ponderado. Si en un día llegaron cien pacientes y el modelo se equivoca en total por quince, la precisión es ochenta y cinco por ciento."),
    ("¿A qué se debe el salto de mayo de 2022?",
     "No lo sabemos: la fuente no lo explica, puede ser un cambio en cómo se registra. Por eso el modelo usa el nivel de la última semana en lugar de la historia completa. Es una limitación que declaramos."),
    ("¿Quién paga y por qué? ¿El precio está validado?",
     "Paga el hospital, porque es el que gasta en horas extra. Los costos son de proveedores reales, pero el precio del plan es una propuesta que todavía no hemos validado con un cliente; eso es parte del piloto."),
    ("¿Validaron con usuarios?",
     "[Respondan con lo que de verdad hicieron.] Tenemos el protocolo: cinco tareas y el cuestionario SUS dentro de la página, anónimo, con meta de sesenta y ocho. Si ya hicieron sesiones, den el número de personas, el promedio y un cambio que hicieron por lo que vieron. Si no, digan que están en curso."),
    ("¿Qué aporta frente a lo que ya existe?",
     "Junta en un solo sistema reproducible el pronóstico, su traducción a personal y la orientación al paciente, con una evaluación honesta contra referencias simples y todo verificable con datos abiertos."),
    ("¿Cómo sabemos que no es una maqueta?",
     "Se puede ver: la aplicación consulta una base de datos real, hay más de cien pruebas automáticas que se ejecutan en vivo, una corrida completa en Airflow, el plan de ejecución de las consultas y el repositorio con el código."),
    ("¿Qué harían distinto o qué sigue?",
     "Conseguir datos de un hospital de Cali con el personal por turno, usar un pronóstico del clima en lugar del observado, probar con coordinadores reales y hacer un piloto de tres meses. También conectar el asistente a WhatsApp."),
]
for i, (q, a) in enumerate(preguntas, 1):
    mixto([(f"{i}. {q}", True)])
    if a.startswith("["):
        nota(a)
    else:
        p(a)

# ====================================================================== 7. cifras
h1("7. Cifras para tener en la cabeza")
tabla(["Dato", "Valor"], [
    ["Atenciones analizadas", "79.521 (89.453 bajadas − 9.932 repetidas − 0 rechazadas)"],
    ["Periodo de los datos", "2020 a septiembre de 2022; modelo entrenado desde abril de 2021"],
    ["Espera de la mitad de los pacientes", "39 minutos; uno de cada diez espera más de 138"],
    ["Quién espera más de dos horas", "14 % de las atenciones"],
    ["Relación llegadas y espera", "Spearman entre 0,23 y 0,37, p menor que 0,001"],
    ["Triage IV y V frente a III", "79 a 82 minutos de mediana frente a 37"],
    ["Días de prueba", "53 (del 8 de agosto al 29 de septiembre de 2022)"],
    ["Precisión por franja de 3 h", "71 %, 70 % y 74 % según el centro (meta: 85 %)"],
    ["Precisión por día", "85 % a 87 %"],
    ["Mejora frente a la mejor referencia (3 h)", "+3,4 (La Rosa), +2,6 (San Vicente), +1,2 (Hospital Local Civil, no concluyente)"],
    ["Rango probable del 80 %", "Cubre entre 87 % y 90 % de las horas"],
    ["Pruebas automáticas", "293, todas pasan; cobertura 89,1 %"],
    ["Velocidad de la API", "Percentil 95 de 68 ms en 240 peticiones"],
    ["Índice en la base", "La consulta del modelo es 5,6 veces más rápida"],
    ["Airflow", "7 tareas, corrida completa en unos 9 minutos"],
    ["Costo fijo mensual", "$901.237"],
    ["Costo variable por cliente", "$270.016 al mes"],
    ["Plan Completo", "$0,78 millones al mes, sin IVA"],
    ["Punto de equilibrio", "2 clientes"],
    ["Inversión hasta la versión Beta", "$86,3 millones"],
], [6.2, 9.8])

h1("8. Tres consejos finales")
lista([
    "Si algo del tablero tarda, no se queden callados: sigan hablando del siguiente paso mientras carga.",
    "Cuando respondan una pregunta técnica, empiecen por la decisión («usamos tal cosa») y después por la razón.",
    "No defiendan lo que no cumplieron: nombren la meta, el resultado real y lo que aprendieron. Eso suma más que esconderlo.",
])

doc.save(SALIDA)
print("listo", SALIDA)
