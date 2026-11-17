"""Lámina para imprimir a 300 ppp de verdad: la caricatura (1152x1536) se amplía con IA (Real-ESRGAN en Replicate).

Solo para pedidos pagados. Sin REPLICATE_API_TOKEN, o si Replicate falla, se entrega el archivo original como hasta ahora.
"""
import io
import logging
import time

import httpx
from PIL import Image

from . import config, storage

log = logging.getLogger(__name__)
API = "https://api.replicate.com/v1"
VERSION = config.env("REPLICATE_UPSCALE_VERSION", "42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b")  # nightmareai/real-esrgan
A4_LONG_PX = 3508   # lado largo de un A4 (297 mm) a 300 ppp
NAME = "result-300.png"


def enabled() -> bool:
    return bool(config.env("REPLICATE_API_TOKEN"))


def to_300ppp(big: Image.Image) -> Image.Image:
    """Lo ampliado (x4) se deja en tamaño A4 a 300 ppp: el lado largo mide 3508 píxeles. Pura."""
    k = A4_LONG_PX / max(big.size)
    return big.resize((round(big.width * k), round(big.height * k)), Image.LANCZOS) if k < 1 else big


def replicate_x4(png: bytes) -> bytes:
    h = {"Authorization": f"Bearer {config.env('REPLICATE_API_TOKEN')}"}
    with httpx.Client(timeout=120) as c:
        f = c.post(f"{API}/files", headers=h, files={"content": ("caricatura.png", png, "image/png")})
        f.raise_for_status()
        p = c.post(f"{API}/predictions", headers={**h, "Prefer": "wait=60"},
                   json={"version": VERSION, "input": {"image": f.json()["urls"]["get"], "scale": 4, "face_enhance": False}}).json()
        for _ in range(60):
            if p.get("status") in ("succeeded", "failed", "canceled"):
                break
            time.sleep(2)
            p = c.get(p["urls"]["get"], headers=h).json()
        if p.get("status") != "succeeded":
            raise RuntimeError(f"Replicate: {p.get('status')} {p.get('error')}")
        out = p["output"] if isinstance(p["output"], str) else p["output"][0]
        return c.get(out).content


def digital_file(job_id: str) -> bytes | None:
    """PNG a 300 ppp para la descarga (se guarda para no ampliar dos veces), o None si no se puede."""
    cached = storage.ensure_file(job_id, NAME)
    if cached.exists():
        return cached.read_bytes()
    if not enabled():
        return None
    try:
        src = storage.ensure_file(job_id, "result.png").read_bytes()
        img = to_300ppp(Image.open(io.BytesIO(replicate_x4(src))).convert("RGB"))
        buf = io.BytesIO(); img.save(buf, format="PNG", dpi=(300, 300)); data = buf.getvalue()
        storage.keep(job_id, NAME, data, "image/png")
        return data
    except Exception as e:  # noqa: BLE001
        log.warning("ampliación de %s falló: %s", job_id, e)
        return None
