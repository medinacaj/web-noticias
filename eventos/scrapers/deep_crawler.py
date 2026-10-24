"""Rastreo acotado (BFS) dentro del sitio de una fuente."""
from urllib.parse import urlparse

import metadata
from scrapers import calendar_feeds, generic_events, ticketing
from scrapers.common import absolute_links, fetch, looks_like_event_url, same_site
from scrapers.sitemap import event_urls_from_sitemap

PARSERS = {"generic": generic_events.extract, "ticketing": ticketing.extract}
CANDIDATE_HINTS = ("teatro", "cultura", "centro-cultural", "ticket", "entradas", "festival",
                   "agenda", "eventos", "museo", "biblioteca", "camara", "emprend")


class CrawlResult:
    def __init__(self):
        self.pages = 0
        self.events = []
        self.possibles = []
        self.candidates = []
        self.http_status = None
        self.error = None
        self.resolved_url = None  # dominio confirmado entre url_candidates
        self.feeds = []


def _is_own_site(page, source):
    """Un dominio candidato vale solo si la página se presenta como esa municipalidad."""
    text = metadata.strip_accents(page.text or "").lower()
    commune = metadata.strip_accents(source.get("commune") or "").lower()
    return bool(commune) and commune in text and ("municipalidad" in text or "municipio" in text)


def resolve_start(source, fetcher, timeout):
    """Prueba url_candidates (dominios no confirmados) y devuelve (url, página) o (None, último fallo)."""
    last = None
    for url in [source["url"]] + [u for u in source.get("url_candidates") or [] if u != source["url"]]:
        page = fetcher(url, timeout=timeout)
        if page.ok and _is_own_site(page, source):
            return url, page
        last = page
    return None, last


def crawl(source, communes, fetcher=fetch, ref=None):
    res = CrawlResult()
    parser = PARSERS.get(source.get("parser") or "generic", generic_events.extract)
    start = source["url"]
    timeout = int(source.get("timeout") or 20)
    first = None
    if source.get("url_candidates"):
        start, first = resolve_start(source, fetcher, timeout)
        if not start:
            res.http_status = first.status if first else None
            res.error = ("Ningún dominio candidato se identificó como sitio de la Municipalidad de %s"
                         % source.get("commune"))
            return res
        res.resolved_url = start
    max_pages = int(source.get("max_pages") or 10) if source.get("deep_crawl") else 1
    max_depth = int(source.get("max_depth") or 1) if source.get("deep_crawl") else 0
    queue, seen = [(start, 0)], {start}
    if source.get("deep_crawl"):
        for u in event_urls_from_sitemap(start, fetcher=fetcher, limit=max_pages, timeout=timeout):
            if u not in seen and same_site(u, start):
                queue.append((u, 1))
                seen.add(u)
    while queue and res.pages < max_pages:
        url, depth = queue.pop(0)
        page = first if url == start and first is not None else fetcher(url, timeout=timeout)
        if url == start:
            res.http_status = page.status
            if not page.ok:
                res.error = page.error or "HTTP %s" % page.status
                return res
            found, res.feeds = calendar_feeds.collect(source, page.text, page.final_url, communes,
                                                      fetcher, timeout, ref)
            res.events += found
        if not page.ok:
            continue
        res.pages += 1
        ev, pe = parser(page.text, page.final_url, source, communes, ref)
        res.events += ev
        res.possibles += pe
        for link, text in absolute_links(page.text, page.final_url):
            if same_site(link, start):
                if depth < max_depth and link not in seen and looks_like_event_url(link, text):
                    seen.add(link)
                    queue.append((link, depth + 1))
            else:
                host = urlparse(link).netloc.lower()
                low = (link + " " + text).lower()
                if host.endswith(".cl") and any(h in low for h in CANDIDATE_HINTS):
                    res.candidates.append((link, host, url, "Enlace externo con pinta de agenda/eventos"))
    return res
