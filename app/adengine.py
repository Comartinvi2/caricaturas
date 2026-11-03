"""Avisa a AdEngine de cada pago cobrado, con los identificadores del clic del anuncio guardados en el pago de Stripe.
AdEngine apunta la venta y se la pasa a Google (gclid) y a Meta (API de conversiones). Sin ADENGINE_SALES_URL/ADENGINE_KEY no hace nada."""
import httpx

from . import config


def clicks(cookies) -> dict:
    """Identificadores del clic del anuncio que tiene el navegador: gclid (lo guarda base.html) y _fbc/_fbp (los pone el píxel de Meta)."""
    out = {"gclid": cookies.get("ae_gclid"), "fbc": cookies.get("_fbc"), "fbp": cookies.get("_fbp")}
    return {k: v[:490] for k, v in out.items() if v}


async def report_sale(s: dict):
    url, key = config.env("ADENGINE_SALES_URL"), config.env("ADENGINE_KEY")
    if not url or not key:
        return
    md = s.get("metadata") or {}
    body = {"orderId": s.get("client_reference_id") or md.get("job_id"), "amount": (s.get("amount_total") or 0) / 100,
            "currency": (s.get("currency") or "eur").upper(), "email": (s.get("customer_details") or {}).get("email"),
            "gclid": md.get("gclid"), "fbc": md.get("fbc"), "fbp": md.get("fbp"), "url": f"{config.BASE_URL}/gracias"}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(url, json=body, headers={"x-adengine-key": key})
            if r.status_code >= 400:
                print("AdEngine rechazó la venta:", r.status_code, r.text[:200])
    except Exception as e:
        print("AdEngine no respondió:", e)
