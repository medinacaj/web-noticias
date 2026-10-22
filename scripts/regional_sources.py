"""RSS regional opt-in: solo titulares, enlaces y atribución del editor.

La disponibilidad de un feed y la revisión de sus condiciones son estados
separados. Ninguna fuente pendiente se consulta automáticamente.
"""
from datetime import timedelta
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


CATALOG = Path(__file__).resolve().parents[1] / "config" / "regional_sources.json"
MAX_FEEDS = 16
MAX_ITEMS = 4
MAX_FEED_BYTES = 450_000


def fetch_feed(url):
    """Respuesta acotada y redirecciones públicas, sin consultar artículos."""
    from urllib.request import Request, build_opener
    from scripts.article_images import permitted_url, SafeRedirects
    if not permitted_url(url):
        raise ValueError("El feed no es una URL HTTPS pública")
    request = Request(url, headers={"User-Agent": "NoticiasDelMomento/2.0",
                                   "Accept": "application/rss+xml,application/xml,text/xml"})
    with build_opener(SafeRedirects).open(request, timeout=8) as response:
        if not permitted_url(response.geturl()):
            raise ValueError("El feed redirigió a un destino no público")
        if "xml" not in (response.headers.get("Content-Type") or "").lower():
            raise ValueError("El feed no entregó XML")
        return response.read(MAX_FEED_BYTES + 1)


def load_catalog(path=CATALOG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["sources"]


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "").casefold())
                   if not unicodedata.combining(c))


def _editorial_url(url, domain, *, article=False):
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower().rstrip(".")
        return (p.scheme == "https" and not p.username and not p.password
                and p.port in (None, 443) and bool(domain)
                and (host == domain or host.endswith("." + domain))
                and (not article or p.path.strip("/")))
    except (ValueError, TypeError):
        return False


def _news_category(labels):
    text = " ".join(_fold(label) for label in labels)
    for category, words in (
        ("economia", ("economia", "economy", "negocios", "mercado", "finanzas")),
        ("salud-ciencia", ("salud", "ciencia", "saude", "medicina")),
        ("tecnologia", ("tecnologia", "technology")),
        ("deportes", ("deportes", "esportes", "sports")),
        ("cultura", ("cultura", "entretenimiento", "cultural")),
        ("medioambiente", ("medioambiente", "ambiente", "clima")),
    ):
        if any(word in text for word in words):
            return category
    # Política, Nacional y Regiones de otro país no pertenecen a las secciones chilenas.
    return "internacional"


def parse_feed(raw, source, now):
    """No interpreta descripciones ni imágenes; conserva el titular original."""
    from fetch_noticias import parse_date, to_iso
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if (len(raw) > MAX_FEED_BYTES or b"<!DOCTYPE" in raw.upper()
            or b"<!ENTITY" in raw.upper()):
        return []
    root = ET.fromstring(raw)
    result, seen = [], set()
    for node in root.findall(".//item")[:60]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        published = parse_date(node.findtext("pubDate"))
        labels = [el.text or "" for el in node.findall("category")]
        path = _fold(urlsplit(link).path) if _editorial_url(link, source["domain"], article=True) else ""
        topics = " ".join(_fold(x) for x in labels) + " " + path
        if (not title or not path or not published
                or not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15)
                or re.search(r"\b(opinion|opiniao|editorial|columnistas?|publicidad|patrocinado|patrocinada|sponsored)\b", topics)):
            continue
        # URL completa: los parámetros semánticos también pueden identificar artículos.
        if link in seen:
            continue
        seen.add(link)
        result.append({
            "title": title, "link": link, "source": source["name"],
            "source_url": "https://" + source["domain"],
            "source_country": source["country"],
            "source_country_label": source["country_label"],
            "publisher_id": source["id"], "category": _news_category(labels),
            "published": to_iso(published), "summary": "", "image": "",
            "metadata_only": True,
        })
        if len(result) == MAX_ITEMS:
            break
    return result


def collect_regional(now, fetch=fetch_feed, catalog=None):
    result = []
    sources = load_catalog() if catalog is None else catalog
    active = [source for source in sources
              if source.get("enabled") is True
              and source.get("permission_status") == "approved"
              and source.get("technical_status") == "verified"
              and source.get("permission_evidence")
              and _editorial_url(source.get("feed_url"), source.get("domain"))]
    for source in active[:MAX_FEEDS]:
        try:
            result.extend(parse_feed(fetch(source["feed_url"]), source, now))
        except (OSError, ValueError, TypeError, ET.ParseError) as error:
            print(f"[aviso] RSS regional {source['name']} no disponible: {error}")
    return result
