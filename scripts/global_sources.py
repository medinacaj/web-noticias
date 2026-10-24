"""Búsquedas mundiales dirigidas opt-in; no altera las vías previas de ingesta.

El catálogo sólo prepara candidatos, sin acreditar permisos de uso de Google
Noticias o de sus editores. Las fuentes pendientes nunca se consultan aquí.
"""
from datetime import timedelta
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from xml.etree.ElementTree import ParseError

from scripts.article_images import permitted_url
from scripts.dedupe_history import canonical_key
from scripts.latam import explicit_date
from scripts.regional_sources import _editorial_url

CATALOG = Path(__file__).resolve().parents[1] / "config" / "world_sources.json"
MAX_SEARCHES = 10
MAX_ITEMS = 4


def load_catalog(path=CATALOG):
    return json.loads(Path(path).read_text(encoding="utf-8"))["sources"]


def enabled_source(media):
    """La activación es explícita y conjunta; ni nombre ni disponibilidad bastan."""
    evidence = media.get("permission_evidence")
    scope = media.get("search_scope") or ""
    return (media.get("enabled") is True and media.get("permission_status") == "approved"
            and media.get("technical_status") == "verified"
            and isinstance(evidence, str) and bool(evidence.strip())
            and media.get("language") in ("en", "es") and isinstance(scope, str)
            and not any(char.isspace() for char in scope)
            and permitted_url("https://" + (media.get("domain") or ""), check_dns=False)
            and _editorial_url("https://" + scope, media.get("domain")))


def world_news_google_url(media):
    spanish = media["language"] == "es"
    return "https://news.google.com/rss/search?" + urlencode({
        "q": "site:" + media["search_scope"] + " when:1d",
        "hl": "es-419" if spanish else "en-US", "gl": "CL" if spanish else "US",
        "ceid": "CL:es-419" if spanish else "US:en",
    })


def matches_world_source(item, media):
    """Verifica dominio editorial y destino; no confía en el nombre del medio."""
    source_url, link = item.get("source_url"), item.get("link")
    # urllib puede eliminar controles antes de parsear: no aceptarlos ni admitir
    # barras inversas que los navegadores interpreten como separadores de host.
    if any(not isinstance(value, str) or "\\" in value or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
           for value in (source_url, link)):
        return False
    domain = media.get("domain")
    if not (permitted_url(source_url, check_dns=False) and _editorial_url(source_url, domain)):
        return False
    if permitted_url(link, check_dns=False) and _editorial_url(link, domain, article=True):
        return True
    try:
        parsed = urlsplit(link)
        return (parsed.scheme == "https" and (parsed.hostname or "").lower().rstrip(".") == "news.google.com"
                and not parsed.username and not parsed.password and parsed.port in (None, 443)
                and parsed.path.startswith(("/rss/articles/", "/articles/"))
                and bool(parsed.path.rsplit("/", 1)[-1]))
    except (TypeError, ValueError):
        return False


def prepare_item(item, media, now):
    """Sólo metadatos y fecha original con zona; no hay consultas al artículo."""
    from fetch_noticias import to_iso
    published = explicit_date(item.get("published"))
    title = item.get("title")
    if (not enabled_source(media) or not isinstance(title, str) or not title.strip()
            or published is None or not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15)
            or not matches_world_source(item, media)):
        return None
    return {**item, "category": "internacional", "publisher_id": media["id"],
            "published": to_iso(published), "metadata_only": True, "summary": "", "image": ""}


def collect_world(now, fetch=None, catalog=None):
    """Máximo diez búsquedas y cuatro URLs únicas por editor activo y ejecución."""
    if fetch is None:
        from fetch_noticias import fetch_rss
        fetch = fetch_rss
    sources = load_catalog() if catalog is None else catalog
    result, searched = [], set()
    for media in sources:
        if not enabled_source(media) or media["domain"] in searched:
            continue
        if len(searched) >= MAX_SEARCHES:
            break
        searched.add(media["domain"])
        try:
            seen, accepted = set(), []
            for item in fetch(world_news_google_url(media), "internacional", metadata_only=True):
                record = prepare_item(item, media, now)
                if record is None:
                    continue
                key = canonical_key(record["link"])
                if key in seen:
                    continue
                seen.add(key)
                accepted.append(record)
                if len(accepted) == MAX_ITEMS:
                    break
            result.extend(accepted)
            print(f"Medio mundial {media['name']}: {len(accepted)} titulares")
        except (OSError, ValueError, TypeError, LookupError, ParseError) as error:
            print(f"[aviso] Medio mundial {media['name']} falló: {error}")
    return result
