"""Qué ve cada visita según su país (cabecera cf-ipcountry de Cloudflare)."""

DIGITAL_ONLY = {"MX", "CL"}  # Gelato no produce allí: solo la caricatura para imprimir (descarga)
US = {"US", "PR"}

TEXTS = {
    "es": {"SHIP_SHORT": "Envío gratis", "SHIP_NOTE": "envío gratis",
           "SHIP_INFO": "<b>Envío gratuito por mensajería</b><br>Entrega en 24-48 h tras la aprobación del diseño."},
    "us": {"SHIP_SHORT": "Envío gratis a EE. UU.", "SHIP_NOTE": "envío gratis a EE. UU. · pagas en dólares",
           "SHIP_INFO": "<b>Envío gratis a Estados Unidos y Puerto Rico</b><br>Se imprime tras tu aprobación y llega en 5-8 días laborables."},
    "digital": {"SHIP_SHORT": "Para imprimir, al momento", "SHIP_NOTE": "te llega al momento · pagas en tu moneda",
                "SHIP_INFO": "<b>Para imprimir, sin esperas</b><br>La lámina de tu caricatura te llega por email al momento de pagar."},
}


def market(country: str | None) -> str:
    c = (country or "").upper()
    return "digital" if c in DIGITAL_ONLY else "us" if c in US else "es"


def texts(country: str | None) -> dict:
    mk = market(country)
    return {"MARKET": mk, **TEXTS[mk]}


# --- Moneda del visitante (19-nov, María): la página enseña y Stripe cobra exactamente el mismo importe ----------------
# EE. UU. en dólares (euros × 1,15 redondeado a ,90), México en pesos (euros × 20 → $399), Chile en pesos (euros × 1000 → $19.990).
CURRENCY = {"US": "usd", "PR": "usd", "MX": "mxn", "CL": "clp"}
ZERO_DECIMAL = {"clp"}   # Stripe cobra los pesos chilenos sin céntimos


def currency(country: str | None) -> str:
    return CURRENCY.get((country or "").upper(), "eur")


def to_local(eur_cents: int, cur: str) -> int:
    """Precio en euros (céntimos) → importe en la moneda del visitante, en la unidad que usa Stripe (céntimos; pesos chilenos enteros)."""
    if cur == "usd":
        return (-(-(eur_cents * 115 - 90 * 100) // 10000)) * 100 + 90   # ×1,15 y hacia arriba a ,90: 19,90 € → $22.90
    if cur == "mxn":
        return (-(-eur_cents * 20 // 10000)) * 10000 - 100   # ×20 y hacia arriba a …99: 19,90 € → $399
    if cur == "clp":
        return (-(-eur_cents * 10 // 1000)) * 1000 - 10      # ×1000 y hacia arriba a …990: 19,90 € → $19.990
    return eur_cents


def major(amount: int, cur: str) -> float:
    return amount if cur in ZERO_DECIMAL else amount / 100


def fmt(amount: int, cur: str) -> str:
    """Importe en la unidad de Stripe → texto: «19,90 €», «$22.90 USD», «$399 MXN», «$19.990 CLP»."""
    x = major(amount, cur)
    if cur == "eur":
        s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return s.replace(",00", "") + " €"
    if cur == "usd":
        return f"${x:,.2f}".replace(".00", "") + " USD"
    if cur == "mxn":
        return f"${x:,.0f}" + " MXN"
    return f"${x:,.0f}".replace(",", ".") + " CLP"
