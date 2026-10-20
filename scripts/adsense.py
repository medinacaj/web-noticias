"""Configuración segura y optativa de Google AdSense para sitio estático.

Ningún código publicitario se carga sin decisión explícita ADSENSE_READY=true,
sitio servido en la raíz de un host controlado y privacidad HTTPS revisada.
"""
import html
import re
from urllib.parse import urlsplit

from scripts.newsletter import safe_external_url


PUBLISHER_PATTERN = re.compile(r"^ca-pub-([0-9]{16})$")
GOOGLE_ADS_TXT_CERT = "f08c47fec0942fa0"


def configured_adsense(environ, site_url):
    """Devuelve fragmentos HTML seguros; nunca finge aprobación del sitio."""
    publisher = (environ.get("ADSENSE_PUBLISHER_ID") or "").strip()
    match = PUBLISHER_PATTERN.fullmatch(publisher)
    privacy = safe_external_url(environ.get("ADSENSE_PRIVACY_URL"))
    requested = (environ.get("ADSENSE_READY") or "").strip().lower() == "true"
    site = urlsplit((site_url or "").strip())
    # ads.txt se sirve desde la raíz del HOST. Una ruta de proyecto
    # user.github.io/repo no controla user.github.io/ads.txt.
    # GitHub.io figura en la Public Suffix List: user.github.io/ (sitio
    # de usuario) puede ser válido si se controla realmente su raíz.
    host = (site.hostname or "").lower()
    github_user_site = host.endswith(".github.io") and host.count(".") == 2
    candidate_host = host not in ("github.io", "io") and (
        not host.endswith(".github.io") or github_user_site
    )
    owned_root = (
        site.scheme == "https" and candidate_host
        and site.path in ("", "/") and not site.query and not site.fragment
        and not site.username and not site.password
        and not site.port
    )
    valid_id = bool(match)
    eligible = valid_id and bool(privacy) and owned_root
    enabled = bool(requested and eligible)
    meta = (f'<meta name="google-adsense-account" content="{publisher}">'
            if valid_id else "")
    code = (
        '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
        f'adsbygoogle.js?client={publisher}" crossorigin="anonymous"></script>'
        if enabled else ""
    )
    footer = (
        f'<a class="footer-privacy-link" href="{html.escape(privacy, quote=True)}">'
        'Privacidad y publicidad</a>'
        if privacy and valid_id else ""
    )
    ads_txt = (
        f"google.com, {publisher.replace('ca-', '')}, DIRECT, {GOOGLE_ADS_TXT_CERT}\n"
        if valid_id and owned_root else ""
    )
    return {
        "meta": meta, "code": code, "footer": footer,
        "ads_txt": ads_txt, "enabled": enabled,
        "requested": requested, "valid_id": valid_id,
        "owned_root": owned_root, "privacy_configured": bool(privacy),
    }
