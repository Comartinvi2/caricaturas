"""Recordatorio a quien generó su caricatura, dejó el email y no la pidió.

Unas 20 h después le escribimos una sola vez con sus visualizaciones y un descuento
del REMINDER_PCT % válido 24 h. El descuento va en el enlace, firmado con ADMIN_TOKEN,
y se comprueba en el servidor al crear el pago: no hace falta crear cupones en Stripe.
"""
import asyncio
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import config, storage

log = logging.getLogger("caricaturas.reminder")

REMINDER_PCT = 10
AFTER_H, UNTIL_H = 18, 40   # se escribe a quien generó hace entre 18 y 40 horas
VALID_H = 24                # el descuento dura 24 h desde el correo


def sign(email: str, exp: int) -> str:
    key = (config.ADMIN_TOKEN or "").encode()
    return hmac.new(key, f"{email.strip().lower()}|{exp}".encode(), hashlib.sha256).hexdigest()[:20]


def token(email: str, now: float | None = None) -> str:
    exp = int((now or time.time()) + VALID_H * 3600)
    return f"{exp}.{sign(email, exp)}"


def discount_pct(meta: dict | None, tok: str, now: float | None = None) -> int:
    """% de descuento si el token es válido para el email de esta caricatura y no ha caducado."""
    try:
        exp_s, sig = str(tok or "").split(".", 1)
        exp = int(exp_s)
    except ValueError:
        return 0
    email = (meta or {}).get("email") or ""
    if not config.ADMIN_TOKEN or not email or (now or time.time()) > exp:
        return 0
    return REMINDER_PCT if hmac.compare_digest(sig, sign(email, exp)) else 0


def pending(rows: list[dict], now: float | None = None) -> list[dict]:
    """Agrupa por email las caricaturas sin pagar, de 18-40 h, sin recordatorio. Pura, para poder probarla."""
    now = now or time.time()
    groups: dict[str, dict] = {}
    for r in rows:
        m = r.get("meta") or {}
        email, created = (m.get("email") or "").strip().lower(), m.get("created") or 0
        if not email or m.get("paid") or m.get("reminded") or m.get("status") not in ("previewed", "checkout"):
            continue
        if not (AFTER_H * 3600 <= now - created <= UNTIL_H * 3600):
            continue
        g = groups.setdefault(email, {"email": email, "jobs": [], "scene": m.get("scene") or "", "created": 0})
        g["jobs"].append(r["job_id"])
        if created > g["created"]:
            g["created"], g["scene"] = created, m.get("scene") or g["scene"]
    # si esa persona ya pagó otra caricatura, no se le escribe
    paid = {(r.get("meta") or {}).get("email", "").strip().lower() for r in rows if (r.get("meta") or {}).get("paid")}
    return [g for e, g in groups.items() if e not in paid]


def _rows() -> list[dict]:
    if not storage.SB_ON:
        return []
    since = (datetime.now(timezone.utc) - timedelta(hours=UNTIL_H + 12)).isoformat()
    r = httpx.get(f"{storage.SB_URL}/rest/v1/car_orders", headers=storage._h(), timeout=30,
                  params={"select": "job_id,meta", "updated_at": f"gt.{since}", "limit": "1000"})
    return r.json() if r.status_code == 200 else []


async def run_once() -> int:
    from . import catalog, mail
    sent = 0
    for g in pending(await asyncio.to_thread(_rows)):
        title = ((await catalog.get_product(g["scene"])) or {}).get("title") or "tu caricatura"
        link = f"{config.BASE_URL}/p/{g['scene']}?v={','.join(g['jobs'])}&d={token(g['email'])}"
        ok = await mail.reminder(g["email"], title, link, [f"{config.BASE_URL}/api/preview/{j}.jpg" for j in g["jobs"]], REMINDER_PCT)
        for j in g["jobs"]:   # se marca aunque falle el envío: una sola vez, nunca en bucle
            meta = storage.read_meta(j)
            if meta is not None:
                meta.update(reminded=time.time(), reminder_ok=bool(ok))
                storage.write_meta(j, meta); storage._sb_save(j, meta)
        sent += 1 if ok else 0
    return sent


async def loop() -> None:
    while True:
        try:
            n = await run_once()
            if n:
                log.info("recordatorios enviados: %d", n)
        except Exception:  # noqa: BLE001
            log.exception("recordatorios: fallo")
        await asyncio.sleep(1800)
