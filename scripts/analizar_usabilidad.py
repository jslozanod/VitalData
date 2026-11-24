"""Resume las pruebas de usabilidad guardadas en la base: SUS por persona, promedio con intervalo y tareas logradas."""
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sqlalchemy import text  # noqa: E402

from vitaldata.api.service import sus_puntaje  # noqa: E402
from vitaldata.etl import load  # noqa: E402

eng = load.get_engine()
with eng.connect() as con:
    filas = con.execute(text("""SELECT s.sesion_id, s.rol, s.tareas_ok, s.tareas_total, s.segundos, s.comentario,
                                u.q1,u.q2,u.q3,u.q4,u.q5,u.q6,u.q7,u.q8,u.q9,u.q10
                                FROM vd.usabilidad_sesion s JOIN vd.usabilidad_sus u USING (sesion_id) ORDER BY s.creada""")).all()
if not filas:
    print("Todavia no hay sesiones. Hagan la prueba con 5 personas (docs/usabilidad/protocolo.md).")
    sys.exit(0)
sus = [sus_puntaje([getattr(f, f"q{i}") for i in range(1, 11)]) for f in filas]
n = len(sus)
media = statistics.mean(sus)
ee = statistics.stdev(sus) / math.sqrt(n) if n > 1 else 0.0
print(f"Personas: {n}")
for f, s in zip(filas, sus):
    print(f"  {f.rol:12s} SUS {s:5.1f}  tareas {f.tareas_ok}/{f.tareas_total}  {f.segundos // 60}:{f.segundos % 60:02d}  {f.comentario or ''}")
print(f"SUS promedio: {media:.1f}  (IC 95 %: {media - 1.96 * ee:.1f} a {media + 1.96 * ee:.1f})")
print(f"Tareas logradas: {sum(f.tareas_ok for f in filas) / sum(f.tareas_total for f in filas):.0%}")
print(f"Tiempo mediano: {statistics.median(f.segundos for f in filas) / 60:.1f} min")
print("Interpretacion: 68 = promedio de la industria; mas de 80 = muy bueno." + ("  (con menos de 5 personas es solo una senal)" if n < 5 else ""))
