"""Cobertura explícita en titulares, independiente del país del medio.

No consulta artículos ni infiere ubicación por dominio, idioma o IP.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import unicodedata
from urllib.parse import urlencode, urlsplit

# Alias y gentilicios controlados en español/portugués. Sin nombres de políticos,
# ciudades o apellidos: su coincidencia no prueba el país al que alude la noticia.
COUNTRIES = {
    "AR": ("Argentina", r"argentina|argentinos?|argentinas?"),
    "BO": ("Bolivia", r"bolivia|bolivianos?|bolivianas?"),
    "BR": ("Brasil", r"brasil|brazil|brasilenos?|brasilenas?|brasileiros?|brasileiras?"),
    "CL": ("Chile", r"chile|chilenos?|chilenas?"),
    "CO": ("Colombia", r"colombia|colombianos?|colombianas?"),
    "CR": ("Costa Rica", r"costa rica|costarricenses?"),
    "CU": ("Cuba", r"cuba|cubanos?|cubanas?"),
    "DO": ("República Dominicana", r"republica dominicana|dominicanos?|dominicanas?"),
    "EC": ("Ecuador", r"ecuador|ecuatorianos?|ecuatorianas?|equatorianos?|equatorianas?"),
    "GT": ("Guatemala", r"guatemala|guatemaltecos?|guatemaltecas?"),
    "HN": ("Honduras", r"honduras|hondurenos?|hondurenas?"),
    "HT": ("Haití", r"haiti|haitianos?|haitianas?"),
    "MX": ("México", r"mexico|mexicanos?|mexicanas?"),
    "NI": ("Nicaragua", r"nicaragua|nicaraguenses?"),
    "PA": ("Panamá", r"panama|panamenos?|panamenas?"),
    "PE": ("Perú", r"peru|peruanos?|peruanas?"),
    "PR": ("Puerto Rico", r"puerto rico|porto rico|puertorriquenos?|puertorriquenas?"),
    "PY": ("Paraguay", r"paraguay|paraguai|paraguayos?|paraguayas?|paraguaios?|paraguaias?"),
    "SV": ("El Salvador", r"el salvador|salvadorenos?|salvadorenas?"),
    "UY": ("Uruguay", r"uruguay|uruguai|uruguayos?|uruguayas?|uruguaios?|uruguaias?"),
    "VE": ("Venezuela", r"venezuela|venezolanos?|venezolanas?|venezuelanos?|venezuelanas?"),
}


def _fold(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "").casefold())
                   if not unicodedata.combining(c))


def country_codes(title):
    text = _fold(title)
    return [code for code, (_, pattern) in COUNTRIES.items()
            if re.search(r"\b(?:" + pattern + r")\b", text)]


def combine_countries(*values):
    return sorted({code for value in values if isinstance(value, (list, tuple))
                   for code in value if isinstance(code, str) and code in COUNTRIES})


def country_labels(story):
    return [COUNTRIES[code][0] for code in combine_countries(story.get("coverage_countries"))]


def classify(story, catalog=None):
    """Enriquece el historial sin reemplazar la política de datos ya existente."""
    codes = combine_countries(story.get("coverage_countries"), country_codes(story.get("title")))
    if codes:
        story["coverage_countries"] = codes
    if (story.get("category") == "internacional" and any(code != "CL" for code in codes)
            and (catalog is None or catalog_allowed(story, catalog))):
        story["category"] = "latinoamerica"
    return story


def merge_countries(target, incoming):
    codes = combine_countries(target.get("coverage_countries"), incoming.get("coverage_countries"))
    if codes:
        target["coverage_countries"] = codes
    if (target.get("category") == "internacional"
            and incoming.get("category") == "latinoamerica"
            and any(code != "CL" for code in codes)):
        target["category"] = "latinoamerica"
        if incoming.get("title"):
            target["title"] = incoming["title"]
            if "_norm" in target:
                from fetch_noticias import normalize_title
                target["_norm"] = normalize_title(target["title"])


def search_urls():
    searches = [
        {"q": "(Brasil OR brasileiros OR brasileiras) when:1d", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
        {"q": '(México OR Guatemala OR Honduras OR "El Salvador" OR Nicaragua OR "Costa Rica" OR Panamá) when:1d',
         "hl": "es-419", "gl": "MX", "ceid": "MX:es-419"},
        {"q": "(Bolivia OR Colombia OR Ecuador OR Perú OR Venezuela) when:1d",
         "hl": "es-419", "gl": "CO", "ceid": "CO:es-419"},
        {"q": '(Argentina OR Paraguay OR Uruguay OR Cuba OR Haití OR "Puerto Rico" OR "República Dominicana") when:1d',
         "hl": "es-419", "gl": "AR", "ceid": "AR:es-419"},
    ]
    return ["https://news.google.com/rss/search?" + urlencode(params) for params in searches]


def explicit_date(value):
    """Rechaza fecha ausente, inválida o sin zona; no asigna UTC implícitamente."""
    if not value:
        return None
    try:
        date = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError, OverflowError):
        try:
            date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, OverflowError):
            return None
    try:
        if date.tzinfo is None or date.utcoffset() is None:
            return None
        # Una fecha válida en su zona puede exceder datetime al convertirla a
        # UTC. Se rechaza aquí para no abortar el feed ni los demás editores.
        return date.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def catalog_allowed(item, catalog):
    """No eludir los permisos del catálogo cambiando la vía de recolección."""
    try:
        hosts = [(urlsplit(item.get(field) or "").hostname or "").lower().rstrip(".")
                 for field in ("source_url", "link")]
    except (ValueError, TypeError):
        return False
    names = [_fold(name) for name in (item.get("sources") or [item.get("source")]) if name]
    for source in catalog:
        domain = source.get("domain", "").lower().rstrip(".")
        known = (domain and any(host == domain or host.endswith("." + domain) for host in hosts))
        if known or _fold(source.get("name")) in names:
            if not (source.get("enabled") is True and source.get("permission_status") == "approved"
                    and source.get("technical_status") == "verified" and source.get("permission_evidence")):
                return False
    return True


def source_requires_metadata_only(item, catalog):
    """Conservar restricciones de colectores especializados y fuentes catalogadas."""
    if item.get("metadata_policy") == "source" or item.get("publisher_id") or item.get("discovery_edition"):
        return True
    from scripts.global_sources import load_catalog as load_world_catalog
    try:
        hosts = [(urlsplit(item.get(field) or "").hostname or "").lower().rstrip(".")
                 for field in ("source_url", "link")]
    except (ValueError, TypeError):
        return True
    names = [_fold(name) for name in (item.get("sources") or [item.get("source")]) if name]
    for source in list(catalog) + load_world_catalog():
        domain = source.get("domain", "").lower().rstrip(".")
        if ((domain and any(host == domain or host.endswith("." + domain) for host in hosts))
                or _fold(source.get("name")) in names):
            return True
    return False


def restore_legacy_image_policy(story, catalog):
    """Reparación explícita de datos conocidos; nunca se aplica al cargar un archivo."""
    from scripts.article_images import is_google_news
    if (story.get("category") == "latinoamerica" and story.get("metadata_only")
            and is_google_news(story.get("link"))
            and not source_requires_metadata_only(story, catalog)):
        story["metadata_only"] = False


def prepare_item(item, now, catalog):
    """Misma puerta de entrada para las búsquedas de cada subregión."""
    from scripts.article_images import permitted_url
    from fetch_noticias import to_iso, safe_image
    published = explicit_date(item.get("published"))
    codes = country_codes(item.get("title"))
    source_url = item.get("source_url") or ""
    if (not item.get("title") or not any(code != "CL" for code in codes)
            or published is None
            or not now - timedelta(hours=24) <= published <= now + timedelta(minutes=15)
            or not permitted_url(source_url, check_dns=False)):
        return None
    try:
        link = urlsplit(item.get("link") or "")
        source_host = (urlsplit(source_url).hostname or "").lower().rstrip(".").removeprefix("www.")
        host = (link.hostname or "").lower().rstrip(".").removeprefix("www.")
        if link.scheme != "https" or not host or link.username or link.password or link.port not in (None, 443):
            return None
        google = host == "news.google.com" and link.path.startswith(("/rss/articles/", "/articles/"))
        editorial = (permitted_url(item.get("link"), check_dns=False) and link.path.strip("/")
                     and (host == source_host or host.endswith("." + source_host)))
        if not (google or editorial) or not catalog_allowed(item, catalog):
            return None
    except (ValueError, TypeError):
        return None
    metadata_only = bool(item.get("metadata_only")) or source_requires_metadata_only(item, catalog)
    return {**item, "category": "latinoamerica", "coverage_countries": codes,
            "published": to_iso(published), "summary": "",
            "image": "" if metadata_only else safe_image(item.get("image")),
            "metadata_only": metadata_only}
