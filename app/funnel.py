"""Embudo propio sin cookies: solo totales por día y paso.

No guarda IP, identificadores ni nada en el navegador, así que no necesita
consentimiento (LSSI 22.2). Los contadores viven en memoria y se copian cada
minuto a un archivo privado de Supabase Storage (y al apagar).
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from . import storage

log = logging.getLogger("caricaturas.funnel")

STEPS = ["ficha", "generar", "generada", "vista", "email", "pedir", "venta"]
BASE = {"generar": "ficha", "email": "generar", "generada": "generar", "vista": "generada", "pedir": "vista", "venta": "pedir"}  # para el %
CLIENT_STEPS = {"vista"}  # los que avisa el navegador; el resto los cuenta el servidor
_BOT = re.compile(r"bot|crawl|spider|slurp|preview|facebookexternalhit|headless|lighthouse|curl|wget|python|httpx", re.I)
_PATH = "stats/embudo.json"
_counts: dict[str, dict[str, int]] = {}
_dirty = False
_loaded = False  # no se guarda nada hasta haber leído lo anterior (para no pisarlo)


def is_bot(ua: str | None) -> bool:
    return not ua or bool(_BOT.search(ua))


def hit(step: str) -> None:
    global _dirty
    day = _counts.setdefault(datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d"), {})
    day[step] = day.get(step, 0) + 1
    _dirty = True


def counts() -> dict[str, dict[str, int]]:
    return _counts


def _url() -> str:
    return f"{storage.SB_URL}/storage/v1/object/{storage.BUCKET}/{_PATH}"


def load() -> None:
    global _loaded
    if not storage.SB_ON:
        return
    try:
        r = httpx.get(_url(), headers=storage._h(), timeout=30)
        if r.status_code in (400, 404) and "not found" in r.text.lower():
            _loaded = True  # aún no existe
        if r.status_code == 200:
            _loaded = True
            for d, steps in r.json().items():  # suma lo guardado a lo contado mientras arrancaba
                for k, n in steps.items():
                    _counts.setdefault(d, {})[k] = _counts.get(d, {}).get(k, 0) + n
    except Exception:
        log.exception("no se pudo leer el embudo")


def save() -> None:
    global _dirty
    if not storage.SB_ON or not _dirty or not _loaded:
        return
    _dirty = False
    for d in sorted(_counts)[:-120]:  # guarda 4 meses
        _counts.pop(d, None)
    try:
        h = storage._h("application/json"); h["x-upsert"] = "true"
        httpx.post(_url(), headers=h, content=json.dumps(_counts), timeout=30)
    except Exception:
        _dirty = True
        log.exception("no se pudo guardar el embudo")


async def loop() -> None:
    await asyncio.to_thread(load)
    while True:
        await asyncio.sleep(60)
        if not _loaded:
            await asyncio.to_thread(load)
        await asyncio.to_thread(save)
