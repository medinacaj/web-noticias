"""Fragmentos AdSense optativos; nunca hacen solicitudes ni activan una cuenta.

La raíz administrable es un control explícito del proyecto, no una afirmación
de propiedad, aprobación de Google o cumplimiento de privacidad.
"""
import html
import ipaddress
import os
import re
from urllib.parse import urlsplit

from scripts.newsletter import safe_external_url


PUBLISHER_PATTERN = re.compile(r"ca-pub-([0-9]{16})")
DOCUMENTATION_IDS = {"ca-pub-0000000000000000", "ca-pub-1234567890123456"}
GOOGLE_ADS_TXT_CERT = "f08c47fec0942fa0"


def _root_candidate(site_url):
    """Comprueba forma de URL raíz pública; no demuestra control del host."""
    safe = safe_external_url(site_url)
    if not safe:
        return False
    site = urlsplit(safe)
    host = (site.hostname or "").lower()
    if (site.path not in ("", "/") or site.query or site.fragment
            or site.netloc.lower() != host or "." not in host):
        return False
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part)
           for part in host.split(".")):
        return False
    if host.rsplit(".", 1)[-1] in {"local", "localhost", "internal", "invalid", "test"}:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    if host == "github.io" or (host.endswith(".github.io") and host.count(".") != 2):
        return False
    return True


def configured_adsense(environ=None, site_url=""):
    """Devuelve HTML/ads.txt sin efectos laterales; omite anuncios ante dudas.

    ``None`` lee os.environ; un mapping vacío desactiva toda configuración.
    ADSENSE_ROOT_CONTROLLED es la declaración del responsable tras verificar la
    publicación en raíz; la forma de SITE_URL por sí sola nunca la sustituye.
    """
    env = os.environ if environ is None else environ
    publisher = str(env.get("ADSENSE_PUBLISHER_ID") or "").strip()
    valid_id = bool(PUBLISHER_PATTERN.fullmatch(publisher)) and publisher not in DOCUMENTATION_IDS
    requested = str(env.get("ADSENSE_READY") or "").strip().lower() == "true"
    root_controlled = str(env.get("ADSENSE_ROOT_CONTROLLED") or "").strip().lower() == "true"
    privacy = safe_external_url(env.get("ADSENSE_PRIVACY_URL"))
    owned_root = bool(root_controlled and _root_candidate(site_url))
    enabled = bool(requested and valid_id and privacy and owned_root)
    return {
        "requested": requested, "enabled": enabled, "valid_id": valid_id,
        "owned_root": owned_root, "privacy_configured": bool(privacy),
        "meta": (f'<meta name="google-adsense-account" content="{publisher}">'
                 if valid_id else ""),
        "script": ('<script async src="https://pagead2.googlesyndication.com/pagead/js/'
                   f'adsbygoogle.js?client={publisher}" crossorigin="anonymous"></script>'
                   if enabled else ""),
        "footer": (f'<a class="footer-privacy-link" href="{html.escape(privacy, quote=True)}">'
                   'Privacidad y publicidad</a>' if privacy and valid_id else ""),
        "ads_txt": (f"google.com, {publisher[3:]}, DIRECT, {GOOGLE_ADS_TXT_CERT}\n"
                    if valid_id and owned_root else ""),
    }
