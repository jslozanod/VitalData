"""Escoge los hiperparametros del modelo en una ventana de VALIDACION (13 de junio a 7 de agosto de 2022).
El periodo de prueba (desde el 8 de agosto) no se toca aqui: solo se usa una vez, al final, en publicar_modelos.py."""
import itertools
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from vitaldata import config  # noqa: E402
from vitaldata.etl import load  # noqa: E402
from vitaldata.models import backtest, data  # noqa: E402

VAL_INI, VAL_FIN = "2022-06-13", "2022-08-07"
ALPHAS = [1e-4, 1e-2]
PESOS = [0.0, 0.01, 0.02, 0.04]

eng = load.get_engine()
ips_lista = pd.read_sql("""SELECT i.nombre FROM vd.dim_ips i JOIN vd.fact_atencion f USING (ips_id)
                           GROUP BY i.nombre HAVING count(*) >= %(m)s ORDER BY 1""", eng, params={"m": config.MIN_REGISTROS_IPS})["nombre"].tolist()
series = {i: data.preparar(eng, i, usar_clima=True) for i in ips_lista}
filas = []
for a, w in itertools.product(ALPHAS, PESOS):
    prec = []
    for i in ips_lista:
        r = backtest.correr(eng, i, test_inicio=VAL_INI, test_fin=VAL_FIN, alpha=a, peso_reciente=w,
                            con_sin_clima=False, d=series[i])
        prec.append(r["metricas"]["3h"]["vitaldata"]["wape"])
    filas.append({"alpha": a, "peso_reciente": w, "wape_3h_medio": round(sum(prec) / len(prec), 4),
                  **{f"wape_3h_{i}": round(p, 4) for i, p in zip(ips_lista, prec)}})
    print(filas[-1], flush=True)
tabla = pd.DataFrame(filas).sort_values("wape_3h_medio")
mejor = tabla.iloc[0]
salida = {"alpha": float(mejor["alpha"]), "peso_reciente": float(mejor["peso_reciente"]),
          "ventana_validacion": [VAL_INI, VAL_FIN], "criterio": "WAPE medio por franja de 3 horas"}
(RAIZ / "src" / "vitaldata" / "models" / "hiperparametros.json").write_text(json.dumps(salida, indent=2), encoding="utf-8")
(RAIZ / "docs" / "evidencias").mkdir(parents=True, exist_ok=True)
tabla.to_csv(RAIZ / "docs" / "evidencias" / "tuning_validacion.csv", index=False)
print("elegido:", salida)
