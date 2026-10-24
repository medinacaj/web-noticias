"""Evento desde la página individual de una fuente oficial que no publica JSON-LD.

Aprobado por el responsable el 2026-10-24 («publicar con resguardos»). Muchas
fuentes oficiales (teatros, centros culturales, municipios) tienen una página
por evento pero sin datos estructurados. Esta extracción publica el evento con
estado «Por confirmar» solo si se cumplen todas las condiciones:

- la fuente es oficial y de tipo recinto, municipio o agregador oficial;
- la URL es una ficha individual (no la portada ni un listado o categoría) y,
  salvo en recintos, contiene una pista de evento en la ruta;
- la página tiene un título propio (h1, og:title o <title>);
- el texto trae una fecha vigente con año explícito, o sin año pero dentro de
  los próximos 90 días (evita inferir mal el año de fechas pasadas);
- hay a lo sumo 15 fechas distintas (más que eso suele ser un listado);
- la comuna es la fija del recinto o aparece junto a la fecha.

No se inventa hora, precio ni recinto: si no están en el bloque de la fecha
o sus vecinos inmediatos, quedan vacíos.
"""
from datetime import date, timedelta
import html
import re
from urllib.parse import urlparse

from images import extract_official_image
import metadata
from scrapers.common import parse_page

ALLOWED_TYPES = {"venue", "municipal", "aggregator"}
PAGE_TAG = "ficha sin datos estructurados"
LISTING_SEGMENTS = {"", "eventos", "events", "evento", "event", "agenda", "cartelera", "actividades",
                    "actividad", "programacion", "programa", "category", "categoria", "categorias",
                    "tag", "tags", "page", "talleres", "archivo", "espectaculos", "que-hacer-en-gam",
                    "es", "en", "noticias", "calendario", "calendar"}
LISTING_PARTS = ("/category/", "/categoria/", "/tag/", "/page/", "/feed")
PATH_HINTS = ("evento", "event", "actividad", "espectaculo", "obra", "concierto", "festival",
              "feria", "funcion", "taller", "programacion", "cartelera", "agendacultural", "agenda")
GENERIC_TITLES = ("inicio", "home", "cartelera", "programacion", "eventos", "agenda", "actividades",
                  "noticias", "talleres", "pagina no encontrada", "404")
NEWS_FOLDERS = {"noticias", "noticia", "prensa", "comunicados", "comunicado", "blog", "actualidad"}
# Títulos de trámites o noticias, no de eventos (casos reales del 2026-10-24).
NOT_EVENT_TITLE = re.compile(
    r"\b(seleccionad[oa]s?|selecciona|postulaci[oó]n(es)?|postula[nr]?|abre (las )?postulaciones|"
    r"convocatoria|concursables?|fondos|beneficios|resultados|ganador(es|as)?|calendario de|"
    r"inauguran|inaugur[oó]|balance|licitaci[oó]n)\b", re.I)
END_WINDOW = 45  # funciones de una misma temporada; fechas más lejanas suelen ser otra cosa
LISTING_LINKS = 3  # enlaces a fichas hijas de la misma ruta: es una página de categoría
# Nombres de región que contienen el nombre de una comuna de otra región.
REGION_PHRASES = re.compile(
    r"antartica chilena|region(es)? de los (rios|lagos)( y los (rios|lagos))?|region de o ?higgins|"
    r"libertador general bernardo o ?higgins|los rios y los lagos", re.I)
INFERRED_HORIZON = 90
MAX_DATES = 15
YEAR_RE = re.compile(r"\b20\d{2}\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2}\b")


def _og_title(page_html):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', page_html or "", re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title', page_html or "", re.I)
    return html.unescape(m.group(1)) if m else ""


def _clean_title(text, source):
    """Quita el sufijo con el nombre del sitio: «Elektra | Teatro Municipal» -> «Elektra»."""
    text = " ".join(html.unescape(text or "").split())
    site = metadata.normalize(source.get("name") or "")
    host = urlparse(source.get("url") or "").netloc.lower().removeprefix("www.").split(".")[0]
    for sep in (" | ", " – ", " — ", " - "):
        if sep in text:
            head, tail = text.rsplit(sep, 1)
            t = metadata.normalize(tail)
            if head.strip() and t and (t in site or site in t or host in t.replace(" ", "")):
                text = head.strip()
    return text[:160].strip()


def _is_generic(title, source):
    norm = metadata.normalize(title)
    names = {metadata.normalize(source.get("name") or "")}
    host = urlparse(source.get("url") or "").netloc.lower().removeprefix("www.").split(".")[0]
    site = metadata.normalize(source.get("name") or "")
    return (len(norm) < 4 or norm in names or norm == host or (norm and norm in site)
            or any(norm == g or norm.startswith(g + " ") and len(norm) < 25 for g in GENERIC_TITLES))


def is_detail_url(url, source):
    p = urlparse(url)
    start = urlparse(source.get("url") or "")
    path = p.path.lower()
    if p.netloc.lower().removeprefix("www.") != start.netloc.lower().removeprefix("www."):
        return False
    if path.rstrip("/") == start.path.lower().rstrip("/") or any(x in path for x in LISTING_PARTS):
        return False
    segments = [s for s in path.split("/") if s]
    if not segments or segments[-1] in LISTING_SEGMENTS:
        return False
    if source.get("source_type") == "venue":
        return True
    # Municipios y agregadores: la pista debe estar en una carpeta de la ruta
    # (/evento/, /actividades/), no solo en el título de una noticia
    # (/v2/conoce-los-seleccionados-feria-…) ni bajo /noticias/.
    folders = segments[:-1]
    if any(f in NEWS_FOLDERS for f in folders):
        return False
    return any(h in f for f in folders for h in PATH_HINTS)


def _without_regions(text):
    """«Magallanes y de la Antártica Chilena» no es la comuna Antártica."""
    return REGION_PHRASES.sub(" ", metadata.strip_accents(text or "").lower())


def _is_listing(page_html, page_url):
    """Página de categoría: enlaza a varias fichas hijas de su propia ruta."""
    from scrapers.common import absolute_links
    base = urlparse(page_url).path.rstrip("/") + "/"
    children = {urlparse(u).path.rstrip("/") for u, _ in absolute_links(page_html, page_url)
                if urlparse(u).path.startswith(base) and urlparse(u).path.rstrip("/") + "/" != base}
    return len(children) >= LISTING_LINKS


def _trusted_dates(block, ref):
    """(inicio, fin) del bloque si la fecha es confiable y vigente; si no, None."""
    start, end = metadata.parse_date_range(block, ref)
    if not start:
        return None
    s = date.fromisoformat(start)
    e = date.fromisoformat(end) if end else s
    explicit = bool(YEAR_RE.search(block))
    years = set(re.findall(r"\b(20\d{2})\b", block))
    if years and str(s.year) not in years and str(e.year) not in years:
        return None  # «9 al 19 de diciembre | 2020»: el año escrito no es el inferido
    if e < ref:
        return None
    if not explicit and s > ref + timedelta(days=INFERRED_HORIZON):
        return None
    return s, e


def event_from_page(page_html, page_url, source, communes, ref=None):
    """Devuelve un evento (dict) o None si no se cumplen todos los resguardos."""
    ref = ref or date.today()
    if (not source.get("official") or source.get("radar_only")
            or source.get("source_type") not in ALLOWED_TYPES or not is_detail_url(page_url, source)):
        return None
    page = parse_page(page_html)
    # og:title suele ser propio de cada página; el primer h1 a veces es el logo del sitio.
    candidates = [_og_title(page_html)] + page.headings[:1] + [page.title]
    title = next((t for t in (_clean_title(c, source) for c in candidates if c)
                  if t and not _is_generic(t, source)), "")
    if not title or NOT_EVENT_TITLE.search(metadata.strip_accents(title)):
        return None
    if _is_listing(page_html, page_url):
        return None
    found = []
    for i, block in enumerate(page.blocks):
        if len(block) > 400:
            continue
        span = _trusted_dates(block, ref)
        if span:
            found.append((span, i))
    distinct = {span for span, _ in found}
    if not found or len(distinct) > MAX_DATES:
        return None
    start = min(s for (s, _), _ in found)
    end = max(e for (s, e), _ in found if s <= start + timedelta(days=END_WINDOW))
    first = next(i for (s, _), i in found if s == start)
    near = page.blocks[max(0, first - 1):first + 3]
    names = [c["name"] for c in communes]
    commune = source.get("commune") or next(
        (c for c in (metadata.detect_commune(_without_regions(b), names) for b in near) if c), None)
    if not commune:
        return None
    price_value, price_status = metadata.parse_price(" ".join(near))
    when = page.blocks[first]
    return {
        "title": title, "description": None,
        "date": start.isoformat(),
        "end_date": end.isoformat() if end > start else None,
        "time": metadata.parse_time(when), "end_time": None,
        "venue": None, "address": None, "commune": commune,
        "category": metadata.guess_category(title + " " + " ".join(near)),
        "tags": [PAGE_TAG],
        "price_value": price_value, "price_status": price_status,
        "status": "Por confirmar",
        "source": source["name"], "source_url": page_url,
        "source_type": source.get("source_type"), "source_priority": source.get("source_priority", 3),
        "official": True, "image_url": extract_official_image(page_html, page_url),
        "single_event_page": True,
    }
