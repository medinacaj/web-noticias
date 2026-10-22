"""Selección por editor sin descartar candidatos ni modificar sus datos."""
import re
import unicodedata
from urllib.parse import urlsplit


_NAME_ALIASES = {
    "bbc": "bbc.com",
    "bbc mundo": "bbc.com",
    "bbc news mundo": "bbc.com",
    "biobiochile": "biobiochile.cl",
    "bio bio": "biobiochile.cl",
    "bio bio chile": "biobiochile.cl",
}


def _editorial_domain(url):
    try:
        parsed = urlsplit(str(url or "").strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if (parsed.scheme not in ("http", "https") or "." not in host
                or parsed.username or parsed.password
                or not re.fullmatch(r"[a-z0-9.-]+", host)
                or host == "news.google.com" or host.endswith(".news.google.com")):
            return ""
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    for domain, canonical in (("bbc.com", "bbc.com"), ("bbc.co.uk", "bbc.com"),
                              ("biobiochile.cl", "biobiochile.cl")):
        if host == domain or host.endswith("." + domain):
            return canonical
    return host


def publisher_key(story):
    """Identidad del editor principal: dominio editorial, luego nombre."""
    for url in (story.get("source_url"), story.get("link")):
        domain = _editorial_domain(url)
        if domain:
            return domain
    sources = story.get("sources") or []
    primary = sources[0] if sources else story.get("source") or "Fuente"
    folded = unicodedata.normalize("NFKD", str(primary).casefold())
    name = " ".join(re.findall(r"[^\W_]+", "".join(
        ch for ch in folded if not unicodedata.combining(ch))))
    return _NAME_ALIASES.get(name, name or "fuente")


def diverse_prefix(candidates, size, max_per_source=2, initial_counts=None):
    """Priorizar la cuota en orden; rellenar después con los diferidos.

    ``initial_counts`` usa claves de ``publisher_key`` para reservar editores
    ya presentes en otra sección. La cuota es flexible si faltan alternativas.
    La lista de entrada y sus artículos permanecen disponibles sin cambios.
    """
    if size <= 0:
        return []
    counts = dict(initial_counts or {})
    selected, deferred = [], []
    for story in candidates:
        key = publisher_key(story)
        if counts.get(key, 0) >= max_per_source:
            deferred.append(story)
            continue
        selected.append(story)
        counts[key] = counts.get(key, 0) + 1
        if len(selected) == size:
            return selected
    return selected + deferred[:size - len(selected)]
