"""Imágenes públicas servidas desde caricaturea.com/img/... en vez de directamente desde Supabase.

Cada imagen se guarda en el disco del servidor la primera vez (y se refresca como mucho una vez por
semana), así que sale de Supabase una sola vez y no en cada visita: el tráfico (egress) de Supabase
baja casi a cero. Si Supabase falla, se sirve la copia guardada.

- Ruta GET /img/{bucket}/{ruta}: descarga la imagen pública de Supabase y la devuelve con caché larga.
- Middleware: en las respuestas HTML/JSON/XML/JS cambia las URLs públicas de Supabase por /img/...
"""
import hashlib
import os
import time

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from . import config

SB_URL = config.env("SUPABASE_URL").rstrip("/")
SB_PUBLIC = f"{SB_URL}/storage/v1/object/public/" if SB_URL else ""
IMG_BASE = f"{config.BASE_URL}/img/"
BUCKETS = {"caricaturas", "fe"}  # buckets públicos que se pueden servir por aquí
CACHE = "public, max-age=604800, s-maxage=2592000"  # navegador 7 días, Cloudflare 30 días
REWRITE_TYPES = ("text/html", "application/json", "application/xml", "text/xml", "application/javascript", "text/javascript")
MAX_BYTES = 15 * 1024 * 1024
CACHE_DIR = config.DATA_DIR / "imgcache"   # caché en el disco de Render: cada imagen sale de Supabase una vez
CACHE_MAX_BYTES = int(config.env("IMG_CACHE_MB", "1500")) * 1024 * 1024
CACHE_TTL = 7 * 86400                       # se vuelve a pedir a Supabase como mucho una vez por semana
_last_prune = 0.0

_client: httpx.AsyncClient | None = None


def _c() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30, follow_redirects=True)
    return _client


def url(u: str) -> str:
    """URL pública de Supabase → URL de caricaturea.com/img/ (para usar en código)."""
    return u.replace(SB_PUBLIC, IMG_BASE) if (u and SB_PUBLIC) else u


def _cache_file(path: str):
    h = hashlib.sha1(path.encode()).hexdigest()
    ext = os.path.splitext(path)[1][:6] or ".bin"
    return CACHE_DIR / h[:2] / f"{h}{ext}"


def _prune():
    """Si la caché pasa del tope, borra los archivos menos usados."""
    global _last_prune
    if time.time() - _last_prune < 600:
        return
    _last_prune = time.time()
    try:
        files = [(f.stat().st_atime, f.stat().st_size, f) for f in CACHE_DIR.rglob("*") if f.is_file()]
        total = sum(x[1] for x in files)
        for _, size, f in sorted(files):
            if total <= CACHE_MAX_BYTES * 0.8:
                break
            f.unlink(missing_ok=True); total -= size
    except OSError:
        pass


_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".json": "application/json"}


async def serve(path: str):
    bucket = path.split("/", 1)[0]
    if bucket not in BUCKETS or ".." in path:
        raise HTTPException(404)
    f = _cache_file(path)
    ct = _TYPES.get(f.suffix.lower(), "application/octet-stream")
    try:
        if f.exists() and time.time() - f.stat().st_mtime < CACHE_TTL:
            return FileResponse(f, media_type=ct, headers={"Cache-Control": CACHE})
    except OSError:
        pass
    try:
        r = await _c().get(SB_PUBLIC + path)
    except Exception:  # noqa: BLE001  (red caída, timeout...)
        r = None
    if r is None or r.status_code != 200 or len(r.content) > MAX_BYTES:
        if f.exists():  # Supabase caído: mejor la copia vieja que nada
            return FileResponse(f, media_type=ct, headers={"Cache-Control": "public, max-age=300"})
        code = 404 if (r is not None and r.status_code in (400, 404)) else 502
        return Response(status_code=code, headers={"Cache-Control": "no-store"})
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(f.suffix + f".{os.getpid()}.tmp")
        tmp.write_bytes(r.content); tmp.replace(f)
        _prune()
    except OSError:
        pass
    return Response(r.content, media_type=r.headers.get("content-type", ct), headers={"Cache-Control": CACHE})


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
