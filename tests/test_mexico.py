import stripe as real

from app import fulfilment as shop

PARAMS = {"mode": "payment", "adaptive_pricing": {"enabled": True}, "managed_payments": {"enabled": False},
          "line_items": [{"price_data": {"currency": "eur", "unit_amount": 1990, "product_data": {"name": "Archivo"}}, "quantity": 1}]}


class FakeStripe:
    StripeError = real.StripeError

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail
        outer = self

        class Session:
            @staticmethod
            def create(**p):
                outer.calls.append(p)
                if outer.fail and p.get("managed_payments", {}).get("enabled"):
                    raise real.StripeError("no activado")
                return p

        self.checkout = type("C", (), {"Session": Session})


def test_mexico_digital_va_por_managed_payments():
    f = FakeStripe()
    s = shop.create_session(f, PARAMS, mexico_digital=True)
    assert s["managed_payments"] == {"enabled": True} and "adaptive_pricing" not in s
    assert s["line_items"][0]["price_data"]["product_data"]["tax_code"] == "txcd_10505001"
    assert "tax_code" not in PARAMS["line_items"][0]["price_data"]["product_data"]  # no toca los parámetros originales


def test_resto_de_paises_pago_normal():
    f = FakeStripe()
    assert shop.create_session(f, PARAMS, mexico_digital=False) == PARAMS


def test_si_stripe_lo_rechaza_se_cobra_normal():
    f = FakeStripe(fail=True)
    assert shop.create_session(f, PARAMS, mexico_digital=True) == PARAMS and len(f.calls) == 2
