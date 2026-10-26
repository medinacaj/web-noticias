#!/usr/bin/env python3
"""
Noticias del Momento — recolector y generador de sitio estático.

Fuentes: Google Noticias (RSS, sin límite) + GNews API (verificación cruzada,
consultada cada 3 horas para respetar el plan gratuito de 100 solicitudes/día).

En cada ejecución:
  1. Recolecta titulares por categoría.
  2. Los fusiona con data/historial.json (ventana de 24 h) sin duplicar noticias.
  3. Genera en public/ un sitio YA RENDERIZADO, que no depende de JavaScript:
     index.html, 404.html, sitemap.xml y robots.txt, más los archivos de static/.

Uso:
  python3 fetch_noticias.py                    # ejecución normal (la usa GitHub Actions)
  python3 fetch_noticias.py --solo-render      # regenera el sitio sin consultar fuentes
  python3 fetch_noticias.py --importar x.json  # pruebas con noticias propias en JSON

Variables de entorno:
  GNEWS_API_KEY     clave de gnews.io (opcional; sin ella se usa solo RSS)
  SITE_URL          URL pública definitiva sin barra final (ej: https://noticias.midominio.cl).
                    Si no se define, se deduce de GITHUB_REPOSITORY (GitHub Pages).
  GSC_VERIFICATION  código de verificación de Google Search Console (opcional)
"""

import argparse
import difflib
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

# ---------- CONFIGURACIÓN ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.html")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEFAULT_HISTORY = os.path.join(BASE_DIR, "data", "historial.json")
DEFAULT_OUT = os.path.join(BASE_DIR, "public")

TZ_CHILE = ZoneInfo("America/Santiago")
USER_AGENT = "Mozilla/5.0 (compatible; NoticiasDelMomento/2.0)"

STORIES_PER_CATEGORY = 24  # seis iniciales, resto progresivo
WINDOW_HOURS = 24            # cuánto tiempo permanece una noticia en el sitio
FUTURE_TOLERANCE = timedelta(minutes=15)  # pequeño desfase del reloj editorial
MAX_HISTORY = 400            # tope de noticias guardadas en el historial
SIMILARITY_THRESHOLD = 0.6   # umbral para considerar dos titulares "la misma noticia"
RSS_LIMIT = 15

GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "").strip()
GNEWS_EVERY_HOURS = 3        # 6 categorías x 8 corridas/día = 48 solicitudes (límite gratis: 100)

SITE_NAME = "Noticias del Momento"
SITE_TITLE = "Noticias de Chile y el mundo hoy | Noticias del Momento"
SITE_DESCRIPTION = (
    "Noticias de Chile y el mundo: nacional, regiones, política, economía, tecnología, "
    "salud, clima, cultura y deportes, con enlaces a los medios originales."
)

GOOGLE_RSS = "https://news.google.com/rss/headlines/section/topic/{topic}?hl=es-419&gl=CL&ceid=CL:es-419"

CATEGORIES = [
    {"key": "nacional",      "label": "Nacional",                  "google_topic": "NATION",        "gnews": "nation"},
    {"key": "latinoamerica", "label": "Latinoamérica"},
    {"key": "internacional", "label": "Internacional",             "google_topic": "WORLD",         "gnews": "world"},
    {"key": "economia",      "label": "Economía y negocios",       "google_topic": "BUSINESS",      "gnews": "business",      "short": "Economía"},
    {"key": "tecnologia",    "label": "Ciencia y tecnología",      "google_topic": "TECHNOLOGY",    "gnews": "technology"},
    {"key": "deportes",      "label": "Deportes",                  "google_topic": "SPORTS",        "gnews": "sports"},
    {"key": "cultura",       "label": "Cultura y entretenimiento", "google_topic": "ENTERTAINMENT", "gnews": "entertainment", "short": "Cultura"},
    {"key": "regiones", "label": "Regiones", "google_query": "(Biobío OR Ñuble OR Concepción OR Valparaíso OR Antofagasta OR Araucanía) noticias Chile"},
    {"key": "politica", "label": "Política", "google_query": "(Gobierno OR Congreso OR Senado OR política) Chile"},
    # Medioambiente incluye clima y es sección propia (decisión del usuario, 2026-10-25).
    {"key": "medioambiente", "label": "Medioambiente", "google_query": "(medioambiente OR cambio climático OR meteorología OR clima) Chile"},
    # Salud es un subtema de «Ciencia y tecnología»: rótulo propio en tarjetas y filtros, sin entrada
    # aparte en el menú. La clave se mantiene para no romper el historial ni las anclas publicadas.
    {"key": "salud-ciencia", "label": "Salud", "google_query": "(salud pública OR medicina OR hospitales OR enfermedades) Chile"},
]
CATEGORY_LABELS = {c["key"]: c["label"] for c in CATEGORIES}

# Feeds RSS directos de medios (opcional). Sus enlaces apuntan a la nota original y no a
# Google Noticias. Si un feed falla, se informa en el registro y el resto sigue funcionando.
DIRECT_FEEDS = {
    "internacional": [("https://feeds.bbci.co.uk/mundo/rss.xml", "BBC News Mundo")],
}

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def resolve_site_url():
    url = os.environ.get("SITE_URL", "").strip().rstrip("/")
    if url:
        return url
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        owner = owner.lower()
        if name.lower() == f"{owner}.github.io":
            return f"https://{owner}.github.io"
        return f"https://{owner}.github.io/{name}"
    return "https://TU-USUARIO.github.io/noticias-del-momento"


SITE_URL = resolve_site_url()


# ---------- UTILIDADES ----------

def esc(text):
    return html.escape(str(text or ""), quote=True)


def parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_title(title):
    text = re.sub(r"[^\w\s]", " ", (title or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def is_similar(a, b):
    matcher = difflib.SequenceMatcher(None, a, b)
    return (matcher.real_quick_ratio() >= SIMILARITY_THRESHOLD
            and matcher.quick_ratio() >= SIMILARITY_THRESHOLD
            and matcher.ratio() >= SIMILARITY_THRESHOLD)


def is_google_link(url):
    return "news.google." in (url or "")


def shorten(text, limit):
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def clean_summary(title, raw):
    """Devuelve un extracto real o cadena vacía. Google Noticias suele repetir el
    titular y el medio en la descripción, lo que no es un resumen útil."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    head = normalize_title(text)[: len(normalize_title(title)) + 30]
    if difflib.SequenceMatcher(None, normalize_title(title), head).ratio() > 0.6:
        return ""
    return shorten(text, 220)


def http_get(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


# ---------- RECOLECCIÓN ----------

MEDIA_NS = "{http://search.yahoo.com/mrss/}"


def safe_image(url):
    url = (url or "").strip()
    return url if url.startswith("https://") else ""  # evita contenido mixto http


def source_domain(source_url, article_url=""):
    """Dominio editorial seguro; nunca atribuir noticias al agregador Google."""
    for value in (source_url, article_url):
        try:
            parsed = urllib.parse.urlsplit((value or "").strip())
            host = (parsed.hostname or "").lower().rstrip(".")
        except ValueError:
            continue
        if (parsed.scheme == "https" and host and "." in host
                and not parsed.username and not parsed.password
                and not is_google_link(value)
                and re.fullmatch(r"[a-z0-9.-]+", host)):
            return host
    return ""


def source_mark(story):
    """Logo del medio, con monograma visible cuando falta o falla la imagen."""
    sources = story.get("sources") or ["Fuente"]
    initial = next((ch.upper() for ch in sources[0] if ch.isalnum()), "N")
    domain = source_domain(story.get("source_url"), story.get("link"))
    image = ""
    if domain:
        url = "https://www.google.com/s2/favicons?" + urllib.parse.urlencode(
            {"domain": domain, "sz": "64"})
        image = (f'<img src="{esc(url)}" alt="" width="18" height="18" '
                 f'loading="lazy" decoding="async" referrerpolicy="no-referrer" '
                 f'onerror="this.hidden=true">')
    return (f'<span class="source-mark" aria-hidden="true">'
            f'<span class="source-initial">{esc(initial)}</span>{image}</span>')


def rss_image(node):
    for tag in (MEDIA_NS + "content", MEDIA_NS + "thumbnail"):
        element = node.find(tag)
        if element is not None and element.get("url"):
            return safe_image(element.get("url"))
    enclosure = node.find("enclosure")
    if enclosure is not None and (enclosure.get("type") or "").startswith("image"):
        return safe_image(enclosure.get("url"))
    return ""


def fetch_rss(url, category, default_source=None, *, metadata_only=False):
    root = ET.fromstring(http_get(url))
    items = []
    for node in root.findall(".//item")[:RSS_LIMIT]:
        title = html.unescape((node.findtext("title") or "").strip())
        source_node = node.find("source")
        source = source_node.text.strip() if source_node is not None and source_node.text else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)].strip()
        if not source:
            if default_source:
                source = default_source
            elif " - " in title:
                title, source = [part.strip() for part in title.rsplit(" - ", 1)]
        from scripts.latam import country_codes, explicit_date
        if (metadata_only or category == "latinoamerica" or (category == "internacional"
                and any(code != "CL" for code in country_codes(title)))):
            published = explicit_date(node.findtext("pubDate"))
        else:
            published = parse_date(node.findtext("pubDate"))
        items.append({
            "category": category,
            "title": title,
            "source": source or "Fuente",
            "source_url": (source_node.get("url") or "").strip() if source_node is not None else (url if default_source else ""),
            "link": (node.findtext("link") or "").strip(),
            "published": to_iso(published) if published else None,
            "summary": "" if metadata_only or category == "latinoamerica" else clean_summary(title, node.findtext("description")),
            "image": "" if metadata_only or category == "latinoamerica" else rss_image(node),
        })
    return items


def fetch_gnews(cat):
    params = {"category": cat["gnews"], "lang": "es", "country": "cl", "max": "10", "apikey": GNEWS_API_KEY}
    data = json.loads(http_get("https://gnews.io/api/v4/top-headlines?" + urllib.parse.urlencode(params)))
    items = []
    for article in data.get("articles", []):
        title = (article.get("title") or "").strip()
        from scripts.latam import country_codes, explicit_date
        regional = cat["key"] == "internacional" and any(code != "CL" for code in country_codes(title))
        published = (explicit_date if regional else parse_date)(article.get("publishedAt"))
        items.append({
            "category": cat["key"],
            "title": title,
            "source": (article.get("source") or {}).get("name") or "GNews",
            "source_url": (article.get("source") or {}).get("url") or "",
            "link": (article.get("url") or "").strip(),
            "published": to_iso(published) if published else None,
            "summary": clean_summary(title, article.get("description")),
            "image": safe_image(article.get("image")),
        })
    return items


def category_google_url(cat):
    """Feeds de búsqueda para nuevas secciones; sin presuponer topic IDs."""
    if cat["key"] == "latinoamerica":
        from scripts.latam import search_urls
        return search_urls()[0]
    if cat.get("google_query"):
        params = urllib.parse.urlencode({
            "q": cat["google_query"], "hl": "es-419", "gl": "CL", "ceid": "CL:es-419"
        })
        return "https://news.google.com/rss/search?" + params
    return GOOGLE_RSS.format(topic=cat["google_topic"])


def collect(now):
    use_gnews = bool(GNEWS_API_KEY) and now.hour % GNEWS_EVERY_HOURS == 0
    if GNEWS_API_KEY and not use_gnews:
        print(f"GNews: se omite en esta corrida (se consulta cada {GNEWS_EVERY_HOURS} horas por la cuota gratuita).")
    from scripts.latam import search_urls, prepare_item, country_codes
    from scripts.regional_sources import load_catalog
    catalog = load_catalog()
    items = []
    for cat in CATEGORIES:
        key, count = cat["key"], 0
        urls = search_urls() if key == "latinoamerica" else [category_google_url(cat)]
        for url in urls:
            try:
                got = fetch_rss(url, key)
                if key == "latinoamerica":
                    got = [record for entry in got if (record := prepare_item(entry, now, catalog))]
                items += got
                count += len(got)
            except Exception as error:  # una fuente caída no debe detener las demás
                print(f"[aviso] Google Noticias falló en {key}: {error}")
        for url, name in DIRECT_FEEDS.get(key, []):
            try:
                got = fetch_rss(url, key, default_source=name)
                items += got
                count += len(got)
            except Exception as error:
                print(f"[aviso] Feed directo {name} falló: {error}")
        if use_gnews and cat.get('gnews'):
            try:
                got = fetch_gnews(cat)
                items += got
                count += len(got)
            except Exception as error:
                print(f"[aviso] GNews falló en {key}: {error}")
        print(f"{cat['label']}: {count} notas recolectadas")
    from scripts.entertainment import collect_entertainment
    if any(cat["key"] == "cultura" for cat in CATEGORIES):
        items += collect_entertainment(now, fetch=fetch_rss)
    from scripts.global_sources import collect_world
    items += collect_world(now, fetch=fetch_rss)
    from scripts.regional_sources import collect_regional
    regional = collect_regional(now)
    items += regional
    if regional:
        print(f"RSS regionales revisados: {len(regional)} titulares recolectados")
    # WORLD/GNews ya consultados pueden aportar cobertura regional; misma puerta
    # de permisos y minimización que las búsquedas nuevas, sin llamadas extra.
    result = []
    for item in items:
        if (item.get("category") == "internacional"
                and any(code != "CL" for code in country_codes(item.get("title")))):
            item = prepare_item(item, now, catalog)
        if item:
            result.append(item)
    return result


# ---------- HISTORIAL (24 h, sin duplicados) ----------

def load_history(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[aviso] No se pudo leer el historial ({error}); se parte desde cero.")
        return []
    stories = data.get("noticias", []) if isinstance(data, dict) else []
    from scripts.latam import classify
    from scripts.regional_sources import load_catalog
    catalog = load_catalog()
    for story in stories:
        classify(story, catalog)
        story["_norm"] = normalize_title(story.get("title", ""))
    return stories


def load_signals(path):
    """Metadatos acumulados; separados de la ventana de portada de 24 horas."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            items = data.get("senales_historicas", [])
            start = data.get("senales_inicio", "")
            return (items if isinstance(items, list) else []), start
    except (OSError, json.JSONDecodeError):
        pass
    return [], ""


def save_history(path, stories, now, signals_archive=None, signals_started=""):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    clean = [{k: v for k, v in s.items() if not k.startswith("_")} for s in stories]
    data = {"actualizado": to_iso(now), "noticias": clean}
    if signals_archive is not None:
        data["senales_inicio"] = signals_started or to_iso(now)
        data["senales_historicas"] = signals_archive
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)


def coverage_entry(item):
    """Solo enlaces HTTPS directos a publicaciones; conservar sus títulos originales."""
    url = (item.get("link") or "").strip()
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or is_google_link(url)):
        return None
    outlet = (item.get("source") or (item.get("sources") or [""])[0] or "").strip()
    title = (item.get("title") or "").strip()
    if not outlet or not title:
        return None
    date = parse_date(item.get("published"))
    return {"source": outlet, "title": title, "link": url,
            "published": to_iso(date) if date else ""}


def coverage_items(story):
    """Nunca reconstruir enlaces desde el nombre de una fuente."""
    seen_sources, seen_urls, result = set(), set(), []
    for item in story.get("coverages") or []:
        if not isinstance(item, dict):
            continue
        entry = coverage_entry(item)
        if not entry:
            continue
        source_key = entry["source"].casefold()
        if source_key in seen_sources or entry["link"] in seen_urls:
            continue
        seen_sources.add(source_key)
        seen_urls.add(entry["link"])
        result.append(entry)
    return result[:12]


def coverage_control(story):
    rows = coverage_items(story)
    if len(rows) < 2:
        return ""
    content = "".join(
        f'<li><span class="coverage-source">{esc(x["source"])}</span>'
        f'<a href="{esc(x["link"])}" rel="noopener">{esc(x["title"])}</a>'
        + (f'<time datetime="{esc(x["published"])}">{esc(x["published"][:10])}</time>'
           if x["published"] else "") + '</li>'
        for x in rows
    )
    return (f'<button type="button" class="coverage-trigger" aria-haspopup="dialog" '
            f'data-coverage-trigger>Otras coberturas <span aria-hidden="true">↗</span></button>'
            f'<template class="coverage-data"><h2>Otras coberturas de esta noticia</h2>'
            f'<p>Publicaciones relacionadas detectadas de {len(rows)} medios. '
            f'Los enlaces conservan los titulares originales; no se infieren diferencias de enfoque.</p>'
            f'<ol class="coverage-list">{content}</ol></template>')


def merge(stories, items, now, window_hours=WINDOW_HOURS):
    """Agrupa titulares vigentes; deduplica la misma URL sin renovar su fecha."""
    added = 0
    limit = now - timedelta(hours=window_hours)
    future_limit = now + FUTURE_TOLERANCE
    from scripts.latam import classify, merge_countries
    for original in items:
        item = classify(dict(original))
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        if not title or not link or item.get("category") not in CATEGORY_LABELS:
            continue
        norm = normalize_title(title)
        incoming_sources = item.get("sources") or [item.get("source") or "Fuente"]
        published = parse_date(item.get("published"))
        if published and published > future_limit:
            continue
        incoming_time = published or now
        published = to_iso(published) if published else None
        # La URL canónica identifica una nota aunque cambie el titular o tenga tracking.
        # La similitud difusa, en cambio, solo agrupa noticias dentro de una
        # categoría: no debe absorber Salud, Ciencia o Medioambiente en Nacional.
        from scripts.dedupe_history import canonical_key
        try:
            article_key = canonical_key(link)
        except ValueError:
            continue
        match = next((s for s in stories
                      if canonical_key(s["link"]) == article_key), None)
        # Una nota caducada no debe absorber ni envejecer otra URL vigente,
        # independientemente del orden de llegada. La misma URL sigue deduplicándose.
        if match is None and incoming_time >= limit:
            match = next((s for s in stories
                          if s["category"] == item["category"]
                          and limit <= (story_time(s) or now) <= future_limit
                          and not s.get("metadata_only") and not item.get("metadata_only")
                          and is_similar(norm, s["_norm"])), None)
        if match:
            merge_countries(match, item)
            coverages = coverage_items(match)
            entry = coverage_entry(item)
            if entry and all(x["link"] != entry["link"] for x in coverages):
                coverages.append(entry)
            match["coverages"] = coverages[:12]
            for source in incoming_sources:
                if source and source not in match["sources"]:
                    match["sources"].append(source)
            if ((is_google_link(match["link"]) and not is_google_link(link))
                    or (match["link"].startswith("http://") and link.startswith("https://"))):
                match["link"] = link  # preferir el enlace directo y HTTPS al mismo artículo
            if not match.get("summary") and item.get("summary"):
                match["summary"] = item["summary"]
            if (not source_domain(match.get("source_url"), match.get("link"))
                    and source_domain(item.get("source_url"), link)):
                match["source_url"] = item.get("source_url") or link
            if not match.get("image") and item.get("image"):
                match["image"] = safe_image(item["image"])
            # first_seen también fija la edad cuando aún falta fecha editorial.
            # Incorporar una fecha posterior rejuvenecería la misma noticia.
            previous_time = story_time(match)
            if published and (not previous_time or incoming_time <= previous_time):
                match["published"] = published
            for field in ("publisher_id", "source_country", "source_country_label", "discovery_edition"):
                if not match.get(field) and item.get(field):
                    match[field] = item[field]
            if item.get("metadata_only") or match.get("metadata_only"):
                match["metadata_only"] = True
                match["summary"] = ""
                match["image"] = ""
        else:
            stories.append({
                "category": item["category"],
                "title": title,
                "summary": "" if item.get("metadata_only") else item.get("summary") or "",
                "image": "" if item.get("metadata_only") else safe_image(item.get("image")),
                "source_url": item.get("source_url") or (link if not is_google_link(link) else ""),
                "sources": [s for s in incoming_sources if s],
                "coverages": [coverage_entry(item)] if coverage_entry(item) else [],
                "link": link,
                "published": published,
                "first_seen": to_iso(now),
                "_norm": norm,
                **{key: item[key] for key in ("publisher_id", "source_country",
                   "source_country_label", "metadata_only", "coverage_countries", "discovery_edition") if key in item},
            })
            added += 1
    return added


def story_time(story):
    return parse_date(story.get("published")) or parse_date(story.get("first_seen"))


def hours_old(story, now):
    moment = story_time(story) or now
    return max(0.0, (now - moment).total_seconds() / 3600)


def prune(stories, now, window_hours):
    limit = now - timedelta(hours=window_hours)
    future_limit = now + FUTURE_TOLERANCE
    kept = [s for s in stories if limit <= (story_time(s) or now) <= future_limit]
    kept.sort(key=lambda s: story_time(s) or now, reverse=True)
    return kept[:MAX_HISTORY]


# ---------- SELECCIÓN ----------

def score(story, now):
    # más medios que la reportan = más relevante; pierde un punto cada 6 horas
    return len(story["sources"]) - hours_old(story, now) / 6


def balance_section_sources(candidates, limit=STORIES_PER_CATEGORY):
    """Distribuir medios entre las seis fichas iniciales sin suprimir notas.

    Si hay pocas fuentes distintas, el espacio restante se completa en el
    orden original de relevancia; el resto sigue disponible con «Ver más».
    """
    from scripts.source_diversity import diverse_prefix
    selected = diverse_prefix(candidates, min(6, limit))
    selected_ids = {id(story) for story in selected}

    for story in candidates:
        if len(selected) >= limit:
            break
        if id(story) in selected_ids:
            continue
        selected.append(story)
        selected_ids.add(id(story))
    return selected


def select(stories, now):
    ranked = sorted(stories, key=lambda s: score(s, now), reverse=True)
    recent = [s for s in ranked if hours_old(s, now) <= 12]
    candidates = (recent or ranked)[:5]
    lead = next((s for s in candidates if s.get("image")), candidates[0] if candidates else None)
    rest = [s for s in ranked if s is not lead]
    # Destacadas: las mejor puntuadas, sin vaciar ninguna sección (se respeta al menos una por categoría)
    remaining = {}
    for story in rest:
        remaining[story["category"]] = remaining.get(story["category"], 0) + 1
    from scripts.source_diversity import publisher_key
    secondary = []
    used_editors = {publisher_key(lead)} if lead else set()
    from scripts.presentation_groups import canonical_section
    used_categories = {canonical_section(lead["category"])} if lead else set()
    relevant = [s for s in rest if hours_old(s, now) <= 12][:12]
    for require_new_editor, require_new_category in ((True, True), (True, False), (False, False)):
        for story in relevant if require_new_category else rest:
            if len(secondary) == 3:
                break
            if any(story is selected for selected in secondary):
                continue
            if remaining[story["category"]] < 2:
                continue
            editor = publisher_key(story)
            if require_new_category and canonical_section(story["category"]) in used_categories:
                continue
            if require_new_editor and editor in used_editors:
                continue
            secondary.append(story)
            remaining[story["category"]] -= 1
            used_editors.add(editor)
            used_categories.add(canonical_section(story["category"]))
    used = {id(s) for s in secondary}
    by_category = {}
    for cat in CATEGORIES:
        candidates = [s for s in rest if s["category"] == cat["key"] and id(s) not in used]
        if cat["key"] == "cultura":
            from scripts.entertainment import balance_entertainment
            chosen = balance_entertainment(candidates, STORIES_PER_CATEGORY)
        else:
            chosen = balance_section_sources(candidates)
        if chosen:
            by_category[cat["key"]] = chosen
    counts = {}
    for story in stories:
        counts[story["category"]] = counts.get(story["category"], 0) + 1
    from scripts.dedupe_history import canonical_key
    latest, latest_urls = [], set()
    # first_seen indica recolección, no publicación: no convierte una nota
    # sin fecha editorial en «Lo último».
    dated = [s for s in stories if parse_date(s.get("published")) is not None]
    for story in sorted(dated, key=lambda s: parse_date(s["published"]), reverse=True):
        url = canonical_key(story.get("link", ""))
        if not url or url in latest_urls:
            continue
        latest.append(story)
        latest_urls.add(url)
        if len(latest) == 6:
            break
    return {
        "lead": lead,
        "secondary": secondary,
        "by_category": by_category,
        "latest": latest,
        "most_reported": max(ranked, key=lambda s: (len(s["sources"]), -hours_old(s, now))) if ranked else None,
        "most_recent": min(rest, key=lambda s: hours_old(s, now)) if rest else None,  # distinta de la portada
        "busiest": max(counts.items(), key=lambda kv: kv[1]) if counts else None,
        "total": len(stories),
        "outlets": len({src for s in stories for src in s["sources"]}),
    }


# ---------- RENDER ----------

def time_ago(story, now):
    hours = hours_old(story, now)
    minutes = int(hours * 60)
    if minutes < 60:
        return f"hace {max(minutes, 1)} min"
    if hours < 24:
        return f"hace {int(hours)} h"
    days = int(hours // 24)
    return "hace 1 día" if days == 1 else f"hace {days} días"


def human_datetime(moment):
    local = moment.astimezone(TZ_CHILE)
    return f"{local.day} {MESES[local.month - 1]} {local.year}, {local:%H:%M}"


def category_label(story):
    return CATEGORY_LABELS[story["category"]]


def title_link(story):
    from scripts.latam import country_labels
    countries = ", ".join(country_labels(story))
    from scripts.dedupe_history import canonical_key
    first_seen = story.get("first_seen") or ""
    if not parse_date(first_seen):
        first_seen = ""
    return (f'<a data-news-id="{esc(canonical_key(story["link"]))}" data-first-seen="{esc(first_seen)}" data-countries="{esc(countries)}" href="{esc(story["link"])}" rel="noopener" '
            f'data-cat="{esc(category_label(story))}" data-key="{story["category"]}" '
            f'data-sources="{esc(json.dumps(story.get("sources") or [], ensure_ascii=False))}">{esc(story["title"])}</a>')


def figure_html(story, eager=False):
    image = safe_image(story.get("image"))
    if not image:
        source = (story.get("sources") or ["Fuente"])[0]
        region_class, region_label = "", ""
        description = f"Medio de origen: {source}"
        if story.get("category") == "latinoamerica":
            from scripts.latam import country_labels
            countries = " · ".join(country_labels(story)) or "Latinoamérica"
            region_class = " media--region"
            region_label = f'<span class="region-label">{esc(countries)}</span>'
            description = f"Ficha de {countries}. Medio: {source}"
        return (f'<figure class="media media--source{region_class}" role="img" '
                f'aria-label="{esc(description)}">'
                f'<span class="source-visual">{source_mark(story)}'
                f'{region_label}'
                f'<span class="source-visual-name">{esc(source)}</span></span>'
                f'</figure>')
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<figure class="media"><img src="{esc(image)}" alt="" width="1200" height="675" '
            f'{loading} decoding="async" referrerpolicy="no-referrer">'
            f'</figure>')


def meta_html(story, now, read_link=False):
    sources = story["sources"]
    label = ", ".join(sources[:3]) + (f" y {len(sources) - 3} más" if len(sources) > 3 else "")
    moment = story_time(story) or now
    fresh = ' data-fresh="true"' if hours_old(story, now) <= 1 else ""
    country = (f'<span class="source-country">{esc(story["source_country_label"])}</span>'
               if story.get("source_country_label") else "")
    from scripts.latam import country_labels
    coverage = "".join(f'<span class="coverage-country" title="País mencionado en el titular">{esc(label)}</span>'
                       for label in country_labels(story))
    return (f'<p class="meta"><span class="src">{source_mark(story)}<span class="source-name">{esc(label)}</span></span>'
            f'{country}{coverage}<time datetime="{to_iso(moment)}"{fresh}>{time_ago(story, now)}</time>{coverage_control(story)}</p>')


def dek_html(story):
    return f'<p class="dek">{esc(story["summary"])}</p>' if story.get("summary") else ""


def render_breaking(sel, now):
    stories = sel.get("latest", [sel["most_recent"]] if sel.get("most_recent") else [])
    if not stories:
        return ""
    slides = "".join(
        f'<li class="breaking-item cat-{story["category"]}" title="{esc(story["title"])}">'
        f'<span class="breaking-category">{esc(category_label(story))}</span>'
        f'{title_link(story)}<time datetime="{to_iso(story_time(story))}">'
        f'{time_ago(story, now)}</time></li>' for story in stories
    )
    return ('<section class="breaking" data-carousel aria-label="Últimas noticias" '
            'aria-roledescription="carrusel"><div class="container breaking-inner">'
            '<h2 class="breaking-label"><span data-breaking-label>Lo último</span>'
            '<button type="button" class="breaking-pause" data-carousel-pause hidden '
            'aria-label="Pausar deslizamiento de Lo último" aria-pressed="false" '
            'aria-controls="latest-track" title="Pausar titulares">Lo último</button></h2>'
            f'<ol class="breaking-track" id="latest-track" tabindex="0" '
            f'aria-label="Titulares recientes, usa las flechas para desplazarte">{slides}</ol>'
            '</div></section>')


def topic_anchor(story, reserved):
    """Una ancla por tema publicado que no tiene sección independiente."""
    category = story["category"]
    if category in reserved:
        return ""
    reserved.add(category)
    from scripts.presentation_groups import canonical_section
    section = canonical_section(category)
    return f' id="cat-{esc(category)}" data-nav-topic="{esc(category)}" data-nav-section="{esc(section)}"'


def parent_topic_anchor(story, reserved):
    from scripts.presentation_groups import canonical_section
    parent = canonical_section(story["category"])
    return topic_anchor({"category": parent}, reserved) if parent != story["category"] else ""


def render_top(sel, now):
    lead = sel["lead"]
    if not lead:
        return ""
    grouped = sel.get("by_category", {})
    reserved = set(grouped) | {s["category"] for items in grouped.values() for s in items}
    lead_anchor = topic_anchor(lead, reserved)
    parent_anchor = parent_topic_anchor(lead, reserved)
    lead_html = (
        f'<article class="lead cat-{lead["category"]}{" lead--text" if not safe_image(lead.get("image")) else ""}" id="portada">{figure_html(lead, eager=True)}'
        f'<p class="kicker"{parent_anchor}>Portada · {esc(category_label(lead))}</p>'
        f'<h2 class="lead-title"{lead_anchor}>{title_link(lead)}</h2>{dek_html(lead)}{meta_html(lead, now, True)}</article>'
    )
    items = "".join(
        f'<li class="cat-{s["category"]}"><article class="rail-item">{figure_html(s)}'
        f'<p class="kicker"{parent_topic_anchor(s, reserved)}>{esc(category_label(s))}</p>'
        f'<h3{topic_anchor(s, reserved)}>{title_link(s)}</h3>{meta_html(s, now)}</article></li>'
        for s in sel["secondary"]
    )
    if not items:
        return f'<div class="top-grid top-grid--single">{lead_html}</div>'
    return (f'<div class="top-grid">{lead_html}<div class="top-aside">'
            f'<h2 class="rail-title"><span>Destacadas</span><button type="button" '
            f'id="visit-updates" class="visit-updates" hidden></button></h2><ol class="rail-list">{items}</ol></div></div>')


def render_edition_count(sel):
    """Contar las noticias publicadas en tarjetas, sin duplicar URLs o medios."""
    from scripts.dedupe_history import canonical_key
    published = ([sel["lead"]] if sel.get("lead") else []) + sel.get("secondary", [])
    published += [story for items in sel.get("by_category", {}).values() for story in items]
    urls = {canonical_key(story["link"]) for story in published}
    sources = {name.strip() for story in published for name in story.get("sources", []) if name.strip()}
    count, outlets = len(urls), len(sources)
    return (f'<p class="edition-count" data-news-count="{count}" '
            f'title="Noticias publicadas en esta portada y sus secciones">'
            f'{count} {"noticia" if count == 1 else "noticias"} · '
            f'{outlets} {"medio" if outlets == 1 else "medios"}</p>')


def render_coverage_radar(stories):
    """Radar conservador: no infiere tendencia o crecimiento desde una instantánea."""
    prominent = [s for s in stories if len(set((s.get("sources") or []))) >= 4]
    prominent.sort(key=lambda s: len(set(s["sources"])), reverse=True)
    if not prominent:
        return ""
    items = "".join(
        f'<li><a href="{esc(story["link"])}" rel="noopener">'
        f'{esc(story["title"])}</a><span>{len(set(story["sources"]))} medios distintos</span></li>'
        for story in prominent[:5]
    )
    return (f'<section class="coverage-radar" aria-labelledby="coverage-radar-title">'
            f'<div class="radar-head"><h2 id="coverage-radar-title">Radar de cobertura</h2>'
            f'<span>4 o más medios</span></div>'
            f'<p>Noticias publicadas por varios medios. No implica que estén creciendo en popularidad.</p>'
            f'<ul>{items}</ul></section>')


def recent_section_stories(stories):
    """Orden visible inicial; conserva la selección editorial y no muta la entrada."""
    return sorted(stories, key=lambda story: story_time(story).timestamp() if story_time(story) else float("-inf"), reverse=True)


def render_sections(by_category, now):
    from scripts.presentation_groups import PRESENTATION_LABELS
    reserved = set(by_category)
    blocks = []
    present = [c for c in CATEGORIES if c["key"] in by_category]
    for number, cat in enumerate(present, start=1):
        original = by_category[cat["key"]]
        editorial_order = {id(story): index for index, story in enumerate(original)}
        stories = recent_section_stories(original)
        feature, rest = stories[0], stories[1:]
        feature_html = (f'<article class="feature" data-original-order="{editorial_order[id(feature)]}">{figure_html(feature)}'
                        f'<div class="news-body"><p class="kicker">{esc(category_label(feature))}</p>'
                        f'<h3 class="feature-title"{topic_anchor(feature, reserved)}>{title_link(feature)}</h3>'
                        f'{dek_html(feature)}{meta_html(feature, now, True)}</div></article>')
        compact = "".join(
            f'<li data-original-order="{editorial_order[id(s)]}"{" data-extra" if i >= 5 else ""}><article class="compact">{figure_html(s)}'
            f'<div class="news-body"><p class="kicker">{esc(category_label(s))}</p>'
            f'<h3{topic_anchor(s, reserved)}>{title_link(s)}</h3>{meta_html(s, now)}</div></article></li>'
            for i, s in enumerate(rest))
        grid_class = "section-grid" if compact else "section-grid section-grid--single"
        compact_html = f'<ul class="compact-list">{compact}</ul>' if compact else ""
        count = len(stories)
        more = (f'<button type="button" class="show-more" data-show-more '
                f'aria-controls="noticias-{esc(cat["key"])}" data-step="6">'
                f'Ver más noticias <span aria-hidden="true">↓</span></button>'
                if count > 6 else "")
        blocks.append(
            f'<section class="section cat-{cat["key"]}" id="cat-{cat["key"]}" aria-labelledby="titulo-{cat["key"]}">'
            f'<div class="section-head"><span class="section-num">{number:02d}</span>'
            f'<h2 id="titulo-{cat["key"]}">{esc(PRESENTATION_LABELS.get(cat["key"], cat["label"]))}</h2>'
            f'<span class="section-count">{count} {"noticia" if count == 1 else "noticias"}</span></div>'
            f'<div class="{grid_class}" id="noticias-{esc(cat["key"])}">{feature_html}{compact_html}</div>'
            f'{more}</section>'
        )
    return "\n".join(blocks)


def render_nav(sel, agenda=False):
    from scripts.presentation_groups import PRESENTATION_LABELS, canonical_section
    sections = set(sel["by_category"])
    published = ([sel["lead"]] if sel.get("lead") else []) + sel.get("secondary", [])
    published += [story for items in sel["by_category"].values() for story in items]
    available = sections | {canonical_section(story["category"]) for story in published}
    links = ['<li><a href="#portada">Portada</a></li>'] if sel["lead"] else []
    emitted = set()
    def entry(category):
        key = category["key"]
        label = PRESENTATION_LABELS.get(key, category["label"])
        return f'<li><a class="cat-{key}" href="#cat-{key}">{esc(label)}</a></li>'
    for category in CATEGORIES:
        key = category["key"]
        if key not in available or key in emitted:
            continue
        parent = canonical_section(key)
        if parent != key:
            continue
        links.append(entry(category))
        emitted.add(key)
    if agenda:
        links.append('<li><a class="cat-agenda" href="#cat-agenda">Agenda</a></li>')
    return "".join(links)


def build_jsonld(sel, now):
    page_url = SITE_URL + "/"
    ordered = ([sel["lead"]] if sel["lead"] else []) + sel["secondary"] + \
        [s for k in sel["by_category"] for s in recent_section_stories(sel["by_category"][k])]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": page_url + "#website", "url": page_url,
             "name": SITE_NAME, "inLanguage": "es-CL"},
            {"@type": "CollectionPage", "@id": page_url + "#webpage", "url": page_url,
             "name": SITE_TITLE, "description": SITE_DESCRIPTION, "inLanguage": "es-CL",
             "isPartOf": {"@id": page_url + "#website"}, "dateModified": to_iso(now),
             "mainEntity": {
                 "@type": "ItemList",
                 "numberOfItems": len(ordered),
                 "itemListElement": [
                     {"@type": "ListItem", "position": i, "url": s["link"], "name": s["title"]}
                     for i, s in enumerate(ordered, start=1)
                 ],
             }},
        ],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


PAGE_404 = """<!DOCTYPE html>
<html lang="es-CL">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Página no encontrada · Noticias del Momento</title>
<meta name="robots" content="noindex">
<link rel="icon" href="%%HOME%%favicon.svg?v=editorial" type="image/svg+xml">
<style>
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
    background:#FBFAF7;color:#07192E;text-align:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
  h1{font-family:Georgia,serif;font-size:34px;margin:0 0 10px;text-transform:uppercase}
  p{color:#6D7480}
  a{color:#C8102E;font-weight:600}
  @media (prefers-color-scheme:dark){body{background:#0B1420;color:#E9EDF2}p{color:#9BA5B1}a{color:#FF5C70}}
</style>
</head>
<body>
<main>
  <h1>Página no encontrada</h1>
  <p>La dirección que buscas no existe o fue movida.</p>
  <p><a href="%%HOME%%">Volver a Noticias del Momento</a></p>
</main>
</body>
</html>
"""


def build_site(stories, now, out_dir, window_hours=WINDOW_HOURS,
               signals_archive=None, signals_started="", agenda=None):
    sel = select(stories, now)
    from scripts.presentation_groups import group_sections
    sel["by_category"] = group_sections(sel["by_category"], STORIES_PER_CATEGORY)
    from scripts.editorial_signals import trending_topics, related_timeline, render_signals
    archive = signals_archive or []
    signals_html = render_signals(
        trending_topics(archive, now, signals_started),
        related_timeline(archive, now))
    with open(TEMPLATE_PATH, encoding="utf-8") as handle:
        page = handle.read()

    from scripts.newsletter import configured_newsletter, render_newsletter
    from scripts.adsense import configured_adsense
    newsletter = configured_newsletter(os.environ)
    adsense = configured_adsense(os.environ, SITE_URL)

    gsc_code = os.environ.get("GSC_VERIFICATION", "").strip()
    from scripts.agenda import render_agenda
    sections_shown = sum(1 for c in CATEGORIES if c["key"] in sel["by_category"])
    agenda_html = render_agenda(agenda or [], now, number=sections_shown + 1, source_mark=source_mark)
    nav = render_nav(sel, agenda=bool(agenda_html))
    replacements = {
        "%%TITLE%%": esc(SITE_TITLE),
        "%%DESCRIPTION%%": esc(SITE_DESCRIPTION),
        "%%SITE_NAME%%": esc(SITE_NAME),
        "%%CANONICAL%%": esc(SITE_URL + "/"),
        "%%OG_IMAGE%%": esc(SITE_URL + "/og-image.png"),
        "%%GSC_META%%": f'<meta name="google-site-verification" content="{esc(gsc_code)}">' if gsc_code else "",
        "%%ADSENSE_META%%": adsense["meta"],
        "%%ADSENSE_SCRIPT%%": adsense["script"],
        "%%ADSENSE_PRIVACY_LINK%%": adsense["footer"],
        "%%JSONLD%%": build_jsonld(sel, now),
        "%%UPDATED_ISO%%": to_iso(now),
        "%%UPDATED_HUMAN%%": human_datetime(now),
        "%%YEAR%%": str(now.astimezone(TZ_CHILE).year),
        "%%NAV%%": nav,
        "%%FOOTER_NAV%%": nav,
        "%%BREAKING%%": render_breaking(sel, now),
        "%%TOP%%": render_top(sel, now),
        "%%EDITION_COUNT%%": render_edition_count(sel),
        "%%RADAR%%": render_coverage_radar(stories),
        "%%SIGNALS%%": signals_html,
        "%%SECTIONS%%": render_sections(sel["by_category"], now),
        "%%AGENDA%%": agenda_html,
        "%%NEWSLETTER_SIGNUP%%": newsletter["signup_html"],
    }
    # Only the original template supplies tokens; news text remains literal.
    markers = re.compile(r"%%[A-Z_]+%%")
    leftover = [marker for marker in markers.findall(page) if marker not in replacements]
    if leftover:
        raise SystemExit(f"ERROR: la plantilla quedó con marcadores sin reemplazar: {leftover}")
    page = markers.sub(lambda match: replacements[match.group(0)], page)

    # Páginas propias y estables: no convertir enlaces a medios en páginas de noticias ficticias.
    from scripts.seo_pages import render_about_page, render_sitemap
    newsletter_html = render_newsletter(
        stories, now, SITE_URL, configuration=newsletter)
    about_html = render_about_page(SITE_URL)
    os.makedirs(out_dir, exist_ok=True)
    if os.path.isdir(STATIC_DIR):
        shutil.copytree(STATIC_DIR, out_dir, dirs_exist_ok=True)

    files = {
        "index.html": page,
        "sobre-el-portal.html": about_html,
        "boletin-diario.html": newsletter_html,
        "404.html": PAGE_404.replace("%%HOME%%", esc(SITE_URL + "/")),
        "robots.txt": f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",
        "sitemap.xml": render_sitemap(SITE_URL, to_iso(now)),
    }
    if adsense["ads_txt"]:
        files["ads.txt"] = adsense["ads_txt"]
    else:
        # Reusing the output directory must not retain an earlier authorization,
        # including one copied from static/ for a deployment at a different URL.
        ads_path = os.path.join(out_dir, "ads.txt")
        if os.path.lexists(ads_path):
            os.remove(ads_path)
    # Archivo «Últimos 7 días» (noindex): se regenera completo para que no queden días vencidos.
    from scripts.archive_pages import DIR as ARCHIVE_DIR, render_archive
    from scripts.presentation_groups import canonical_section
    shutil.rmtree(os.path.join(out_dir, ARCHIVE_DIR), ignore_errors=True)
    os.makedirs(os.path.join(out_dir, ARCHIVE_DIR), exist_ok=True)
    files.update(render_archive(archive, now, SITE_URL, CATEGORIES, canonical_section))
    for name, content in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(content)

    from scripts.public_feeds import write_public_feeds
    write_public_feeds(out_dir, stories, now, SITE_URL, CATEGORY_LABELS)

    total = (1 if sel["lead"] else 0) + len(sel["secondary"]) + sum(len(v) for v in sel["by_category"].values())
    print(f"Sitio generado en {out_dir}: {total} noticias publicadas · URL canónica {SITE_URL}/")


# ---------- PRINCIPAL ----------

def main():
    parser = argparse.ArgumentParser(description="Noticias del Momento — recolector y generador")
    parser.add_argument("--solo-render", action="store_true", help="no consulta fuentes; regenera desde el historial")
    parser.add_argument("--importar", metavar="JSON", help="carga noticias desde un archivo JSON (pruebas)")
    parser.add_argument("--ventana", type=float, default=WINDOW_HOURS, help="horas que permanece una noticia")
    parser.add_argument("--historial", default=DEFAULT_HISTORY)
    parser.add_argument("--salida", default=DEFAULT_OUT)
    parser.add_argument("--ahora", help="fecha/hora ISO a usar como 'ahora' (pruebas)")
    args = parser.parse_args()

    now = parse_date(args.ahora) if args.ahora else datetime.now(timezone.utc)
    archive, signals_started = load_signals(args.historial)
    stories = load_history(args.historial)
    print(f"Historial: {len(stories)} noticias previas")

    if args.importar:
        with open(args.importar, encoding="utf-8") as handle:
            items = json.load(handle)
        print(f"Importadas: {merge(stories, items, now, args.ventana)} noticias nuevas")
    elif not args.solo_render:
        items = collect(now)
        if not items:
            print("[aviso] Ninguna fuente respondió; se publica con el historial existente.")
        print(f"Nuevas: {merge(stories, items, now, args.ventana)} (el resto ya estaba publicado y solo sumó fuentes)")

    stories = prune(stories, now, args.ventana)
    if not stories:
        # Falla a propósito: GitHub Actions no publica una página vacía y te avisa por correo.
        print("ERROR: no hay noticias disponibles en la ventana de tiempo; no se publica el sitio.", file=sys.stderr)
        sys.exit(1)

    if not args.solo_render and not args.importar:
        # Enriquecer solo artículos visibles para evitar consultas masivas a editores.
        # Los errores de terceros nunca deben impedir publicar noticias.
        try:
            from scripts.article_images import enrich_visible_images
            enrich_visible_images(stories, select(stories, now), now)
        except Exception as error:
            print(f"[aviso] Recuperación editorial no disponible: {error}")

    # Reconciliar enlaces canónicos antes de guardar Y publicar. La recuperación
    # de imágenes puede resolver un enlace Google News hacia una URL ya existente.
    from scripts.dedupe_history import deduplicate
    before_dedupe = len(stories)
    stories = deduplicate(stories)
    if len(stories) != before_dedupe:
        print(f"URLs repetidas consolidadas antes de publicar: {before_dedupe - len(stories)}")
    from scripts.editorial_signals import update_archive
    archive = update_archive(archive, stories, now)
    signals_started = signals_started or to_iso(now)
    save_history(args.historial, stories, now, archive, signals_started)
    agenda = []
    if not args.solo_render and not args.importar:
        # Eventos ya validados por eventos-biobio (Biobío y resto de Chile); un fallo solo oculta la sección.
        from scripts.agenda import load_agenda
        agenda = load_agenda(now)
    build_site(stories, now, args.salida, args.ventana,
               signals_archive=archive, signals_started=signals_started, agenda=agenda)


if __name__ == "__main__":
    main()

