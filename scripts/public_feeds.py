"""RSS del portal: índice y categorías originales con atribución editorial.
Solo serializa titulares, enlaces y fechas; no consulta páginas ni copia extractos.
"""
from datetime import timezone
from email.utils import format_datetime
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr


def _xml_text(value):
    """XML 1.0 admite tabuladores y saltos de línea, pero no controles ni sustitutos."""
    return isinstance(value, str) and all(
        char in "\t\n\r" or 0x20 <= ord(char) <= 0xD7FF
        or 0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF
        for char in value)


def _safe_link(value):
    try:
        if not _xml_text(str(value or "")):
            return ""
        p = urlsplit(str(value or ""))
        host = (p.hostname or "").lower().rstrip(".")
        if (p.scheme == "https" and p.hostname and not p.username and not p.password
                and p.port in (None, 443)
                and host != "news.google.com" and not host.endswith(".news.google.com")):
            return str(value)
    except (ValueError, TypeError):
        pass
    return ""


def _host(url):
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".").removeprefix("www.")
    except (ValueError, TypeError):
        return ""


def _publication(item):
    """Vincular titular y medio al enlace publicado, sin inferir otras coberturas."""
    from fetch_noticias import parse_date, story_time
    url = _safe_link(item.get("link"))
    if not url:
        return None
    declared = _safe_link(item.get("source_url"))
    declared_host = _host(item.get("source_url") or "")
    same_host = bool(declared and _host(declared) == _host(url))
    coverage = next((entry for entry in item.get("coverages") or []
                     if isinstance(entry, dict) and _safe_link(entry.get("link")) == url), None)
    if coverage is not None:
        title = coverage.get("title")
        publisher = coverage.get("source")
        moment = parse_date(coverage.get("published"))
    else:
        sources = item.get("sources") or []
        # Una noticia agrupada puede conservar el nombre del primer editor
        # aunque su enlace ya apunte a otro. Sin evidencia coincidente, omitir.
        if len(sources) != 1 or (declared_host and declared_host != _host(url)):
            return None
        title, publisher, moment = item.get("title"), sources[0], story_time(item)
    if (not title or not publisher or moment is None
            or not _xml_text(title) or not _xml_text(publisher)):
        return None
    # La URL viene del enlace comprobado, nunca de reconstruir el nombre del medio.
    parsed = urlsplit(url)
    source_url = declared if same_host else f"https://{parsed.netloc}"
    return title, url, publisher, source_url, moment


def render_rss(items, now, site_url, title, description, limit=50):
    base = site_url.rstrip("/") + "/"
    rows, seen = [], set()
    publications = [publication for item in items
                    if (publication := _publication(item)) is not None]
    publications.sort(key=lambda publication: publication[4], reverse=True)
    for headline, url, publisher, source_url, moment in publications:
        if len(rows) >= limit:
            break
        if url in seen:
            continue
        if moment is None or moment > now or (now - moment).total_seconds() > 24 * 3600:
            continue
        seen.add(url)
        source_node = (
            '<source url=' + quoteattr(source_url) + '>' + escape(publisher) + '</source>'
            if source_url and publisher else ""
        )
        rows.append(
            "<item><title>" + escape(headline) + "</title>"
            "<link>" + escape(url) + "</link>"
            "<guid isPermaLink=\"true\">" + escape(url) + "</guid>"
            "<pubDate>" + format_datetime(moment.astimezone(timezone.utc), usegmt=True) + "</pubDate>"
            + source_node + "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel><title>' + escape(title) + '</title>'
        '<link>' + escape(base) + '</link><description>' + escape(description)
        + '</description><language>es-CL</language>'
        '<lastBuildDate>' + format_datetime(now.astimezone(timezone.utc), usegmt=True)
        + '</lastBuildDate><ttl>60</ttl>'
        + "".join(rows) + '</channel></rss>\n'
    )


def write_public_feeds(folder, stories, now, site_url, categories):
    """Retorna archivos publicados. El límite de cada feed es explícito."""
    from pathlib import Path
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stories = list(stories)
    paths = ["rss.xml"]
    (folder / "rss.xml").write_text(
        render_rss(stories, now, site_url, "Noticias del Momento · Actualidad",
                   "Selección de titulares recientes y enlaces a medios originales.", limit=50),
        encoding="utf-8")
    rss_folder = folder / "rss"
    rss_folder.mkdir(exist_ok=True)
    for cat, name in categories.items():
        filename = cat + ".xml"
        recent = [s for s in stories if s.get("category") == cat]
        (rss_folder / filename).write_text(
            render_rss(recent, now, site_url, "Noticias del Momento · " + name,
                       "Titulares recientes de " + name + "; publicaciones de terceros.", limit=24),
            encoding="utf-8")
        paths.append("rss/" + filename)
    return paths
