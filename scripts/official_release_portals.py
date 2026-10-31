"""Directorio de fuentes oficiales para verificar estrenos y noticias.

Enlaces de consulta, no fuentes automáticas: una página de prensa global o
estadounidense no acredita por sí sola disponibilidad ni fecha en Chile.
No se extrae contenido, no se copian imágenes y no se crean noticias ficticias.
"""
from html import escape
from urllib.parse import urlsplit

# Páginas verificadas como oficiales el 31-10-2026.
# discovery_only=True: los derechos/condiciones de sindicación automática no
# están acreditados. Su aprobación requeriría revisión editorial y jurídica.
OFFICIAL_PORTALS = (
    ("Netflix", "Estrenos Netflix", "https://about.netflix.com/es/new-to-watch", "Internacional"),
    ("Netflix", "Noticias Netflix", "https://about.netflix.com/es/newsroom", "Internacional"),
    ("HBO Max", "HBO Max", "https://press.wbd.com/us/brands/hbo-max", "EE. UU."),
    ("Prime Video", "Prime Video", "https://www.aboutamazon.com/news/entertainment", "Internacional"),
    ("Disney+", "Disney+", "https://press.disneyplus.com/news", "Internacional"),
    ("Mega / MegaGo", "Mega · Noticias", "https://www.mega.cl/entretenimiento/", "Chile"),
    ("Mega / MegaGo", "Mega / MegaGo", "https://www.mega.cl/temas/megashorts/", "Chile"),
)


def official_portals():
    """Devuelve enlaces de referencia con identidad de dominio verificada."""
    return tuple(
        {"brand": brand, "label": label, "url": url, "market": market,
         "discovery_only": True}
        for brand, label, url, market in OFFICIAL_PORTALS
    )


def render_official_portals():
    """HTML de enlaces independientes del flujo de noticias o guías."""
    links = []
    for portal in official_portals():
        url = portal["url"]
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            continue
        links.append(
            f'<a href="{escape(url, quote=True)}" rel="noopener noreferrer"'
            f' title="Fuente oficial · {escape(portal["market"], quote=True)}">'
            f'{escape(portal["label"])}</a>'
        )
    if not links:
        return ""
    return ('<nav class="official-release-portals" aria-label="Fuentes oficiales de estrenos">'
            '<span class="official-release-portals-label">Portales oficiales:</span>'
            + "".join(links) + '</nav>'
            '<p class="official-release-portal-note">'
            'Fuentes de consulta. Las novedades internacionales no garantizan un estreno en Chile.'
            '</p>')
