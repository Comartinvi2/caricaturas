"""Qué ve cada país: México/Chile solo la caricatura para imprimir; EE. UU. envío a EE. UU.; España como siempre."""
import pytest
from fastapi.testclient import TestClient

from app import catalog, fulfilment, main, market

SCENE = {"slug": "caricatura-motero-40-cumpleanos", "title": "Motero 40", "short_desc": "Para moteros", "images": [], "collections": []}


@pytest.fixture
def page(monkeypatch):
    async def get_product(slug): return SCENE
    async def get_catalog(): return [], []
    monkeypatch.setattr(catalog, "get_product", get_product)
    monkeypatch.setattr(catalog, "get_catalog", get_catalog)
    c = TestClient(main.app)

    def get(country=None):
        r = c.get("/p/" + SCENE["slug"], headers={"cf-ipcountry": country} if country else {})
        assert r.status_code == 200
        return r.text
    return get


def test_mercado_por_pais():
    assert [market.market(c) for c in ("MX", "cl", "US", "PR", "ES", "", None)] == ["digital", "digital", "us", "us", "es", "es", "es"]


def test_mexico_solo_para_imprimir(page):
    t = page("MX")
    assert 'const MARKET = "digital"' in t and "te llega al momento · pagas en tu moneda" in t
    assert "Envío gratuito por mensajería" not in t and "{{" not in t


def test_eeuu(page):
    t = page("US")
    assert 'const MARKET = "us"' in t and "Envío gratis a Estados Unidos y Puerto Rico" in t and "Envío gratis a EE. UU." in t


def test_espana_y_sin_cabecera_igual_que_antes(page):
    for c in ("ES", None):
        t = page(c)
        assert 'const MARKET = "es"' in t and "Envío gratuito por mensajería" in t and "· envío gratis</p>" in t


def test_impreso_desde_mexico_se_rechaza():
    impreso = next(k for k, v in fulfilment.PRODUCTS.items() if v["ships"])
    with pytest.raises(ValueError, match="no enviamos impresas"):
        fulfilment.create_checkout("job", impreso, country="MX")


def test_para_imprimir_como_lamina():
    from app import fulfilment
    t = open("app/static/producto.html").read()
    assert "Quiero mi lámina" in t and "Es tuya" in t and "Descargar mi caricatura" not in t and "(descarga)" not in t
    assert "descarga" not in fulfilment.PRODUCTS["digital"]["name"].lower()
