"""23-nov: GA4 contaba la compra con 0 € porque el evento se enviaba sin moneda."""
from pathlib import Path


def test_compra_lleva_moneda():
    t = (Path(__file__).parent.parent / "app/static/gracias.html").read_text()
    assert "track('purchase',{value: s.amount||0, currency: 'EUR'" in t
