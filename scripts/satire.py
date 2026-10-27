"""Enlaces de humor separados de la ingesta y del historial de noticias.

La identidad de El Chigüire Bipolar identifica sátira, no hechos verificados.
Google RSS aporta solo metadatos; su disponibilidad no acredita una licencia.
"""
from datetime import timedelta
from html import escape
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError

from scripts.dedupe_history import canonical_key
from scripts.latam import catalog_allowed, explicit_date

SOURCE_NAME = "El Chigüire Bipolar"
SOURCE_URL = "https://www.elchiguirebipolar.net/"
_HOSTS = {"elchiguirebipolar.net", "www.elchiguirebipolar.net"}


def _url(value):
    if (not isinstance(value, str) or "\\" in value
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.port not in (None, 443)):
            return None
        return parsed
    except ValueError:
        return None


def is_satire(story):
    """Identidad exacta por editor o dominio; no buscar palabras en el titular."""
    names = story.get("sources") or [story.get("source")]
    if isinstance(names, str):
        names = [names]
    if any(isinstance(name, str) and name.strip().casefold() == SOURCE_NAME.casefold()
           for name in names):
        return True
    for field in ("source_url", "link"):
        parsed = _url(story.get(field))
        if parsed and (parsed.hostname or "").lower().rstrip(".") in _HOSTS:
            return True
    return False


def _valid_link(link):
    parsed = _url(link)
    if not parsed:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in _HOSTS:
        return bool(parsed.path.strip("/"))
    return (host == "news.google.com"
            and parsed.path.startswith(("/rss/articles/", "/articles/"))
            and bool(parsed.path.rsplit("/", 1)[-1]))


def collect_satire(now, fetch=None):
    """Una consulta, hasta tres enlaces únicos y fecha explícita de últimas 24 h."""
    from scripts.global_sources import load_catalog as load_world_catalog
    from scripts.regional_sources import load_catalog as load_regional_catalog
    catalog = load_world_catalog() + load_regional_catalog()
    identity = {"source": SOURCE_NAME, "source_url": SOURCE_URL}
    if not catalog_allowed(identity, catalog):
        return []
    if fetch is None:
        from fetch_noticias import fetch_rss
        fetch = fetch_rss
    url = "https://news.google.com/rss/search?" + urlencode({
        "q": "site:elchiguirebipolar.net when:1d", "hl": "es-419",
        "gl": "VE", "ceid": "VE:es-419",
    })
    result, seen = [], set()
    try:
        for item in fetch(url, "satira", metadata_only=True):
            title, name = item.get("title"), item.get("source")
            source = _url(item.get("source_url"))
            published = explicit_date(item.get("published"))
            link = item.get("link")
            if (not isinstance(title, str) or not title.strip()
                    or not isinstance(name, str) or name.strip().casefold() != SOURCE_NAME.casefold()
                    or source is None or (source.hostname or "").lower().rstrip(".") not in _HOSTS
                    or published is None
                    or not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15)
                    or not _valid_link(link) or not catalog_allowed(item, catalog)):
                continue
            key = canonical_key(link)
            if key in seen:
                continue
            seen.add(key)
            result.append({"title": title, "source": SOURCE_NAME, "source_url": SOURCE_URL,
                           "link": link, "published": published.isoformat().replace("+00:00", "Z"),
                           "category": "satira", "metadata_only": True,
                           "summary": "", "image": ""})
            if len(result) == 3:
                break
    except (OSError, ValueError, TypeError, LookupError, ParseError) as error:
        print(f"[aviso] Sátira no disponible: {error}")
    return result


def render_satire(items=()):
    """Lista independiente sin atributos de tarjetas ni inclusión en noticias."""
    links = []
    for item in items:
        title, link = item.get("title"), item.get("link")
        if isinstance(title, str) and title.strip() and _valid_link(link) and is_satire(item):
            links.append(f'<li><a href="{escape(link, quote=True)}" rel="noopener">'
                         f'{escape(title)}</a></li>')
        if len(links) == 3:
            break
    listing = '<ul>' + "".join(links) + '</ul>' if links else ""
    return ('<aside class="satire-links" aria-label="Sátira y humor">'
            '<h3>Sátira y humor</h3><p>El Chigüire Bipolar publica humor y ficción satírica. '
            'Estos enlaces no describen hechos verificados.</p>' + listing +
            f'<a href="{SOURCE_URL}" rel="noopener">El Chigüire Bipolar · Sátira</a></aside>')
