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

### Despliegue 1: generar las imágenes — HECHO (commit 0f4c6ec, 8 nov)

- [x] `catalog.py`: `medium_path()` y `make_thumb(data, 800)` con la calidad 78
      de siempre: 58-72 KB en pruebas con imágenes reales.
- [x] `catalog.py`: `upload_image()` genera también `-m.webp` (solo `main.jpg`).
- [x] `catalog.py`: `ensure_thumbs()` encola además los `-m.webp` que falten.
- [x] Backfill verificado contra Supabase: 436/436 (dos fallaron en la primera
      pasada por errores transitorios y se crearon solas en el arranque siguiente).
      Pesos reales: mediana 73 KB, máx 100 KB (117 quedan entre 80 y 100 KB;
      se aceptó: frente a los ~230 KB del jpg el ahorro grande ya está hecho).

### Despliegue 2: usarlas en la ficha — HECHO (commits 664e10b y cf310a5, 8 nov)

- [x] `main.py`: `MAIN_IMG_M` al template (mismo criterio que `MAIN_IMG_T`).
- [x] `producto.html`: srcset `-t.webp 480w, -m.webp 800w, main.jpg 1160w`,
      `src` sigue siendo `main.jpg`.
- [x] Hallazgo: añadir el 800w NO bastaba para DPR 3 (el navegador calcula
      92vw×3 ≈ 1035 px y elige el candidato superior, main.jpg). Arreglo:
      en `sizes`, para pantallas de ≥2,5dppx se declara 266px, con lo que
      800 px ya cubre (densidad real 2,3x). Navegadores antiguos ignoran esa
      condición y se quedan como estaban.
- [x] Verificado en producción con emulación móvil (375 px, DPR 2):
      `currentSrc` es `main-m.webp` y la ficha se ve bien. DPR 3 queda
      garantizado por el cálculo del propio `sizes` (266×3 ≈ 800).

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
