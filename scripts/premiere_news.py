"""Noticias sobre obras concretas; el RSS no acredita fecha de estreno en Chile."""
from datetime import timedelta
from itertools import islice
import re
import unicodedata
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError

from scripts.dedupe_history import canonical_key
from scripts.global_sources import matches_world_source
from scripts.latam import catalog_allowed, explicit_date
from scripts.weekly_releases import SOURCES

MAX_ITEMS = 8
MAX_PER_SOURCE = 2
MAX_AGE = timedelta(days=7)


def _restrictions():
    from scripts.global_sources import load_catalog as world
    from scripts.regional_sources import load_catalog as regional
    return world() + regional()


def _individual_title(title):
    folded = ''.join(c for c in unicodedata.normalize('NFKD', title.casefold())
                     if not unicodedata.combining(c))
    # Se conserva el titular original; no se extrae una ficha de película.
    names = re.findall(r'''['"«“‘]([^'"»”’]{2,130})['"»”’]''', folded)
    generic = {'streaming','cine','cines','pelicula','peliculas','serie','series','documental',
               'netflix','disney+','hbo','max','prime video','apple tv','mubi','trailer','estreno'}
    if not any(name.strip() not in generic and any(c.isalpha() for c in name) for name in names):
        return False
    if (re.search(r'\b(que ver|mejores|ranking|rankings|top\s*\d+|disco|album|concierto|cantante)\b', folded)
            or re.match(r'^(?:los\s+|las\s+)?estrenos\b', folded)):
        return False
    screen = re.search(r'\b(pelicula|serie|documental|temporada|anime|cines?|netflix|prime video|disney|hbo|apple tv|mubi)\b', folded)
    if not screen:
        return False
    if re.search(r'\b(videojuego|ps5|xbox|playstation)\b', folded) and not re.search(r'\b(pelicula|serie|documental)\b', folded):
        return False
    return bool(re.search(
        r'\b(fecha (?:de )?estreno|se estrena(?:ra|n)?|se estreno|estrenara|'
        r'estrena(?:n)? (?:este|el|hoy|manana)|estreno (?:en|de)|llega(?:ra|n)? (?:a|al)|'
        r'(?:presenta|revela|lanza|publica|estrena) .{0,50}trailer)\b', folded))


def _prepare(item, now, restrictions):
    if not isinstance(item, dict):
        return None
    title, source = item.get('title'), item.get('source')
    published = explicit_date(item.get('published'))
    if (not isinstance(title, str) or not title.strip() or len(title) > 500
            or not isinstance(source, str) or not source.strip() or len(source) > 200
            or published is None or not now - MAX_AGE <= published <= now + timedelta(minutes=15)
            or not _individual_title(title)):
        return None
    try:
        host = (urlsplit(item.get('source_url')).hostname or '').lower().removeprefix('www.')
    except (TypeError, ValueError, AttributeError):
        return None
    identity = next((s for s in SOURCES if s[0] == host), None)
    if (not identity or not matches_world_source(item, {'domain': host})
            or not catalog_allowed(item, restrictions)):
        return None
    from fetch_noticias import to_iso
    return {'title': title.strip(), 'source': source.strip(), 'source_url': item['source_url'],
            'link': item['link'], 'published': to_iso(published), 'source_country_label': 'Medio de ' + identity[1],
            'content_kind': 'premiere-news', 'metadata_only': True, 'summary': '', 'image': ''}


def current_news(items, now, restrictions=None):
    """Revalidación local, límite de ocho noticias y dos por editor."""
    restrictions = _restrictions() if restrictions is None else restrictions
    valid = []
    for item in islice(items or [], 120):
        record = _prepare(item, now, restrictions)
        if record:
            valid.append(record)
    valid.sort(key=lambda s: s['published'], reverse=True)
    result, seen, per_source = [], set(), {}
    for record in valid:
        host = (urlsplit(record['source_url']).hostname or '').lower().removeprefix('www.')
        key = canonical_key(record['link'])
        if key in seen or per_source.get(host, 0) >= MAX_PER_SOURCE:
            continue
        seen.add(key)
        per_source[host] = per_source.get(host, 0) + 1
        result.append(record)
        if len(result) == MAX_ITEMS:
            break
    return result


def collect_news(now, fetch=None, restrictions=None):
    """Tres consultas al RSS existente; nunca solicita los artículos o sus fotos."""
    if fetch is None:
        from fetch_noticias import fetch_rss
        fetch = fetch_rss
    restrictions = _restrictions() if restrictions is None else restrictions
    sources = [s for s in SOURCES if catalog_allowed(
        {'source_url': 'https://' + s[0], 'link': 'https://' + s[0]}, restrictions)]
    groups = ([s for s in sources if s[2] == 'Cine'],
              [s for s in sources if s[2] == 'Streaming' and s[1] != 'España'],
              [s for s in sources if s[2] == 'Streaming' and s[1] == 'España'])
    found = []
    for group in groups:
        if not group:
            continue
        domains = {s[0] for s in group}
        query = '(' + ' OR '.join('site:' + s[0] for s in group) + ') '
        query += '("fecha de estreno" OR "se estrena" OR "primer tráiler" OR "llega a") '
        query += f'after:{(now - MAX_AGE - timedelta(days=1)).date().isoformat()} before:{(now + timedelta(days=1)).date().isoformat()}'
        url = 'https://news.google.com/rss/search?' + urlencode({'q': query, 'hl': 'es-419', 'gl': 'CL', 'ceid': 'CL:es-419'})
        try:
            for item in islice(fetch(url, 'cultura', metadata_only=True, limit=40) or [], 40):
                record = _prepare(item, now, restrictions)
                if record and (urlsplit(record['source_url']).hostname or '').lower().removeprefix('www.') in domains:
                    found.append(record)
        except (OSError, ValueError, TypeError, LookupError, ParseError) as error:
            print(f'[aviso] Noticias de estrenos no disponibles: {type(error).__name__}')
    result = current_news(found, now, restrictions)
    if result:
        print(f'Noticias individuales de estrenos: {len(result)} referencias')
    return result
