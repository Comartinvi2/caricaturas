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
