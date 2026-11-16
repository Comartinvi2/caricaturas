"""Imágenes públicas servidas desde caricaturea.com/img/... en vez de directamente desde Supabase.

Cloudflare (delante de la web) guarda en caché las .jpg/.webp/.png, así que cada imagen sale de Supabase
una sola vez por nodo de Cloudflare y no en cada visita: el tráfico (egress) de Supabase baja casi a cero.

- Ruta GET /img/{bucket}/{ruta}: descarga la imagen pública de Supabase y la devuelve con caché larga.
- Middleware: en las respuestas HTML/JSON/XML/JS cambia las URLs públicas de Supabase por /img/...
"""
import httpx
from fastapi import HTTPException
from fastapi.responses import Response

from . import config

SB_URL = config.env("SUPABASE_URL").rstrip("/")
SB_PUBLIC = f"{SB_URL}/storage/v1/object/public/" if SB_URL else ""
IMG_BASE = f"{config.BASE_URL}/img/"
BUCKETS = {"caricaturas", "fe"}  # buckets públicos que se pueden servir por aquí
CACHE = "public, max-age=604800, s-maxage=2592000"  # navegador 7 días, Cloudflare 30 días
REWRITE_TYPES = ("text/html", "application/json", "application/xml", "text/xml", "application/javascript", "text/javascript")
MAX_BYTES = 15 * 1024 * 1024

_client: httpx.AsyncClient | None = None


def _c() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30, follow_redirects=True)
    return _client


def url(u: str) -> str:
    """URL pública de Supabase → URL de caricaturea.com/img/ (para usar en código)."""
    return u.replace(SB_PUBLIC, IMG_BASE) if (u and SB_PUBLIC) else u


async def serve(path: str):
    bucket = path.split("/", 1)[0]
    if bucket not in BUCKETS or ".." in path:
        raise HTTPException(404)
    try:
        r = await _c().get(SB_PUBLIC + path)
    except httpx.HTTPError:
        raise HTTPException(502)
    if r.status_code != 200 or len(r.content) > MAX_BYTES:
        # sin caché: si Supabase falla un rato, no queremos que Cloudflare guarde el error
        return Response(status_code=404 if r.status_code in (400, 404) else 502, headers={"Cache-Control": "no-store"})
    ct = r.headers.get("content-type", "application/octet-stream")
    return Response(r.content, media_type=ct, headers={"Cache-Control": CACHE})


class RewriteMiddleware:
    """Middleware ASGI que reescribe las URLs de Supabase en respuestas de texto."""

    def __init__(self, app):
        self.app = app
        self.old = SB_PUBLIC.encode()
        self.new = IMG_BASE.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.old or scope.get("path", "").startswith(("/img/", "/admin", "/api/print-file", "/api/download")):
            return await self.app(scope, receive, send)
        start, chunks = None, []

        async def _send(msg):
            nonlocal start
            if msg["type"] == "http.response.start":
                hdrs = dict((k.lower(), v) for k, v in msg.get("headers", []))
                ct = hdrs.get(b"content-type", b"").decode()
                if not ct.startswith(REWRITE_TYPES) or b"content-encoding" in hdrs:
                    start = False
                    return await send(msg)
                start = msg
                return
            if msg["type"] == "http.response.body" and start:
                chunks.append(msg.get("body", b""))
                if msg.get("more_body"):
                    return
                body = b"".join(chunks).replace(self.old, self.new)
                headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
                headers.append((b"content-length", str(len(body)).encode()))
                await send({**start, "headers": headers})
                return await send({"type": "http.response.body", "body": body})
            return await send(msg)

        await self.app(scope, receive, _send)
