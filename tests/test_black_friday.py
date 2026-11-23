"""Barra de Black Friday: anuncia BLACK26 hasta el 30-nov y luego vuelve la de siempre."""
from app import config, main


def test_barra_black_friday(monkeypatch):
    monkeypatch.setattr(config, "BLACK_FRIDAY_END", 2e10)
    for page in ("index.html", "producto.html"):
        html = main._page(page).body.decode()
        assert "código BLACK26" in html and "Llega a tiempo para Navidad" not in html
    monkeypatch.setattr(config, "BLACK_FRIDAY_END", 0)
    for page in ("index.html", "producto.html"):
        html = main._page(page).body.decode()
        assert "BLACK26" not in html and "Llega a tiempo para Navidad" in html
