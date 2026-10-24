"""Ediciones internacionales de entretenimiento de la vía Google RSS existente.

La edición indica dónde se descubrió un titular, no el país del artista o medio.
Solo metadatos: sin descargar artículos, resúmenes o fotos ni activar catálogos.
"""
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

from scripts.article_images import permitted_url
from scripts.dedupe_history import canonical_key
from scripts.latam import catalog_allowed, explicit_date
from scripts.source_diversity import diverse_prefix, publisher_key

EDITIONS = (("ES", "es", "ES:es"), ("MX", "es-419", "MX:es-419"))
MAX_PER_EDITION = 6


def edition_url(country, language, edition):
    return "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?" + urlencode(
        {"hl": language, "gl": country, "ceid": edition})


def collect_entertainment(now, fetch=None):
    from fetch_noticias import fetch_rss
    from scripts.global_sources import load_catalog as load_world_catalog
    from scripts.regional_sources import load_catalog as load_regional_catalog
    fetch = fetch_rss if fetch is None else fetch
    catalog = load_world_catalog() + load_regional_catalog()
    results, seen = [], set()
    for country, language, edition in EDITIONS:
        try:
            items = fetch(edition_url(country, language, edition), "cultura", metadata_only=True)
        except Exception as error:
            print(f"[aviso] Entretenimiento ({country}) no disponible: {error}")
            continue
        accepted = 0
        for item in items:
            title, source = item.get("title"), item.get("source")
            moment = explicit_date(item.get("published"))
            source_url, link = item.get("source_url") or "", item.get("link") or ""
            if any(not isinstance(value, str) or "\\" in value
                   or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
                   for value in (source_url, link)):
                continue
            if (not isinstance(title, str) or not title.strip()
                    or not isinstance(source, str) or not source.strip()
                    or moment is None or not now - timedelta(hours=24) <= moment <= now + timedelta(minutes=15)
                    or not permitted_url(source_url, check_dns=False)):
                continue
            editorial_host = (urlsplit(source_url).hostname or "").lower().rstrip(".")
            if not catalog_allowed(item, catalog):
                continue
            try:
                parsed = urlsplit(link)
                google = (parsed.scheme == "https" and parsed.hostname == "news.google.com"
                          and not parsed.username and not parsed.password and parsed.port in (None, 443)
                          and parsed.path.startswith(("/rss/articles/", "/articles/"))
                          and bool(parsed.path.rsplit("/", 1)[-1]))
                direct_host = (parsed.hostname or "").lower().rstrip(".")
                direct = (permitted_url(link, check_dns=False) and bool(parsed.path.strip("/")) and
                          (direct_host == editorial_host or direct_host.endswith("." + editorial_host)))
                if not (google or direct):
                    continue
                key = canonical_key(link)
            except (TypeError, ValueError):
                continue
            if not key or key in seen:
                continue
            seen.add(key)
            results.append({**item, "category": "cultura", "metadata_only": True,
                            "summary": "", "image": "", "discovery_edition": country})
            accepted += 1
            if accepted == MAX_PER_EDITION:
                break
    return results


def balance_entertainment(candidates, limit):
    """Reservar hasta tres de seis posiciones a las ediciones complementarias.

    Es una distribución de entradas, no una afirmación del país de cada noticia.
    Sin suficientes alternativas, completar con las disponibles; no borrar notas.
    """
    size = min(6, limit)
    if size <= 0:
        return []
    foreign = [s for s in candidates if s.get("discovery_edition") in ("ES", "MX")]
    local = [s for s in candidates if s.get("discovery_edition") not in ("ES", "MX")]
    abroad = diverse_prefix(foreign, min(3, size))
    counts = {}
    for story in abroad:
        editor = publisher_key(story)
        counts[editor] = counts.get(editor, 0) + 1
    existing = diverse_prefix(local, size - len(abroad), initial_counts=counts)
    prefix = []
    for index in range(max(len(abroad), len(existing))):
        if index < len(abroad): prefix.append(abroad[index])
        if index < len(existing): prefix.append(existing[index])
    selected = {id(story) for story in prefix}
    rest = [s for s in candidates if id(s) not in selected]
    return (prefix + rest)[:limit]
