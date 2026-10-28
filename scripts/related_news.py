"""Amplía grupos internacionales del RSS; referencias, sin nuevas noticias o cifras."""
from collections import Counter
from datetime import timedelta
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError

from scripts.article_images import permitted_url
from scripts.dedupe_history import canonical_key
from scripts.latam import catalog_allowed, explicit_date
from scripts.satire import is_satire
from scripts.source_diversity import publisher_key

MAX_SEARCHES = 2
MAX_RELATED = 10
_STOP = set(('de del la las los el un una unos unas en con por para que como este esta estos estas '
             'al mas menos tras sobre ante desde hasta nuevo nueva nuevos nuevas hay deja dejan '
             'dos tres hoy vivo ultima ultimo hora personas muertos muertas heridos heridas '
             'fallecidos decenas cifra ano anos grave reporta reportan provoca').split())


def _google_article(url):
    try:
        p = urlsplit(url)
        return (p.scheme == 'https' and p.hostname == 'news.google.com'
                and not p.username and not p.password and p.port in (None, 443)
                and re.fullmatch(r'/(?:rss/)?articles/[A-Za-z0-9_-]+', p.path) is not None
                and not any(char.isspace() or ord(char) < 32 or char == '\\' for char in url))
    except (TypeError, ValueError):
        return False


class _Cluster(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.field = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            self.row = {'title': '', 'source': ''}
        elif self.row is not None:
            if tag == 'a' and _google_article(dict(attrs).get('href', '')):
                self.field = 'title'
            elif tag == 'font':
                self.field = 'source'

    def handle_data(self, data):
        if self.row is not None and self.field:
            self.row[self.field] += data[:500]

    def handle_endtag(self, tag):
        if tag in ('a', 'font'):
            self.field = None
        elif tag == 'li' and self.row is not None:
            if all(value.strip() for value in self.row.values()) and len(self.rows) < 10:
                self.rows.append({key: value.strip()[:300] for key, value in self.row.items()})
            self.row, self.field = None, None


def cluster_entries(description):
    parser = _Cluster()
    parser.feed(str(description or '')[:30000])
    return parser.rows


def _fold(word):
    return ''.join(c for c in unicodedata.normalize('NFKD', word.casefold())
                   if not unicodedata.combining(c))


def _words(title):
    return {word for word in re.findall(r'[^\W\d_]+', _fold(title))
            if len(word) >= 3 and word not in _STOP}


def _topic(rows):
    if len({publisher_key(row) for row in rows}) < 3:
        return None
    counts = Counter(word for row in rows for word in _words(row['title']))
    common = {word for word, count in counts.items() if count >= 2}
    ranked = sorted(common, key=lambda word: (-counts[word], -len(word), word))
    if len(ranked) < 2:
        return None
    proper = Counter()
    for row in rows:
        tokens = re.findall(r'[^\W\d_]+', row['title'])
        proper.update({_fold(word) for word in tokens[1:] if word.istitle()})
    anchor = next((word for word in ranked if proper[word] >= 2
                   and counts[word] >= (len(rows) + 1) // 2), None)
    if anchor:
        terms = [word for word in ranked if word != anchor][:3]
        query = anchor + ' (' + ' OR '.join(terms) + ')'
    else:
        query = ' '.join(ranked[:3])
    return query + ' when:1d', common, anchor


def _catalog():
    from scripts.regional_sources import load_catalog
    from scripts.global_sources import load_catalog as load_world_catalog
    return load_catalog() + load_world_catalog()


def _source_key(item):
    source = item.get('source')
    sources = item.get('sources')
    if not isinstance(source, str):
        source = sources[0] if isinstance(sources, list) and sources else ''
    return publisher_key({'source': source})


def _relevant(title, common, anchor):
    words = _words(title)
    return (not anchor or anchor in words) and len(words & common) >= min(3, len(common))


def _record(item, now, catalog):
    title, source = item.get('title'), item.get('source')
    sources = item.get('sources')
    if not source and isinstance(sources, list) and sources:
        source = sources[0]
    link, source_url = item.get('link'), item.get('source_url')
    published = explicit_date(item.get('published'))
    if (not isinstance(title, str) or not title.strip() or len(title) > 500
            or not isinstance(source, str) or not source.strip() or len(source) > 150
            or not isinstance(source_url, str) or not isinstance(link, str)
            or any(char.isspace() or ord(char) < 32 or char == '\\' for char in source_url + link)
            or not permitted_url(source_url, check_dns=False) or published is None
            or (now is not None and not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15))
            or is_satire({'source': source, 'source_url': source_url, 'link': link})
            or not catalog_allowed({'source': source, 'source_url': source_url, 'link': link}, catalog)):
        return None
    if not _google_article(link):
        if not permitted_url(link, check_dns=False):
            return None
        source_host = urlsplit(source_url).hostname.removeprefix('www.')
        link_host = urlsplit(link).hostname.removeprefix('www.')
        if link_host != source_host and not link_host.endswith('.' + source_host):
            return None
    return {'title': title.strip(), 'source': source.strip(), 'source_url': source_url,
            'link': link, 'published': published.strftime('%Y-%m-%dT%H:%M:%SZ')}


def combine_related(current, incoming, now=None, catalog=None):
    rows = (current[:60] if isinstance(current, list) else []) + (incoming[:60] if isinstance(incoming, list) else [])
    if not rows:
        return []
    catalog = _catalog() if catalog is None else catalog
    publications = {}
    for item in rows:
        row = _record(item, None, catalog) if isinstance(item, dict) else None
        if row is None:
            continue
        key = canonical_key(row['link'])
        if key in publications:
            publications[key]['published'] = min(publications[key]['published'], row['published'])
        else:
            publications[key] = row
    result, seen_editors = [], set()
    for row in publications.values():
        editor = publisher_key(row)
        if editor in seen_editors or _record(row, now, catalog) is None:
            continue
        seen_editors.add(editor)
        result.append(row)
        if len(result) == MAX_RELATED:
            break
    return result


def enrich_coverages(items, now, *, fetch, catalog, history=()):
    """Hasta dos búsquedas derivadas del RSS; no consulta páginas de editores."""
    result = [dict(item) for item in items]
    candidates = []
    for item in result:
        published = explicit_date(item.get('published'))
        rows = item.get('_coverage_cluster') or []
        if (item.get('category') != 'internacional' or not published or is_satire(item)
                or not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15)
                or not rows):
            continue
        allowed = catalog_allowed(item, catalog)
        if not allowed:
            rows = [row for row in rows if _source_key(row) != _source_key(item)]
        topic = _topic(rows)
        if topic:
            target = item
            if not allowed:
                # El grupo de Google no otorga permiso para usar a su editor principal.
                # Adjuntar solo a una publicación permitida que ya llegó por otra vía.
                _, common, anchor = topic
                members = {_source_key(row) for row in rows}
                anchors = [entry for entry in result + list(history)
                           if entry.get('category') == 'internacional'
                           and _source_key(entry) in members and not is_satire(entry)
                           and catalog_allowed(entry, catalog)
                           and (date := explicit_date(entry.get('published'))) is not None
                           and now - timedelta(hours=24) <= date <= now + timedelta(minutes=15)
                           and (_google_article(entry.get('link'))
                                or permitted_url(entry.get('link'), check_dns=False))
                           and _relevant(entry.get('title') or '', common, anchor)]
                if not anchors:
                    continue
                target = max(anchors, key=lambda entry: explicit_date(entry['published']))
                if not any(target is entry for entry in result):
                    target = dict(target)
                    result.append(target)
            candidates.append((published, target, rows, topic))
    searched = set()
    for _, item, rows, (query, common, anchor) in sorted(candidates, key=lambda row: row[0], reverse=True):
        if query in searched:
            continue
        if len(searched) == MAX_SEARCHES:
            break
        searched.add(query)
        url = 'https://news.google.com/rss/search?' + urlencode(
            {'q': query, 'hl': 'es-419', 'gl': 'CL', 'ceid': 'CL:es-419'})
        try:
            found = []
            primary = {publisher_key(item), _source_key(item)}
            cluster_editors = {publisher_key(row) for row in rows}
            cluster_names = {_fold(row['source']) for row in rows}
            for raw in fetch(url, 'internacional', metadata_only=True, limit=60):
                row = _record(raw, now, catalog)
                if row is None or publisher_key(row) in primary or _source_key(row) in primary:
                    continue
                if not _relevant(row['title'], common, anchor):
                    continue
                found.append(row)
            found.sort(key=lambda row: publisher_key(row) not in cluster_editors
                       and _fold(row['source']) not in cluster_names)
            related = combine_related(item.get('related_coverages'), found, now, catalog)
            if related:
                item['related_coverages'] = related
        except (OSError, ValueError, TypeError, LookupError, ParseError) as error:
            print(f'[aviso] Coberturas relacionadas no disponibles: {error}')
    return result


def display_coverages(story, direct, now=None):
    """Filas y presencia de referencias válidas; no modifica fuentes ni feeds."""
    related = combine_related([], story.get('related_coverages'), now)
    primary = {publisher_key(story), _source_key(story)}
    related = [row for row in related if publisher_key(row) not in primary
               and _source_key(row) not in primary]
    if not related:
        return direct, False
    result, names, links = [], set(), set()
    for row in direct + related:
        name = row['source'].casefold()
        if name in names or row['link'] in links:
            continue
        names.add(name)
        links.add(row['link'])
        result.append(row)
    return result[:12], True
