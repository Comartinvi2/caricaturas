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

## Fase B — portada — HECHO (commit 4354e75, 9 nov)

- [x] `/api/scenes?lite=1` vacía el array `images` (3.052 URLs que la portada
      no usa); `desc` se queda porque las tarjetas y el buscador lo usan.
      JSON: 603 KB → 206 KB en bruto. La ficha (`?only=`) no cambia.
- [x] Verificado en producción: la portada pide `?lite=1` (25 KB transferidos),
      36 tarjetas, tira hero y filtros funcionan, consola sin errores.
- Hallazgo: el transporte YA iba comprimido por el proxy de Render (603 KB →
  40 KB con gzip), así que el ahorro real de esta fase es sobre todo de parseo
  y memoria en móviles (y 40 → 25 KB de red), no los ~550 KB aparentes.
- Hallazgo (datos, no código): no existe NINGÚN producto de boda/pareja, ni en
  el catálogo ni en la tienda polaca de origen (`aniversario` tiene 1 y
  `familia` 3). No había nada que reetiquetar.
- [x] Decisión de Maria (9 nov): ocultar las colecciones sin productos.
      Commit 83ec420: `_nonempty_cols()` filtra menú, filtros de portada,
      sitemap y llms.txt; `/coleccion/<slug>` sigue existiendo por si llega
      un enlace antiguo. Verificado en producción (13 filtros, sin «Boda»).
- Pendiente de decidir algún día: crear productos de boda/aniversario
  (reaparecerían solos en los filtros al tener productos).

## Fase C — mismo patrón en cuadrosconalma y poster-nacimiento (después)

Pesan ~250-330 KB, menos urgente. Revisar: peso de ficha, favicon, catálogo
completo. Mejor como tarea aparte cuando A y B estén cerradas.

## Fase E — ficha como la tienda polaca (aprobada por Maria, 9 nov)

Por qué: Clarity (30 días, 200 sesiones con cookies aceptadas) muestra que el
25 % genera su caricatura pero casi nadie pulsa «Pedir» (1 clic en la ficha del
motero, 25 sesiones que generaron). Se van en el momento de decidir. La tienda
polaca, con los mismos precios, resuelve ese momento con 2 variantes, cambios
con texto y garantía de devolución.

Suposiciones:
- OpenAI `images/edits` acepta `n: 2` con nuestro modelo (una llamada, 2 imágenes).
  Si no, se hacen 2 llamadas en paralelo. Coste por intento ×2; con 2 intentos
  (decisión de Maria, 9 nov) son hasta 4 imágenes por persona y día (hoy 3).
- Los ajustes después de pagar los atiende Maria/Eva a mano (email o Tawk.to);
  no se construye un «panel» como el polaco.
- Precio: igual que ahora durante 1-2 semanas para medir el efecto de estos
  cambios; luego se decide si bajarlo.
- Sin «Se vendieron 3 en 24 horas» salvo que sea un dato real.

TODOs (cada uno se prueba en local en modo demo y luego en producción):

1. [x] Cada «Generar visualización» crea 2 variantes (2 job_id) en vez de 1.
       Intentos gratis: 2 en 24 h (antes 3), en servidor y en la ficha.
       → verificar: en modo demo salen 2 imágenes con marca de agua y las dos se
       pueden pagar.
2. [x] Textos de la caja de fotos: «Hasta 2 pruebas gratuitas en 24 horas.» y
       «Sube una foto, añade tus deseos y pulsa "Generar visualización".
       Crearemos dos visualizaciones. Tarda unos minutos.»
3. [x] Elegir variante con botones «Elijo la opción 1 / 2 …» bajo cada imagen y
       una opción más: «Necesito cambios». Al marcarla se muestra: «Tras pagar tu
       pedido te escribimos para preparar más variantes y hacer los ajustes que
       necesites hasta que te guste. Si no quedas satisfecho, te devolvemos el
       importe.» El pedido guarda esa elección para que el aviso de pago al
       equipo diga «quiere cambios».
       Con «Necesito cambios» el pedido queda EN ESPERA: no se entrega el archivo
       sin marca de agua ni se manda a Gelato hasta que el cliente apruebe la
       versión final (hoy ambas cosas pasan nada más pagar). Mismas garantías
       que la polaca para todos los productos (decisión de Maria, 9 nov): si tras
       los cambios no queda satisfecho, se le devuelve el importe total (no se
       llegó a entregar ni imprimir nada). Quien elige una variante sin cambios
       («Acepto esta variante») recibe el archivo / se imprime al momento, como hoy.
       → verificar: elegir cada opción cambia la variante que se paga; la
       elección llega al email de pedido; con «Necesito cambios» no hay
       descarga ni pedido a Gelato tras pagar.
4. [x] «Probar con otra foto» pasa a «Generar otra visualización»: conserva la
       foto subida y deja editar los deseos (ahora borra la foto).
5. [x] Tocar la caricatura la amplía a pantalla completa (Clarity: clics
       repetidos sin efecto sobre «Tu caricatura»).
6. [x] Tipo «Solo archivo» marcado por defecto y su precio arriba (como la
       polaca). Portada y tarjetas: «desde 25,90 €».
7. [x] Garantía en «Envíos y devoluciones» (ficha) y en `legal.html`: cambiar
       «Si no se parece, lo rehacemos una vez gratis» por los ajustes hasta que
       guste o devolución del importe; y matizar «Los archivos digitales no
       admiten devolución una vez descargados» (con cambios pedidos, el archivo
       no se descarga hasta aprobarlo). Texto exacto a revisar con Maria antes de
       publicarlo (es un compromiso legal frente al cliente).
8. [ ] Medir 1-2 semanas en Clarity: clics en «Pedir» y ventas.

Hecho (9 nov): las 2 variantes son 2 llamadas en paralelo a OpenAI (más
robusto que `n: 2`). Pedidos con cambios: página `/admin/cambios?token=…`
(lista los pagados con «Necesito cambios», botón «Rehacer con estas
indicaciones» que edita la caricatura con OpenAI y guarda la anterior, y
«Aprobar y entregar» que manda a imprimir o habilita la descarga y envía el
email de siempre). La devolución, si hace falta, se hace a mano en Stripe.
Probado en local en modo demo (script con TestClient: 2 variantes, límite de
2 pruebas, pago sin cambios = entrega inmediata, con cambios = en espera sin
descarga ni impresión, rehacer y aprobar).

## Fase F — que no se pierda nadie durante la espera (aprobada por Maria, 9 nov)

Por qué: Clarity (ficha del motero) muestra que ~10 de 25 personas que pulsan
«Generar» se van a los 1-2 min, justo durante la espera (22 de 25 en el
navegador de Facebook/Instagram). Al volver, la página se ha recargado y las
variantes se han perdido (solo se guardan en el móvil al terminar).

Suposiciones:
- El email es opcional y solo se usa para enviar las visualizaciones pedidas
  (servicio solicitado, RGPD art. 6.1.b). No se guarda en el pedido ni se usa
  para recordatorios comerciales (eso pediría consentimiento aparte, LSSI art. 21).
- El enlace del email abre la ficha con `?v=job1,job2` y la ficha recupera esas
  variantes (las previews siguen 2 días en Supabase).

TODOs:
1. [x] Campo opcional «Tu email» en el formulario; `/api/generate` envía al
       terminar un email con las 2 previews y el enlace de vuelta.
       → verificar: en demo, con email válido se llama a `mail.variants_ready`;
       con email inválido o vacío no se envía nada y la generación funciona.
2. [x] La ficha abierta con `?v=…` muestra esas variantes y se pueden pagar.
3. [x] Espera: barra de progreso y «Tarda alrededor de 1 minuto. No cierres
       esta página» en lugar de los mensajes rotatorios.
4. [x] Privacidad (`legal.html`): una frase sobre el email opcional.
5. [x] Desplegar y comprobar en producción (commit af3689f, 9 nov): generación
       real con email a hola@caricaturea.com en 44 s; el enlace `?v=` abre la
       ficha con las 2 variantes. Falta que Maria confirme que el email llegó
       (los logs de Render de este servicio no están en la cuenta conectada).
6. [ ] Medir junto con la Fase E: ¿bajan los abandonos durante la espera?

## Precio del archivo: 2,99 € (decisión de Maria, 9 nov)

Antes 25,90 €. Cambiado el mismo día que se publicaron las Fases E y F, así
que al medir no se podrá separar el efecto de cada cambio. Lienzo y póster
siguen desde 35,90 €.
Mismo día (decisión de Maria): el lienzo pasa a ser la opción marcada por
defecto y la primera; «desde» en portada y fichas = lienzo 20x30. El archivo
queda el último, como extra.

## Fase D — seguimiento

- ~10 nov: revisar en adengine si el % de clics de Meta que cargan sube del 57,8 %.
- Decisión pendiente de Maria (no de código): adengine tiene 1.216 €/mes
  comprometidos frente a su tope de 500 €/mes.

## Fase G — embudo propio sin cookies (aprobada por Maria, 9 nov)

Por qué: Clarity solo ve a quien acepta cookies (pocas sesiones) y Maria quería
cargar las cookies sin consentimiento para medir; eso es ilegal (LSSI 22.2,
RGPD). Alternativa: contar en nuestro servidor cuántas visitas llegan a cada
paso. Solo totales por día: ni IP, ni identificadores, ni nada en el móvil.

- [x] `funnel.py`: contadores por día y paso en memoria, guardados cada minuto
      en Supabase (no hace falta tabla nueva) y al apagar.
- [x] Pasos: ficha (visita no-bot) → generar → generada → vista (la persona ve el resultado; aviso sin cookies desde la ficha) → email → pedir → venta.
- [x] `/admin/embudo?token=…`: tabla de los últimos 30 días, totales y % de
      cada paso respecto al anterior.
- [ ] Probar en local y en producción (los pasos suben al navegar).

## Fase H — del resultado al pago en móvil (11 nov, María: «sigue sin pedirme permiso»)

Por qué: en las grabaciones de Clarity (5-9 nov, móvil desde anuncios) 40 de 118
sesiones enviaron la foto y ninguna pagó. Tras ver el resultado tocaban la imagen
y los precios sin respuesta; el selector de formato queda ~1.300 px por encima del
botón «Pedir» y, al volver desde el email, la página abría arriba del todo.
Prueba real en producción el 11 nov: genera en 48 s y el parecido es bueno, así
que el freno no es el dibujo.

- [x] Selector «Formato y tamaño» (todos los productos con precio) justo encima de
      «Pedir», sincronizado con las tarjetas de tipo y tamaño de arriba.
- [x] Al cargar con visualizaciones guardadas (o con ?v= del email), ir directo a ellas.
- [x] Tocar la imagen principal la amplía (antes solo la del resultado).
- [x] Solo móvil: botón «Mira tu caricatura gratis: sube tu foto ↓» bajo las miniaturas.
- Verificado en local (demo, 375 px): el selector cambia precio y tarjetas en ambos
  sentidos, zoom, botón visible en móvil y oculto en escritorio, salto al resultado.
- [ ] Medir en /admin/embudo con Meta reactivado el 11 nov: generar→vista→pedir→venta.

## Fase I — señal para Meta: «AddToCart» al generar (11 nov)

Meta optimizaba por «inicio de pago» (2 eventos) cuando el píxel ya registra 60
«Lead» (caricatura generada) en 113 visitas medidas. «Lead» no vale como evento de
optimización en campañas de ventas, así que al generar se envía además «AddToCart»
(solo con cookies aceptadas, como el resto). En AdEngine la campaña pasa a
optimizar por ese evento.

- [x] `producto.html`: `track('generate')` envía también `AddToCart` al píxel.
- [ ] Comprobar en Meta que llegan eventos AddToCart con el tráfico nuevo.

## Fase J — confianza junto al botón de pagar (11 nov)

Por qué: la garantía de devolución (política ya publicada en «Envíos y devoluciones»)
solo se veía al marcar «Necesito cambios» o abrir el desplegable. Bajo «Pedir» no
había nada que tranquilizara, y es justo donde se pierde casi todo (60 caricaturas
generadas, 2 inicios de pago, 0 ventas).

- [x] Línea bajo «Pedir»: «Pago seguro · No imprimimos nada sin tu aprobación · Si no
      te gusta, te devolvemos el dinero». Solo repite lo que ya promete la web.
- Verificar: la línea aparece en producción bajo el botón (curl y móvil).
- Medir: pedir/vista en /admin/embudo frente a antes.

## Fase K — Navidad (11 nov)

- [x] Barra superior (portada y ficha): «🎄 Llega a tiempo para Navidad · -X % · Envío gratis ·
      Ves el diseño antes de pagar». Plazo real: 24-48 h + 2-4 días, hoy es cierto.
- OJO: quitar «Llega a tiempo para Navidad» hacia el 15-dic.
- Verificar: curl de la portada y de una ficha en producción.
