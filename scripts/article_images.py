"""Recuperación prudente de imágenes del editor original, sin descargar fotografías.

Solo consulta artículos visibles y conserva el favicon del medio como respaldo.
Las URLs de fotografías se referencian desde la web del editor; no se copian.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import ipaddress
import logging
import re
import socket
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)

LOG = logging.getLogger(__name__)
MAX_LOOKUPS = 30
RETRY_HOURS = 4
MAX_HTML_BYTES = 450_000
NETWORK_TIMEOUT = 6
GOOGLE_NEWS_HOST = "news.google.com"


def permitted_url(url, *, check_dns=True):
    """No consultar direcciones internas, hosts IP ni URLs con credenciales."""
    try:
        p = urlsplit((url or "").strip())
        hostname = (p.hostname or "").lower().rstrip(".")
        if (p.scheme != "https" or p.username or p.password or p.port not in (None, 443)
                or not re.fullmatch(r"[a-z0-9.-]+", hostname)
                or "." not in hostname or hostname.endswith(".local")
                or hostname in ("localhost", GOOGLE_NEWS_HOST)):
            return False
        try:
            # Los hosts expresados como IP son rechazados incluso sin consulta DNS.
            ipaddress.ip_address(hostname)
            return False
        except ValueError:
            pass
        if not check_dns:
            return True
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(info[4][0]).is_global for info in addresses)
    except (ValueError, UnicodeError, OSError):
        return False


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not permitted_url(newurl):
            raise ValueError("Redirección a destino no público")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PictureMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.candidates = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
            if key in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src", "image"):
                self.candidates.setdefault(key, attrs.get("content", "").strip())
        elif tag == "link" and "image_src" in (attrs.get("rel") or "").lower():
            self.candidates.setdefault("image_src", attrs.get("href", "").strip())


def image_from_html(html_text, article_url):
    parser = PictureMetadata()
    parser.feed(html_text)
    for key in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src", "image", "image_src"):
        value = parser.candidates.get(key)
        if value:
            image_url = urljoin(article_url, value)
            if permitted_url(image_url, check_dns=False):
                return image_url
    return ""


def publisher_page_image(article_url):
    """Metadatos oficiales; respuestas acotadas y sin saltar a redes privadas."""
    if not permitted_url(article_url):
        return ""
    opener = build_opener(SafeRedirects)
    request = Request(article_url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; NoticiasDelMomento/2.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with opener.open(request, timeout=NETWORK_TIMEOUT) as response:
        if "html" not in (response.headers.get("Content-Type") or "").lower():
            return ""
        final_url = response.geturl()
        if not permitted_url(final_url):
            return ""
        raw = response.read(MAX_HTML_BYTES)
        charset = response.headers.get_content_charset() or "utf-8"
        return image_from_html(raw.decode(charset, errors="replace"), final_url)


def is_google_news(url):
    try:
        p = urlsplit(url or "")
        return p.scheme == "https" and (p.hostname or "").lower() == GOOGLE_NEWS_HOST
    except ValueError:
        return False


def enrich_visible_images(stories, selected, now, decoder=None, fetch_image=publisher_page_image,
                          max_lookups=MAX_LOOKUPS):
    """Solo artículos publicados, caché de errores y máximo de URLs por ejecución."""
    visible = ([selected["lead"]] if selected["lead"] else []) + selected["secondary"]
    for category_items in selected["by_category"].values():
        visible.extend(category_items)
    unique, seen = [], set()
    for story in visible:
        key = id(story)
        if key in seen or story.get("image") or story.get("image_fetch_disabled"):
            continue
        seen.add(key)
        checked = story.get("image_checked_at", "")
        try:
            prev = datetime.fromisoformat(checked.replace("Z", "+00:00"))
            if prev.tzinfo and now - prev < timedelta(hours=RETRY_HOURS):
                continue
        except (ValueError, AttributeError, TypeError):
            pass
        unique.append(story)
        if len(unique) >= max_lookups:
            break

    if not unique:
        return (0, 0)
    google_urls = list(dict.fromkeys(s["link"] for s in unique if is_google_news(s.get("link"))))
    resolved = {}
    if google_urls:
        try:
            if decoder is None:
                from gnews_decoder import decode_many
                decoder = decode_many
            resolved = decoder(google_urls, concurrency=6, timeout=8) or {}
        except Exception as exc:
            LOG.warning("La resolución de enlaces de Google Noticias falló: %s", exc)

    def task(story):
        link = story.get("link", "")
        candidate = resolved.get(link) if is_google_news(link) else link
        if not candidate or not permitted_url(candidate):
            return story, "", ""
        try:
            image = fetch_image(candidate)
        except Exception as exc:
            LOG.info("No se pudo leer la imagen del editor %s: %s", urlsplit(candidate).hostname, exc)
            image = ""
        return story, candidate, image if permitted_url(image, check_dns=False) else ""

    count = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for story, article_url, image in pool.map(task, unique):
            story["image_checked_at"] = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            if article_url and is_google_news(story.get("link")):
                story["link"] = article_url
                story["source_url"] = story.get("source_url") or article_url
            if image:
                story["image"] = image
                count += 1
    print(f"Fotografías editoriales: {count}/{len(unique)} recuperadas de páginas originales")
    return count, len(unique)
