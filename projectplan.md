# Plan: imagen intermedia para móvil y ficha/portada ligeras

Contexto (7 nov 2026): adengine marca que solo carga el 57,8 % de los clics de Meta.
Ya desplegado: ficha con `/api/scenes?only=`, srcset 480w/1160w, favicon ligero.
Pendiente: en móviles DPR 3 el srcset sigue eligiendo `main.jpg` (~230 KB).

## Suposiciones (confirmar si alguna falla)

- La versión intermedia solo hace falta para la imagen principal (`image_url`,
  normalmente `<slug>/main.jpg`), no para las miniaturas ni `art.jpg`.
- El backfill de los 436 productos se hace igual que las miniaturas `-t.webp`:
  `ensure_thumbs()` en el arranque de Render, sin script aparte.
- Calidad WebP 75 a 800 px debería quedar por debajo de 80 KB; se comprueba con
  una imagen real antes de desplegar y se ajusta si no.

## Fase A — main-m.webp (dos despliegues, para no enlazar imágenes que aún no existen)

### Despliegue 1: generar las imágenes

- [ ] `catalog.py`: función `medium_path()` (`main.jpg` → `main-m.webp`) y versión
      de 800 px / calidad ~75 reutilizando `make_thumb(data, width=800)`.
      → verificar: con un `main.jpg` real descargado, el resultado pesa < 80 KB.
- [ ] `catalog.py`: `upload_image()` genera también `-m.webp` al subir un producto.
- [ ] `catalog.py`: `ensure_thumbs()` encola además los `-m.webp` que falten
      (solo para `image_url` de cada producto).
- [ ] Desplegar y esperar al backfill.
      → verificar: log de Render «miniaturas: N creadas, 0 errores» y que
      `https://.../caricaturas/<slug>/main-m.webp` responde 200 en 2-3 slugs.

### Despliegue 2: usarlas en la ficha

- [ ] `main.py`: pasar `MAIN_IMG_M` al template (mismo criterio que `MAIN_IMG_T`).
- [ ] `producto.html`: srcset `-t.webp 480w, -m.webp 800w, main.jpg 1160w`.
      El `src` sigue siendo `main.jpg` (fallback intacto).
      → verificar: en producción, con DevTools emulando DPR 3 / 390 px,
      la red descarga `main-m.webp` y no `main.jpg`.

## Fase B — portada (valorar, decidir con Maria)

`index.html` sigue bajando `/api/scenes` completo (~594 KB). La portada ya tiene
grid SSR; el JSON se usa para filtros y para el flujo de subida. Opciones:

1. **Modo ligero** `?lite=1`: en el listado, quitar de cada escena `desc` e
   `images` (solo se usan en la ficha). Estimación: reduce el JSON a menos de
   la mitad sin tocar la lógica de filtros. ← la más simple, recomendada.
2. Paginar: rompe el filtrado en cliente; más código. Descartada salvo que (1)
   no baste.

## Fase C — mismo patrón en cuadrosconalma y poster-nacimiento (después)

Pesan ~250-330 KB, menos urgente. Revisar: peso de ficha, favicon, catálogo
completo. Mejor como tarea aparte cuando A y B estén cerradas.

## Fase D — seguimiento

- ~10 nov: revisar en adengine si el % de clics de Meta que cargan sube del 57,8 %.
- Decisión pendiente de Maria (no de código): adengine tiene 1.216 €/mes
  comprometidos frente a su tope de 500 €/mes.
