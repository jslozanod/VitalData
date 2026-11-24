"""Extraccion desde la API de datos abiertos (Socrata). Con reintentos y con el token por variable de entorno."""
from __future__ import annotations

import logging
import time
from typing import Iterator

import httpx

from vitaldata import config

log = logging.getLogger("vitaldata.extract")


class ExtractError(RuntimeError):
    pass


class SocrataClient:
    def __init__(self, base: str = config.SOCRATA_BASE, token: str | None = config.SOCRATA_APP_TOKEN,
                 timeout: float = 180, max_retries: int = 4, backoff: float = 2.0,
                 client: httpx.Client | None = None):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._headers = {"X-App-Token": token} if token else {}   # el token nunca se escribe en los logs
        self._client = client or httpx.Client(timeout=timeout)

    def get(self, dataset: str, params: dict | None = None) -> list[dict]:
        url = f"{self.base}/{dataset}.json"
        ultimo = None
        for intento in range(1, self.max_retries + 1):
            try:
                r = self._client.get(url, params=params, headers=self._headers)
                if r.status_code == 200:
                    datos = r.json()
                    if not isinstance(datos, list):
                        raise ExtractError(f"Respuesta inesperada de {dataset}: {str(datos)[:120]}")
                    return datos
                if r.status_code in (429, 500, 502, 503, 504):
                    ultimo = f"HTTP {r.status_code}"
                else:
                    raise ExtractError(f"HTTP {r.status_code} en {dataset}: {r.text[:160]}")
            except (httpx.TimeoutException, httpx.TransportError) as e:
                ultimo = type(e).__name__
            espera = self.backoff ** intento
            log.warning("Intento %s/%s fallo (%s). Reintento en %.0f s", intento, self.max_retries, ultimo, espera)
            time.sleep(espera)
        raise ExtractError(f"No se pudo leer {dataset} despues de {self.max_retries} intentos ({ultimo})")

    def paginas(self, dataset: str, params: dict | None = None, page_size: int = 50000,
                max_filas: int | None = None) -> Iterator[list[dict]]:
        """Pagina con $limit y $offset ordenando por :id para que las paginas no se solapen."""
        offset = 0
        base = dict(params or {})
        base["$order"] = ":id"
        while True:
            lote = self.get(dataset, {**base, "$limit": page_size, "$offset": offset})
            if not lote:
                return
            yield lote
            offset += len(lote)
            if len(lote) < page_size or (max_filas and offset >= max_filas):
                return


def extraer_triage(cliente: SocrataClient, desde: str | None = None) -> list[dict]:
    """Atenciones de urgencias. Si se pasa `desde` (YYYY-MM-DD) solo trae lo nuevo, para cargas incrementales."""
    params = {}
    if desde:
        params["$where"] = f"fecha_ing >= '{desde}T00:00:00'"
    filas: list[dict] = []
    for pagina in cliente.paginas(config.DS_TRIAGE, params):
        filas.extend(pagina)
    return filas


def extraer_clima_diario(cliente: SocrataClient, dataset: str, estacion: str, desde: str, hasta: str,
                         agregados: str) -> list[dict]:
    """Agrega por dia en el servidor (un mes por peticion) para no bajar millones de observaciones."""
    import pandas as pd

    filas: list[dict] = []
    for ini in pd.date_range(desde, hasta, freq="MS"):
        fin = ini + pd.offsets.MonthBegin(1)
        params = {
            "$select": f"date_trunc_ymd(fechaobservacion) as dia, {agregados}, count(*) as n",
            "$where": f"codigoestacion='{estacion}' AND fechaobservacion >= '{ini:%Y-%m-%d}T00:00:00' "
                      f"AND fechaobservacion < '{fin:%Y-%m-%d}T00:00:00'",
            "$group": "dia",
            "$order": "dia",
            "$limit": 40,
        }
        filas.extend(cliente.get(dataset, params))
    return filas
