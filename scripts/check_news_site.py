#!/usr/bin/env python3
"""Monitor externo de GitHub Pages. Solo descarga nuestra portada y sitemap."""
import html.parser
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

DEFAULT_SITE = "https://medinacaj.github.io/web-noticias/"
# Dos ciclos horarios perdidos ameritan alerta; no esperar una jornada parcial.
MAX_AGE_HOURS = 2


class EditionParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.updated = ""
        self.title_seen = False

    def handle_starttag(self, tag, attrs):
        params = dict(attrs)
        if tag == "time" and params.get("id") == "updated-at":
            self.updated = params.get("datetime") or ""

    def handle_data(self, data):
        if "Noticias del Momento" in data:
            self.title_seen = True


def assess(html_text, sitemap_xml, now, deployment="success", base=DEFAULT_SITE):
    warnings = []
    if deployment not in ("", "success"):
        warnings.append(f"Resultado del despliegue: {deployment}")
    parser = EditionParser()
    parser.feed(html_text)
    if not parser.title_seen:
        warnings.append("La portada pública no identifica el portal esperado")
    try:
        publication = datetime.fromisoformat(parser.updated.replace("Z", "+00:00"))
        if publication.tzinfo is None:
            raise ValueError("Fecha sin zona")
        age = (now - publication.astimezone(timezone.utc)).total_seconds() / 3600
        if age > MAX_AGE_HOURS:
            warnings.append(f"Publicación desactualizada: {age:.1f} h")
        if age < -1:
            warnings.append("Fecha de portada en el futuro")
    except (ValueError, TypeError, OverflowError):
        warnings.append("Fecha de publicación no válida o ausente")
    try:
        root = ET.fromstring(sitemap_xml)
        urls = [node.text for node in root.iter() if node.tag.endswith("}loc")]
        if base.rstrip("/") + "/" not in urls:
            warnings.append("El sitemap no incluye la URL pública canónica")
    except ET.ParseError:
        warnings.append("Sitemap XML inválido")
    return warnings


def read_public(url):
    req = Request(url, headers={"User-Agent": "WebNoticias-HealthWatch/1.0",
                                "Cache-Control": "no-cache"})
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Respuesta demasiado grande")
        return data.decode("utf-8", errors="replace")


def main():
    base = (os.environ.get("SITE_URL") or DEFAULT_SITE).strip().rstrip("/") + "/"
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        print("URL pública no válida")
        return 2
    issues = []
    try:
        page = read_public(base)
        sitemap = read_public(base + "sitemap.xml")
        issues = assess(page, sitemap, datetime.now(timezone.utc),
                        os.environ.get("DEPLOY_CONCLUSION", "success"), base)
    except Exception as exc:
        issues = [f"No se pudo verificar GitHub Pages: {type(exc).__name__}: {exc}"]
    if issues:
        print("ALERTA: " + " | ".join(issues))
        return 1
    print("OK: portada pública, fecha y sitemap verificados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

