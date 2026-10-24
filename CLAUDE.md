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
- `scripts/agenda.py` — sección «Agenda» (eventos): en cada ejecución normal lee la lista `events` (ya validada) de tres archivos: los snapshots del recolector `eventos/` en la rama `events-data` (Biobío `crawled_events.json` y resto de Chile `national_events.json`, con región) y la agenda manual `eventos/agenda_manual.json`. Variables opcionales `EVENTOS_BIOBIO_URL`, `EVENTOS_NACIONALES_URL` y `EVENTOS_MANUAL_URL` (ruta local o URL https; vacías desactivan cada una). Hasta 36 eventos con tope de 12 por región. Se presenta como una sección más (decisión del usuario: que no se vea «forzada»): número correlativo tras las secciones de noticias, mismas tarjetas `compact` con el póster oficial (`image_url` https del snapshot) en el lugar de la imagen y, si no hay, la fecha, kicker «Categoría · Comuna», meta con medio, región, «Gratis» y fecha; color propio dorado (`--c-agenda #8A6100`, `--b-agenda #F2C14E`, clase `.cat-agenda`, pedido del usuario) en el menú, número de sección y tarjetas; entra en búsqueda, favoritos y «Ver más». Filtros por región y «Solo gratis» con botones `density-switch`, solo con JavaScript. Nunca muestra `possible_events`. Sin eventos próximos o con error de red, la sección y su enlace del menú no aparecen.
- `eventos/` — recolector de eventos integrado desde `medinacaj/eventos-biobio` (el usuario lo eliminará; solo se migró el rastreo, no la app local). Fuentes en `eventos/config/` (Biobío y nacionales), resguardos de calidad en `eventos/scrapers/` (JSON-LD, fichas «Por confirmar», calendarios The Events Calendar/iCal, dominios municipales candidatos) y sus propias pruebas (`cd eventos && python3 -m unittest discover -s tests -t .`). El workflow `actualizar-eventos.yml` corre a diario (11:35 UTC) con código de `main` y guarda snapshots, estado de fuentes y `coverage.md` solo en la rama `events-data` vía `scripts/events_data.py` (mismo aislamiento que `news_data.py`). `update-news.yml` hace checkout de esos snapshots en `.events-data/`.
- `eventos/agenda_manual.json` — eventos revisados a mano desde la publicación oficial del organizador (p. ej. afiches de Instagram, que no se pueden rastrear). Cambiarlo republica el sitio; `tests/test_agenda.py` valida cada entrada.
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
- Cabecera compacta con monograma N, nombre, actualización y controles. Navegación lateral visible por defecto desde 1024 px, plegable y con preferencia persistida; en móvil es un menú cerrado inicialmente. Sin carrusel automático de secciones. Tema automático del sistema con elección claro/oscuro/automático. Decisión del usuario delegada en UI/UX, 2026-10-24.
- «Lo último» es un carrusel manual de hasta seis titulares distintos con fecha editorial explícita: tres visibles en escritorio, dos en tablet y uno en móvil. Los indicadores de cobertura quedan en detalles plegables del pie.
- Cultura complementa las vías anteriores con ediciones Google Noticias de España y México; solo metadatos, respetando las puertas de los catálogos mundial y regional. Ver `docs/FUENTES_ENTRETENIMIENTO.md`.
- Firma del pie: cápsula enlazada a `https://www.linkedin.com/in/medinacaj/`, oscura en tema claro y blanca en oscuro. Sin fotografía real, las tarjetas priorizan texto y atribución; no mostrar bloques grandes de ausencia de imagen.
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
- Coherencia visual (lección de la Agenda, PR #87/#88 → #91): toda sección o bloque nuevo reutiliza los componentes existentes (`section-head` numerado, `section-grid`, tarjetas `.feature`/`.compact`, `.kicker`, `.meta`, `.media`, botones `.density-switch`) en vez de crear clases visuales propias. No agregar colores fuera de la paleta: usar los tokens y las clases `.cat-*` de las categorías existentes. Antes de fusionar, revisar una captura de la sección nueva junto a una sección de noticias, a 1440 y 390 px. `tests/test_design_consistency.py` lo vigila: si de verdad hace falta un color o una clase de categoría nueva, actualizar ahí su lista con la aprobación del usuario.

## Pendientes

- Publicar: repo público en GitHub → Settings → Pages → Source: GitHub Actions; secret `GNEWS_API_KEY`; Run workflow. Si falla el push del historial: Settings → Actions → General → Read and write permissions.
- La recolección real (Google Noticias/GNews) nunca se probó contra la red; confirmar en la primera ejecución de Actions.
- En `usuario.github.io/repo/` el `robots.txt` no aplica (solo vale en la raíz del dominio). Recomendado: dominio propio + variable `SITE_URL`.
- Google Search Console (lo hace el propietario): propiedad por prefijo de URL, verificar con etiqueta HTML vía `GSC_VERIFICATION`, enviar `sitemap.xml`, inspeccionar e indexar la portada.
- Ideas no implementadas: páginas de archivo por día, resúmenes con IA, feed RSS propio.

## Marco legal-tecnológico
Leer `docs/ASESOR_LEGAL_TECNOLOGICO.md` en tareas con implicaciones legales, datos, IA, derechos de contenido, seguridad, proveedores, contratos o continuidad. Aplicar solo los controles pertinentes y distinguir requisitos jurídicos verificados de buenas prácticas; registrar evidencia, jurisdicción, riesgo y validación pendiente. Coordinar con `AGENTS.md`.
