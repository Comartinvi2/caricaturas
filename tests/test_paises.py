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
        assert 'const MARKET = "es"' in t and "Envío gratuito por mensajería" in t and ">envío gratis</span></p>" in t


def test_impreso_desde_mexico_se_rechaza():
    impreso = next(k for k, v in fulfilment.PRODUCTS.items() if v["ships"])
    with pytest.raises(ValueError, match="no enviamos impresas"):
        fulfilment.create_checkout("job", impreso, country="MX")


def test_para_imprimir_como_lamina():
    from app import fulfilment
    t = open("app/static/producto.html").read()
    assert "Quiero mi lámina" in t and "Es tuya" in t and "Descargar mi caricatura" not in t and "(descarga)" not in t
    assert "descarga" not in fulfilment.PRODUCTS["digital"]["name"].lower()


def test_ficha_abre_con_la_lamina_para_imprimir_y_destaca_su_calidad():
    t = open("app/static/producto.html").read()
    assert "type = 'digital'" in t and "['digital','canvas','poster']" in t          # primera opción y la elegida al abrir
    assert "minOf('digital')" in t and "minOf(MARKET === 'digital' ? 'digital' : 'canvas')" not in t   # «Desde» = el precio más bajo real
    sellos = t[t.index('id="digi-note"'):t.index('class="chosen-price"')]
    assert "Calidad profesional de impresión" in sellos and "300 ppp en A4" in sellos and "Por email al momento" in sellos
    assert "type === 'digital' ? 'te llega por email al momento'" in t               # la lámina para imprimir no lleva «envío gratis»


def test_con_la_lamina_para_imprimir_no_se_habla_de_entrega_ni_de_tamano():
    t = open("app/static/producto.html").read()
    assert 'id="delivery-digital" hidden' in t and "te llega por email al momento de pagar" in t
    assert "$('#delivery-ship').hidden = dig; $('#delivery-digital').hidden = !dig;" in t
    assert 'id="size-title"' in t and "$('#size-title').hidden = $('#sizes').hidden = list.length < 2;" in t


def test_cabecera_con_el_lienzo_de_referencia_y_la_lamina_para_imprimir():
    t = open("app/static/producto.html").read()
    cab = t[t.index('<p class="from">'):t.index('<h3>Tipo y tamaño</h3>')]
    assert cab.index('id="from-anchor" hidden') < cab.index('id="canvas-from"') < cab.index('id="from-label"') < cab.index('id="price-from"')   # lo caro se lee primero
    assert "Lienzo desde" in cab
    assert "if (MARKET !== 'digital') { $('#from-anchor').hidden = false; $('#canvas-from').textContent = eur(minOf('canvas')); $('#from-label').textContent = 'Para imprimir:'; }" in t
