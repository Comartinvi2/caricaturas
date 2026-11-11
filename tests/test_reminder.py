import time

from app import config, reminder

NOW = 1_800_000_000.0


def row(job, email="ana@x.es", hours=20, **m):
    return {"job_id": job, "meta": {"email": email, "created": NOW - hours * 3600, "status": "previewed", "scene": "motero", **m}}


def test_agrupa_por_email_y_respeta_la_ventana():
    rows = [row("a"), row("b"), row("c", hours=5), row("d", hours=50), row("e", email=""), row("f", email="luis@x.es", reminded=1)]
    out = reminder.pending(rows, now=NOW)
    assert [(g["email"], sorted(g["jobs"])) for g in out] == [("ana@x.es", ["a", "b"])]


def test_no_escribe_a_quien_ya_pago():
    rows = [row("a"), row("z", hours=30, paid=True, status="paid")]
    assert reminder.pending(rows, now=NOW) == []


def test_tambien_a_quien_abandono_el_pago():
    assert [g["jobs"] for g in reminder.pending([row("a", status="checkout")], now=NOW)] == [["a"]]


def test_descuento_firmado(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secreto")
    tok = reminder.token("Ana@x.es", now=NOW)
    assert reminder.discount_pct({"email": "ana@x.es"}, tok, now=NOW + 3600) == 10
    assert reminder.discount_pct({"email": "otra@x.es"}, tok, now=NOW + 3600) == 0       # otro email
    assert reminder.discount_pct({"email": "ana@x.es"}, tok, now=NOW + 25 * 3600) == 0   # caducado
    assert reminder.discount_pct({"email": "ana@x.es"}, tok.split(".")[0] + ".falso", now=NOW) == 0
    assert reminder.discount_pct({"email": "ana@x.es"}, "", now=NOW) == 0
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    assert reminder.discount_pct({"email": "ana@x.es"}, tok, now=NOW) == 0                 # sin secreto, nunca


def test_el_pago_aplica_el_descuento(monkeypatch):
    from app import fulfilment, storage
    seen = {}

    class S:
        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    seen.update(kw)
                    return type("X", (), {"id": "cs_1", "url": "https://pay"})()
    monkeypatch.setattr(config, "PAYMENTS_ENABLED", True)
    monkeypatch.setattr(fulfilment, "stripe_client", lambda: S)
    monkeypatch.setattr(storage, "update_meta", lambda *a, **k: {})
    monkeypatch.setattr(storage, "persist", lambda *a, **k: None)
    pid = next(iter(fulfilment.PRODUCTS))
    fulfilment.create_checkout("job1", pid, pct=10)
    cents = fulfilment.PRODUCTS[pid]["cents"]
    assert seen["line_items"][0]["price_data"]["unit_amount"] == round(cents * 0.9)
    assert seen["metadata"]["descuento"] == "recordatorio 10%"
    fulfilment.create_checkout("job1", pid)
    assert seen["line_items"][0]["price_data"]["unit_amount"] == cents and "descuento" not in seen["metadata"]
