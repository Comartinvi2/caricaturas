"""Moneda de la visita: la ficha y Stripe usan el mismo importe (19-nov, María: «haz que casen con los de stripe»)."""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import catalog, config, fulfilment, main, market, storage


def scenes(monkeypatch, country):
    async def get_catalog(): return [], []
    monkeypatch.setattr(catalog, "get_catalog", get_catalog)
    return TestClient(main.app).get("/api/scenes", headers={"cf-ipcountry": country}).json()


def checkout(monkeypatch, product, country, pct=0):
    calls = []
    fake = SimpleNamespace(StripeError=Exception, checkout=SimpleNamespace(Session=SimpleNamespace(
        create=lambda **p: calls.append(p) or SimpleNamespace(id="cs_1", url="https://pay"))))
    monkeypatch.setattr(config, "PAYMENTS_ENABLED", True)
    monkeypatch.setattr(fulfilment, "stripe_client", lambda: fake)
    monkeypatch.setattr(storage, "update_meta", lambda *a, **k: None)
    monkeypatch.setattr(storage, "persist", lambda *a, **k: None)
    fulfilment.create_checkout("job1", product, country=country, pct=pct)
    return calls[-1]


def test_precios_redondos():
    assert [market.to_local(990, c) for c in ("eur", "usd", "mxn", "clp")] == [990, 1190, 19900, 9990]
    assert market.fmt(1190, "usd") == "$11.90 USD" and market.fmt(19900, "mxn") == "$199 MXN"


def test_ficha_y_stripe_cobran_lo_mismo(monkeypatch):
    for country, cur in (("US", "usd"), ("MX", "mxn"), ("CL", "clp"), ("ES", "eur"), ("", "eur")):
        d = scenes(monkeypatch, country)
        shown = {p["id"]: p["cents"] for p in d["products"]}
        assert d["currency"] == cur
        p = checkout(monkeypatch, "digital", country)
        li = p["line_items"][0]["price_data"]
        assert li["currency"] == cur and li["unit_amount"] == shown["digital"]
        assert ("adaptive_pricing" in p) == (cur == "eur") and p["metadata"]["eur_cents"] == "990"


def test_lienzo_en_dolares_y_descuento_igual_que_la_ficha(monkeypatch):
    shown = {p["id"]: p["cents"] for p in scenes(monkeypatch, "US")["products"]}
    p = checkout(monkeypatch, "canvas_30x40", "US", pct=10)
    assert p["line_items"][0]["price_data"]["unit_amount"] == round(shown["canvas_30x40"] * 90 / 100)  # = Math.round del JS
    assert p["line_items"][0]["price_data"]["currency"] == "usd"


def test_portada_y_colecciones_en_la_moneda_de_la_visita(monkeypatch):
    prods = [{"slug": "motero", "title": "Motero", "short_desc": "x", "image_url": "", "collections": ["boda"], "bestseller": True}]
    cols = [{"slug": "boda", "title": "Boda", "h1": "Boda", "intro": ""}, {"slug": "todas", "title": "Todas", "h1": "Todas", "intro": ""}]
    async def get_catalog(): return prods, cols
    monkeypatch.setattr(catalog, "get_catalog", get_catalog)
    c = TestClient(main.app)
    desde = market.fmt(market.to_local(config.PRICE_CANVAS_20x30_CENTS, "usd"), "usd")
    for path in ("/", "/coleccion/boda", "/regalos/todas"):
        us = c.get(path, headers={"cf-ipcountry": "US"}).text
        assert f"desde {desde}" in us and "€" not in us.split("<body")[1].split("<script")[0], path
        assert "MXN" in c.get(path, headers={"cf-ipcountry": "MX"}).text
        assert "€" in c.get(path, headers={"cf-ipcountry": "ES"}).text


def test_correo_con_lo_que_pago(monkeypatch):
    from app import mail
    sent = []
    async def send(to, subject, paragraphs, button=None, items=None): sent.append(items); return True
    monkeypatch.setattr(mail, "send", send)
    import asyncio
    asyncio.run(mail.order_confirmed("j", {"email": "a@b.c"}, "Lámina", 990, True, "$199 MXN"))
    assert sent[0][0]["text"] == "$199 MXN"
