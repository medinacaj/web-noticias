"""Selección controlada de medios reconocidos para cobertura internacional.

Se consulta Google Noticias RSS filtrado por publicación; no se usa RSS
de terceros cuyo permiso de uso comercial no esté aclarado. Los resultados
se atribuyen exclusivamente a los dominios editoriales indicados.
"""
from urllib.parse import urlencode

# Inglés cuando el medio no ofrece redacción en español, sin traducir titulares.
# Conservar equilibrio geográfico: América, Europa, Oriente Medio, África y Asia.
WORLD_NEWS_SOURCES = (
    {"name": "Reuters", "query": "site:reuters.com", "domain": "reuters.com", "language": "en"},
    {"name": "Associated Press", "query": "site:apnews.com", "domain": "apnews.com", "language": "en"},
    {"name": "Al Jazeera English", "query": "site:aljazeera.com", "domain": "aljazeera.com", "language": "en"},
    {"name": "NHK World-Japan", "query": "site:www3.nhk.or.jp/nhkworld", "domain": "nhk.or.jp", "language": "en"},
    {"name": "The Guardian", "query": "site:theguardian.com/world", "domain": "theguardian.com", "language": "en"},
    {"name": "NPR World", "query": "site:npr.org/sections/world", "domain": "npr.org", "language": "en"},
    {"name": "DW Español", "query": "site:dw.com/es", "domain": "dw.com", "language": "es"},
    {"name": "France 24 Español", "query": "site:france24.com/es", "domain": "france24.com", "language": "es"},
    {"name": "CNN en Español", "query": "site:cnnespanol.cnn.com", "domain": "cnn.com", "language": "es"},
    {"name": "El País Internacional", "query": "site:elpais.com/internacional", "domain": "elpais.com", "language": "es"},
    {"name": "Euronews Español", "query": "site:es.euronews.com", "domain": "euronews.com", "language": "es"},
)

MAX_NEWS_PER_WORLD_SOURCE = 4


def world_news_google_url(media):
    """RSS de búsqueda; cada medio tiene su propio cupo de 4 notas."""
    spanish = media["language"] == "es"
    params = {
        "q": media["query"] + " when:1d",
        "hl": "es-419" if spanish else "en-US",
        "gl": "CL" if spanish else "US",
        "ceid": "CL:es-419" if spanish else "US:en",
    }
    return "https://news.google.com/rss/search?" + urlencode(params)


def matches_world_source(story, media):
    """Evita atribuir al medio resultados ajenos devueltos por una búsqueda."""
    from urllib.parse import urlsplit

    src = (story.get("source_url") or "").strip()
    url = urlsplit(src)
    host = (url.hostname or "").lower().rstrip(".")
    expected = media["domain"]
    return (url.scheme == "https" and not url.username and not url.password
            and (host == expected or host.endswith("." + expected)))
