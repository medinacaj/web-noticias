@AGENTS.md

# Noticias del Momento

Sitio estático de noticias generales (Chile y el mundo) que se regenera solo cada hora con GitHub Actions y se publica en GitHub Pages. Sin servidor propio, sin Vercel.

## Cómo funciona

`fetch_noticias.py` en cada ejecución:
1. Recolecta titulares por categoría desde Google Noticias RSS (sin límite) y GNews API (solo cada 3 horas, para respetar el plan gratis de 100 solicitudes/día). Opcionalmente feeds directos de medios (`DIRECT_FEEDS`).
2. Los fusiona con `data/historial.json` (ventana de 24 h). Si un titular similar ya existe (difflib ≥ 0,6), suma la fuente en vez de duplicar y prefiere el enlace directo al medio sobre el de Google.
3. Genera en `public/` el sitio **ya renderizado en HTML** (no depende de JS): `index.html`, `404.html`, `sitemap.xml`, `robots.txt`, más `static/`.
4. Si no queda ninguna noticia, sale con código 1 a propósito: no publica una página vacía y GitHub avisa por correo.

Selección: puntaje = n.º de medios que la reportan − horas de antigüedad / 6. Portada = mejor de las últimas 12 h; 3 "Destacadas" sin vaciar ninguna sección; hasta `STORIES_PER_CATEGORY` (6) por categoría.

## Archivos

- `fetch_noticias.py` — recolector + generador. Marcadores `%%NOMBRE%%` se reemplazan en `template.html`; si queda alguno sin reemplazar, falla.
- `template.html` — diseño completo (CSS y JS en línea).
- `static/og-image.png` — imagen Open Graph 1200×630.
- `.github/workflows/update-news.yml` — cron cada hora (minuto 7), guarda el historial con commit y despliega con `actions/deploy-pages`.
- `data/historial.json` — lo crea y versiona el workflow. `public/` está en `.gitignore`.
- `scripts/agenda.py` — sección «Agenda de eventos»: en cada ejecución normal lee la lista `events` (ya validada) de los snapshots de `medinacaj/eventos-biobio`: Biobío (`crawled_events.json`) y resto de Chile (`national_events.json`, con región). Variables opcionales `EVENTOS_BIOBIO_URL` y `EVENTOS_NACIONALES_URL` (vacías desactivan cada una). Cada tarjeta lleva etiquetas de región, categoría y «Gratis»; los filtros por región, categoría y gratuidad solo aparecen con JavaScript (sin JS se ve la lista completa). Nunca muestra `possible_events`. Sin eventos próximos o con error de red, la sección y su enlace del menú no aparecen.
- `tests/demo.json` — 11 noticias reales verificadas (una duplicada a propósito) para probar sin red.

## Comandos

```bash
# vista previa local sin red (ventana amplia porque las fechas de demo son antiguas)
python3 fetch_noticias.py --importar tests/demo.json --ventana 1000 \
  --historial /tmp/hist.json --salida /tmp/public
# regenerar desde el historial sin consultar fuentes
python3 fetch_noticias.py --solo-render
```

Variables de entorno: `GNEWS_API_KEY` (secret), `SITE_URL` y `GSC_VERIFICATION` (variables de Actions). Sin `SITE_URL`, la canónica se deduce de `GITHUB_REPOSITORY`.

## Diseño (decisiones tomadas con el usuario)

- Dirección editorial tipo Monocle basada en el documento de diseño de Blog Panorámico (sin migrar a Next.js): tokens `--navy #0A2540`, `--navy-dark #061424`, `--red #C8102E`, `--paper #FBFAF7`, `--ink #07192E`, `--muted #6D7480`, `--rule #B9C0C8`; Source Serif 4 + Inter; esquinas rectas, líneas de 1 px, sin sombras; grilla de 12 columnas (8 en tablet, 1 en móvil).
- Masthead grande; barra de secciones fija arriba (el usuario la quiere siempre visible) que muestra la marca compacta al bajar.
- Cada noticia es una tarjeta separada (el usuario rechazó bloques "pegados").
- Color propio por categoría (pedido del usuario): nacional rojo, internacional azul, economía verde, tecnología violeta, deportes naranjo, cultura ciruela. Variables `--c-*` (texto sobre papel) y `--b-*` (sobre azul marino y modo oscuro). Se aplica en la línea superior y tinte de la tarjeta, etiqueta, encabezado de sección, menú y búsqueda.
- Barra de progreso minimalista del ciclo de 1 hora, basada en la hora real de generación (`<time datetime>`). El usuario no quiere textos tipo "actualización en curso".
- Búsqueda local sobre los titulares publicados (sin tildes), menú móvil desplegable, modo oscuro, `prefers-reduced-motion`.
- Franja de contexto con datos reales (lo más cubierto, sección más activa, cobertura) en lugar de "Dato / Por qué / Implicancia", que exigiría inventar análisis.
- El usuario no quiere mostrar "Verificado en X fuentes" (el dato `sources` se mantiene internamente).
- Cada titular enlaza a la nota concreta, nunca a la portada del medio.
- Descartado a pedido del usuario: sección de Ofertas/comparador de precios. Sin newsletter (no hay backend).

## Reglas del proyecto

- SEO técnico obligatorio en cada cambio: title, meta description, canonical, `index, follow`, Open Graph/Twitter, JSON-LD (`WebSite` + `CollectionPage`/`ItemList`), sitemap, robots, 404 con `noindex`, un solo `h1`.
- Los extractos son la descripción entregada por cada fuente; no presentarlos como redacción propia.
- Verificar tras cambios de diseño: sin desborde horizontal en 1440/1024/390 px, contenido legible con JS desactivado, JSON-LD válido, sintaxis JS con `node --check`.

## Pendientes

- Publicar: repo público en GitHub → Settings → Pages → Source: GitHub Actions; secret `GNEWS_API_KEY`; Run workflow. Si falla el push del historial: Settings → Actions → General → Read and write permissions.
- La recolección real (Google Noticias/GNews) nunca se probó contra la red; confirmar en la primera ejecución de Actions.
- En `usuario.github.io/repo/` el `robots.txt` no aplica (solo vale en la raíz del dominio). Recomendado: dominio propio + variable `SITE_URL`.
- Google Search Console (lo hace el propietario): propiedad por prefijo de URL, verificar con etiqueta HTML vía `GSC_VERIFICATION`, enviar `sitemap.xml`, inspeccionar e indexar la portada.
- Ideas no implementadas: páginas de archivo por día, resúmenes con IA, feed RSS propio.

## Marco legal-tecnológico
Leer `docs/ASESOR_LEGAL_TECNOLOGICO.md` en tareas con implicaciones legales, datos, IA, derechos de contenido, seguridad, proveedores, contratos o continuidad. Aplicar solo los controles pertinentes y distinguir requisitos jurídicos verificados de buenas prácticas; registrar evidencia, jurisdicción, riesgo y validación pendiente. Coordinar con `AGENTS.md`.
