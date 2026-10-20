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
MAX_HISTORY = 400            # tope de noticias guardadas en el historial
SIMILARITY_THRESHOLD = 0.6   # umbral para considerar dos titulares "la misma noticia"
RSS_LIMIT = 15

GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "").strip()
GNEWS_EVERY_HOURS = 3        # 6 categorías x 8 corridas/día = 48 solicitudes (límite gratis: 100)

SITE_NAME = "Noticias del Momento"
SITE_TITLE = "Noticias del Momento — Últimas noticias de Chile y el mundo hoy"
SITE_DESCRIPTION = (
    "Las noticias más relevantes de Chile y el mundo, actualizadas cada hora: nacional, "
    "internacional, economía, tecnología, deportes y cultura, con enlace a cada fuente."
)

GOOGLE_RSS = "https://news.google.com/rss/headlines/section/topic/{topic}?hl=es-419&gl=CL&ceid=CL:es-419"

CATEGORIES = [
    {"key": "nacional",      "label": "Nacional",                  "google_topic": "NATION",        "gnews": "nation"},
    {"key": "internacional", "label": "Internacional",             "google_topic": "WORLD",         "gnews": "world"},
    {"key": "economia",      "label": "Economía y negocios",       "google_topic": "BUSINESS",      "gnews": "business",      "short": "Economía"},
    {"key": "tecnologia",    "label": "Tecnología",                "google_topic": "TECHNOLOGY",    "gnews": "technology"},
    {"key": "deportes",      "label": "Deportes",                  "google_topic": "SPORTS",        "gnews": "sports"},
    {"key": "cultura",       "label": "Cultura y entretenimiento", "google_topic": "ENTERTAINMENT", "gnews": "entertainment", "short": "Cultura"},
    {"key": "regiones", "label": "Regiones", "google_query": "(Biobío OR Ñuble OR Concepción OR Valparaíso OR Antofagasta OR Araucanía) noticias Chile"},
    {"key": "politica", "label": "Política", "google_query": "(Gobierno OR Congreso OR Senado OR política) Chile"},
    {"key": "medioambiente", "label": "Medioambiente y clima", "google_query": "(medioambiente OR cambio climático OR meteorología OR clima) Chile", "short": "Clima"},
    {"key": "salud-ciencia", "label": "Salud y ciencia", "google_query": "(salud pública OR medicina OR ciencia OR investigación) Chile", "short": "Salud y ciencia"},
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
        parsed = urllib.parse.urlsplit((value or "").strip())
        host = (parsed.hostname or "").lower().rstrip(".")
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


def fetch_rss(url, category, default_source=None):
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
        published = parse_date(node.findtext("pubDate"))
        items.append({
            "category": category,
            "title": title,
            "source": source or "Fuente",
            "source_url": (source_node.get("url") or "").strip() if source_node is not None else (url if default_source else ""),
            "link": (node.findtext("link") or "").strip(),
            "published": to_iso(published) if published else None,
            "summary": clean_summary(title, node.findtext("description")),
            "image": rss_image(node),
        })
    return items


def fetch_gnews(cat):
    params = {"category": cat["gnews"], "lang": "es", "country": "cl", "max": "10", "apikey": GNEWS_API_KEY}
    data = json.loads(http_get("https://gnews.io/api/v4/top-headlines?" + urllib.parse.urlencode(params)))
    items = []
    for article in data.get("articles", []):
        title = (article.get("title") or "").strip()
        published = parse_date(article.get("publishedAt"))
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
    items = []
    for cat in CATEGORIES:
        key, count = cat["key"], 0
        try:
            got = fetch_rss(category_google_url(cat), key)
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
    return items


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
    for story in stories:
        story["_norm"] = normalize_title(story.get("title", ""))
    return stories


def save_history(path, stories, now):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    clean = [{k: v for k, v in s.items() if not k.startswith("_")} for s in stories]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"actualizado": to_iso(now), "noticias": clean}, handle, ensure_ascii=False, indent=1)


def merge(stories, items, now):
    """Agrega noticias nuevas; si un titular ya existe (aunque venga de otro medio),
    suma la fuente a la noticia existente en vez de duplicarla."""
    added = 0
    for item in items:
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        if not title or not link or item.get("category") not in CATEGORY_LABELS:
            continue
        norm = normalize_title(title)
        incoming_sources = item.get("sources") or [item.get("source") or "Fuente"]
        published = parse_date(item.get("published"))
        published = to_iso(published) if published else None
        match = next((s for s in stories if is_similar(norm, s["_norm"])), None)
        if match:
            for source in incoming_sources:
                if source and source not in match["sources"]:
                    match["sources"].append(source)
            if is_google_link(match["link"]) and not is_google_link(link):
                match["link"] = link  # preferir el enlace directo al medio
            if not match.get("summary") and item.get("summary"):
                match["summary"] = item["summary"]
            if (not source_domain(match.get("source_url"), match.get("link"))
                    and source_domain(item.get("source_url"), link)):
                match["source_url"] = item.get("source_url") or link
            if not match.get("image") and item.get("image"):
                match["image"] = safe_image(item["image"])
            if published and (not match.get("published") or published < match["published"]):
                match["published"] = published
        else:
            stories.append({
                "category": item["category"],
                "title": title,
                "summary": item.get("summary") or "",
                "image": safe_image(item.get("image")),
                "source_url": item.get("source_url") or (link if not is_google_link(link) else ""),
                "sources": [s for s in incoming_sources if s],
                "link": link,
                "published": published,
                "first_seen": to_iso(now),
                "_norm": norm,
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
    kept = [s for s in stories if (story_time(s) or now) >= limit]
    kept.sort(key=lambda s: story_time(s) or now, reverse=True)
    return kept[:MAX_HISTORY]


# ---------- SELECCIÓN ----------

def score(story, now):
    # más medios que la reportan = más relevante; pierde un punto cada 6 horas
    return len(story["sources"]) - hours_old(story, now) / 6


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
    secondary = []
    for story in rest:
        if len(secondary) == 3:
            break
        if remaining[story["category"]] >= 2:
            secondary.append(story)
            remaining[story["category"]] -= 1
    used = {id(s) for s in secondary}
    by_category = {}
    for cat in CATEGORIES:
        chosen = [s for s in rest if s["category"] == cat["key"] and id(s) not in used][:STORIES_PER_CATEGORY]
        if chosen:
            by_category[cat["key"]] = chosen
    counts = {}
    for story in stories:
        counts[story["category"]] = counts.get(story["category"], 0) + 1
    return {
        "lead": lead,
        "secondary": secondary,
        "by_category": by_category,
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
    return (f'<a href="{esc(story["link"])}" target="_blank" rel="noopener" '
            f'data-cat="{esc(category_label(story))}" data-key="{story["category"]}">{esc(story["title"])}</a>')


def figure_html(story, eager=False):
    image = safe_image(story.get("image"))
    if not image:
        source = (story.get("sources") or ["Fuente"])[0]
        return (f'<figure class="media media--source" role="img" '
                f'aria-label="Medio de origen: {esc(source)}">'
                f'<span class="source-visual">{source_mark(story)}'
                f'<span class="source-visual-name">{esc(source)}</span></span>'
                f'</figure>')
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<figure class="media"><img src="{esc(image)}" alt="" width="1200" height="675" '
            f'{loading} decoding="async" referrerpolicy="no-referrer">'
            f'<span class="media-badge" aria-hidden="true">{source_mark(story)}</span></figure>')


def meta_html(story, now, read_link=False):
    sources = story["sources"]
    label = ", ".join(sources[:3]) + (f" y {len(sources) - 3} más" if len(sources) > 3 else "")
    moment = story_time(story) or now
    read = (f'<a class="read" href="{esc(story["link"])}" target="_blank" rel="noopener">Ver noticia completa</a>'
            if read_link else "")
    return (f'<p class="meta"><span class="src">{source_mark(story)}<span class="source-name">{esc(label)}</span></span>'
            f'<time datetime="{to_iso(moment)}">{time_ago(story, now)}</time>{read}</p>')


def dek_html(story):
    return f'<p class="dek">{esc(story["summary"])}</p>' if story.get("summary") else ""


def render_breaking(sel, now):
    story = sel["most_recent"]
    if not story:
        return ""
    return (f'<div class="breaking"><div class="container breaking-inner">'
            f'<span class="breaking-label">Lo último</span>{title_link(story)}'
            f'<time datetime="{to_iso(story_time(story) or now)}">{time_ago(story, now)}</time></div></div>')


def render_top(sel, now):
    lead = sel["lead"]
    if not lead:
        return ""
    lead_html = (
        f'<article class="lead cat-{lead["category"]}" id="portada">{figure_html(lead, eager=True)}'
        f'<p class="kicker">Portada · {esc(category_label(lead))}</p>'
        f'<h2 class="lead-title">{title_link(lead)}</h2>{dek_html(lead)}{meta_html(lead, now, True)}</article>'
    )
    items = "".join(
        f'<li class="cat-{s["category"]}"><article class="rail-item"><p class="kicker">{esc(category_label(s))}</p>'
        f'<h3>{title_link(s)}</h3>{meta_html(s, now)}</article></li>'
        for s in sel["secondary"]
    )
    if not items:
        return f'<div class="top-grid top-grid--single">{lead_html}</div>'
    return (f'<div class="top-grid">{lead_html}<div class="top-aside">'
            f'<h2 class="rail-title">Destacadas</h2><ol class="rail-list">{items}</ol></div></div>')


def render_context(sel, now, window_hours):
    units = []
    reported = sel["most_reported"]
    if reported:
        n = len(reported["sources"])
        units.append(("Lo más cubierto", title_link(reported),
                      f"{n} medio lo reporta" if n == 1 else f"{n} medios lo reportan"))
    if sel["busiest"]:
        key, count = sel["busiest"]
        units.append(("Sección más activa",
                      f'<a class="cat-{key}" href="#cat-{key}">{esc(CATEGORY_LABELS[key])}</a>',
                      f"{count} noticia publicada" if count == 1 else f"{count} noticias publicadas"))
    period = f"en las últimas {int(window_hours)} horas" if window_hours <= 48 else "en el período publicado"
    units.append(("Cobertura", f'{sel["total"]} noticias de {sel["outlets"]} medios',
                  f"Recopiladas {period}; se actualiza cada hora"))
    cells = "".join(
        f'<div class="context-unit"><p class="context-label"><span class="context-num">{i:02d}</span>'
        f'{esc(label)}</p><p class="context-text">{text}</p><p class="context-note">{esc(note)}</p></div>'
        for i, (label, text, note) in enumerate(units, start=1)
    )
    return f'<section class="context" aria-label="Resumen del día">{cells}</section>'


def render_sections(by_category, now):
    blocks = []
    present = [c for c in CATEGORIES if c["key"] in by_category]
    for number, cat in enumerate(present, start=1):
        stories = by_category[cat["key"]]
        feature, rest = stories[0], stories[1:]
        feature_html = (f'<article class="feature">{figure_html(feature)}'
                        f'<div class="news-body"><p class="kicker">{esc(cat["label"])}</p>'
                        f'<h3 class="feature-title">{title_link(feature)}</h3>'
                        f'{dek_html(feature)}{meta_html(feature, now, True)}</div></article>')
        compact = "".join(
            f'<li{" data-extra" if i >= 5 else ""}><article class="compact">{figure_html(s)}'
            f'<div class="news-body"><p class="kicker">{esc(cat["label"])}</p>'
            f'<h3>{title_link(s)}</h3>{meta_html(s, now)}</div></article></li>'
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
            f'<h2 id="titulo-{cat["key"]}">{esc(cat["label"])}</h2>'
            f'<span class="section-count">{count} {"noticia" if count == 1 else "noticias"}</span></div>'
            f'<div class="{grid_class}" id="noticias-{esc(cat["key"])}">{feature_html}{compact_html}</div>'
            f'{more}</section>'
        )
    return "\n".join(blocks)


def render_nav(sel):
    links = ['<li><a href="#portada">Portada</a></li>'] if sel["lead"] else []
    links += [f'<li><a class="cat-{c["key"]}" href="#cat-{c["key"]}">{esc(c.get("short", c["label"]))}</a></li>'
              for c in CATEGORIES if c["key"] in sel["by_category"]]
    return "".join(links)


def build_jsonld(sel, now):
    page_url = SITE_URL + "/"
    ordered = ([sel["lead"]] if sel["lead"] else []) + sel["secondary"] + \
        [s for k in sel["by_category"] for s in sel["by_category"][k]]
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


def build_site(stories, now, out_dir, window_hours=WINDOW_HOURS):
    sel = select(stories, now)
    with open(TEMPLATE_PATH, encoding="utf-8") as handle:
        page = handle.read()

    gsc_code = os.environ.get("GSC_VERIFICATION", "").strip()
    nav = render_nav(sel)
    replacements = {
        "%%TITLE%%": esc(SITE_TITLE),
        "%%DESCRIPTION%%": esc(SITE_DESCRIPTION),
        "%%SITE_NAME%%": esc(SITE_NAME),
        "%%CANONICAL%%": esc(SITE_URL + "/"),
        "%%OG_IMAGE%%": esc(SITE_URL + "/og-image.png"),
        "%%GSC_META%%": f'<meta name="google-site-verification" content="{esc(gsc_code)}">' if gsc_code else "",
        "%%JSONLD%%": build_jsonld(sel, now),
        "%%UPDATED_ISO%%": to_iso(now),
        "%%UPDATED_HUMAN%%": human_datetime(now),
        "%%YEAR%%": str(now.astimezone(TZ_CHILE).year),
        "%%NAV%%": nav,
        "%%FOOTER_NAV%%": nav,
        "%%BREAKING%%": render_breaking(sel, now),
        "%%TOP%%": render_top(sel, now),
        "%%CONTEXT%%": render_context(sel, now, window_hours),
        "%%SECTIONS%%": render_sections(sel["by_category"], now),
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    leftover = re.findall(r"%%[A-Z_]+%%", page)
    if leftover:
        raise SystemExit(f"ERROR: la plantilla quedó con marcadores sin reemplazar: {leftover}")

    os.makedirs(out_dir, exist_ok=True)
    if os.path.isdir(STATIC_DIR):
        shutil.copytree(STATIC_DIR, out_dir, dirs_exist_ok=True)

    files = {
        "index.html": page,
        "404.html": PAGE_404.replace("%%HOME%%", esc(SITE_URL + "/")),
        "robots.txt": f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",
        "sitemap.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url>\n    <loc>{esc(SITE_URL)}/</loc>\n    <lastmod>{to_iso(now)}</lastmod>\n  </url>\n"
            "</urlset>\n"
        ),
    }
    for name, content in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(content)

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
    stories = load_history(args.historial)
    print(f"Historial: {len(stories)} noticias previas")

    if args.importar:
        with open(args.importar, encoding="utf-8") as handle:
            items = json.load(handle)
        print(f"Importadas: {merge(stories, items, now)} noticias nuevas")
    elif not args.solo_render:
        items = collect(now)
        if not items:
            print("[aviso] Ninguna fuente respondió; se publica con el historial existente.")
        print(f"Nuevas: {merge(stories, items, now)} (el resto ya estaba publicado y solo sumó fuentes)")

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

    save_history(args.historial, stories, now)
    build_site(stories, now, args.salida, args.ventana)


if __name__ == "__main__":
    main()
