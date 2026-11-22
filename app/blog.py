"""Blog en /blog: lo escribe y aloja RankCoworker (cuenta «caricaturea»); esta web solo reenvía /blog/*.
Así los artículos cuentan para el SEO de este dominio. Si se cambia el dominio, cambiarlo también en RankCoworker."""
import httpx
from fastapi import Request, Response

ORIGIN = "https://caricaturea.rankcoworker.com/__pub/caricaturea.com/blog"
_PASS = ("content-type", "location", "cache-control", "etag", "last-modified", "x-rankcoworker-blog")


def target(path: str, query: str = "") -> str:
    """/blog/<path>?<query> -> URL en RankCoworker (sin barra final, como hace su Worker)."""
    p = path.strip("/")
    return ORIGIN + ("/" + p if p else "") + ("?" + query if query else "")


async def proxy(request: Request, path: str = "") -> Response:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as c:
            r = await c.get(target(path, request.url.query), headers={"user-agent": request.headers.get("user-agent", "")})
    except httpx.HTTPError:
        return Response("El blog no está disponible ahora mismo.", status_code=502)
    return Response(r.content, status_code=r.status_code, headers={k: v for k, v in r.headers.items() if k.lower() in _PASS})
