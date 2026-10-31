"""Estrenos individuales verificados: fechas de estreno ≠ fechas de publicación.

El catálogo es editorial: requiere confirmación de mercado y enlaces a noticia
específica y ficha oficial. Nunca se infiere un estreno desde un RSS o guía.
"""
from datetime import date
import json
from pathlib import Path

from scripts.global_sources import matches_world_source
from scripts.latam import catalog_allowed
from scripts.weekly_releases import week_bounds

CATALOG = Path(__file__).resolve().parents[1] / "data" / "premieres.json"


def load_catalog(path=CATALOG):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        records = data.get("premieres", [])
        return records if isinstance(records, list) else []
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f"[aviso] Catálogo de estrenos no disponible: {type(error).__name__}")
        return []


def current_premieres(items, now, restrictions=None):
    """Solo títulos con prueba editorial de estreno en Chile esta semana.

    El enlace principal conduce a la noticia individual, no a un artículo de
    estrenos generales. La ficha de disponibilidad respalda la fecha/territorio.
    """
    from scripts.article_images import permitted_url
    from scripts.dedupe_history import canonical_key
    from scripts.global_sources import load_catalog as world
    from scripts.regional_sources import load_catalog as regional

    restrictions = world() + regional() if restrictions is None else restrictions
    start, end = week_bounds(now)
    seen, accepted = set(), []
    for item in items or []:
        if not isinstance(item, dict) or item.get("verified") is not True or item.get("region") != "CL":
            continue
        title, source = item.get("title"), item.get("source")
        format_ = item.get("format")
        platform = item.get("platform")
        if (not isinstance(title, str) or not title.strip() or len(title) > 180
                or not isinstance(source, str) or not source.strip() or len(source) > 100
                or format_ not in ("Cine", "Streaming")
                or (format_ == "Streaming" and (not isinstance(platform, str) or not platform.strip()))
                or (format_ == "Cine" and platform not in ("", None))):
            continue
        try:
            premiere_day = date.fromisoformat(item["release_date"])
        except (TypeError, ValueError, KeyError):
            continue
        if not start.date() <= premiere_day < end.date():
            continue
        article = {"source_url": item.get("source_url"), "link": item.get("link"), "source": source}
        evidence = item.get("verification_url")
        if (not matches_world_source(article, {"domain": _host(article["source_url"])})
                or not catalog_allowed(article, restrictions)
                or not isinstance(evidence, str) or not permitted_url(evidence, check_dns=False)):
            continue
        key = canonical_key(article["link"])
        if key in seen:
            continue
        seen.add(key)
        accepted.append({
            "title": title.strip(), "source": source.strip(), "source_url": article["source_url"],
            "link": article["link"], "release_date": premiere_day.isoformat(),
            "verification_url": evidence, "format": format_,
            "platform": platform.strip() if isinstance(platform, str) else "",
            "region": "CL", "published": None, "summary": "", "image": "",
            "metadata_only": True, "content_kind": "premiere",
        })
    return sorted(accepted, key=lambda x: (x["release_date"], x["title"]))[:12]


def _host(url):
    from urllib.parse import urlsplit
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".")
    except (TypeError, ValueError, AttributeError):
        return ""
