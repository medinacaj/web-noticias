"""Configuración segura y optativa de Google AdSense para sitio estático.

Ningún código publicitario se carga sin decisión explícita ADSENSE_READY=true,
dominio raíz propio y URL HTTPS de privacidad revisada.
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
    # ads.txt debe publicarse desde la raíz del host. Una ruta de proyecto
    # *.github.io/repo no controla /ads.txt en *.github.io.
    owned_root = (
        site.scheme == "https" and bool(site.hostname)
        and site.path in ("", "/") and not site.query and not site.fragment
        and not site.username and not site.password
        and site.hostname != "github.io"
        and not site.hostname.endswith(".github.io")
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
