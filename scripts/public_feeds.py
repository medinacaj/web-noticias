"""RSS original del portal: índice y secciones con titulares, enlaces y atribución.
No republica fotografías, cuerpos, extractos ni material licenciado de editores.
"""
from datetime import timezone
from email.utils import format_datetime
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr


def _safe_link(value):
    try:
        p = urlsplit(str(value or ""))
        if (p.scheme == "https" and p.hostname and not p.username and not p.password
                and p.port in (None, 443)):
            return value
    except (ValueError, TypeError):
        pass
    return ""


def render_rss(items, now, site_url, title, description, limit=50):
    from fetch_noticias import story_time
    base = site_url.rstrip("/") + "/"
    rows, seen = [], set()
    for item in items:
        if len(rows) >= limit:
            break
        url = _safe_link(item.get("link"))
        if not url or url in seen or not item.get("title"):
            continue
        moment = story_time(item)
        if moment is None or moment > now or (now - moment).total_seconds() > 24 * 3600:
            continue
        seen.add(url)
        sources = item.get("sources") or []
        publisher = sources[0] if sources else ""
        source_url = _safe_link(item.get("source_url"))
        source_node = (
            '<source url=' + quoteattr(source_url) + '>' + escape(publisher) + '</source>'
            if source_url and publisher else ""
        )
        rows.append(
            "<item><title>" + escape(item["title"]) + "</title>"
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
    ordered = sorted(stories, key=lambda s: s.get("published") or s.get("first_seen") or "", reverse=True)
    paths = ["rss.xml"]
    (folder / "rss.xml").write_text(
        render_rss(ordered, now, site_url, "Noticias del Momento · Actualidad",
                   "Selección de titulares recientes y enlaces a medios originales.", limit=50),
        encoding="utf-8")
    rss_folder = folder / "rss"
    rss_folder.mkdir(exist_ok=True)
    for cat, name in categories.items():
        filename = cat + ".xml"
        recent = [s for s in ordered if s.get("category") == cat]
        (rss_folder / filename).write_text(
            render_rss(recent, now, site_url, "Noticias del Momento · " + name,
                       "Titulares recientes de " + name + "; publicaciones de terceros.", limit=24),
            encoding="utf-8")
        paths.append("rss/" + filename)
    return paths
