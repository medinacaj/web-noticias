#!/usr/bin/env python3
"""Comprobaciones SEO locales de las páginas estáticas (sin métricas inventadas).

Ejecutar tras: python3 fetch_noticias.py --solo-render
"""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


class HeadInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.links = []
        self.title = []
        self.in_title = False
        self.jsonld = []
        self.in_jsonld = False

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = props.get("name") or props.get("property")
            if key:
                self.meta.setdefault(key, []).append(props.get("content", ""))
        elif tag == "link":
            self.links.append(props)
        elif tag == "script" and props.get("type") == "application/ld+json":
            self.in_jsonld = True
            self.jsonld.append("")

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.in_jsonld:
            self.jsonld[-1] += data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script":
            self.in_jsonld = False


def inspect_site(folder):
    """Devuelve errores; solo valida el HTML generado y los enlaces internos."""
    root = Path(folder)
    errors = []
    pages = {}
    for name in ("index.html", "sobre-el-portal.html", "boletin-diario.html", "404.html"):
        file = root / name
        if not file.is_file():
            errors.append(f"Página ausente: {name}")
            continue
        content = file.read_text(encoding="utf-8")
        parser = HeadInspector()
        parser.feed(content)
        pages[name] = (content, parser)
        if "%%" in content and re.search(r"%%[A-Z_]+%%", content):
            errors.append(f"Marcadores pendientes: {name}")
    if "index.html" not in pages or "sobre-el-portal.html" not in pages:
        return errors
    home_html, home = pages["index.html"]
    about_html, about = pages["sobre-el-portal.html"]
    indexable_urls = []
    for name, content, head, graph_type in (
        ("index.html", home_html, home, "CollectionPage"),
        ("sobre-el-portal.html", about_html, about, "AboutPage"),
    ):
        title = "".join(head.title).strip()
        if not 20 <= len(title) <= 75:
            errors.append(f"Título poco útil o ausente: {name}")
        description = head.meta.get("description", [""])[0]
        if not 100 <= len(description) <= 190:
            errors.append(f"Descripción ausente o de longitud irregular: {name}")
        if "noindex" in ",".join(head.meta.get("robots", [])).lower():
            errors.append(f"Página pública marcada noindex: {name}")
        canonical = [x.get("href") for x in head.links if x.get("rel") == "canonical"]
        if len(canonical) != 1:
            errors.append(f"Canonical ausente o duplicado: {name}")
            continue
        uri = canonical[0]
        parts = urlsplit(uri)
        if parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment:
            errors.append(f"Canonical inválido: {name}")
        indexable_urls.append(uri)
        for prop in ("og:title", "og:description", "og:image", "og:url"):
            if not head.meta.get(prop):
                errors.append(f"Meta social {prop} ausente: {name}")
        if head.meta.get("og:url", [None])[0] != uri:
            errors.append(f"og:url distinto del canonical: {name}")
        if not head.meta.get("twitter:card"):
            errors.append(f"Tarjeta Twitter ausente: {name}")
        try:
            data = [json.loads(x) for x in head.jsonld]
            kinds = [node.get("@type") for entry in data for node in entry.get("@graph", [])]
            if "WebSite" not in kinds or graph_type not in kinds:
                errors.append(f"JSON-LD incompleto: {name}")
            if "NewsArticle" in kinds:
                errors.append(f"Noticias de terceros declaradas propias: {name}")
        except (ValueError, TypeError, AttributeError):
            errors.append(f"JSON-LD inválido: {name}")
    if "boletin-diario.html" in pages:
        preview = pages["boletin-diario.html"][1]
        if not any("noindex" in x.lower() for x in preview.meta.get("robots", [])):
            errors.append("La vista previa del boletín debe ser noindex")
    if "404.html" in pages:
        not_found = pages["404.html"][1]
        if not any("noindex" in x.lower() for x in not_found.meta.get("robots", [])):
            errors.append("La página 404 debe ser noindex")
    sitemap = root / "sitemap.xml"
    if not sitemap.is_file():
        errors.append("Falta sitemap.xml")
    else:
        try:
            tree = ET.parse(sitemap)
            namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            indexed = [el.text for el in tree.findall(".//s:loc", namespace)]
            if sorted(indexed) != sorted(indexable_urls):
                errors.append(f"Sitemap difiere de páginas canónicas indexables: {indexed}")
        except ET.ParseError:
            errors.append("Sitemap XML mal formado")
    expected = ("sobre-el-portal.html", "boletin-diario.html")
    for path in expected:
        if f'href="{path}"' not in home_html:
            errors.append(f"Sin enlace interno desde la portada: {path}")
    if 'rel="canonical"' not in home_html:
        errors.append("Falta canonical de portada")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="public")
    args = parser.parse_args()
    issues = inspect_site(args.site)
    if issues:
        for issue in issues:
            print("SEO ERROR:", issue)
        raise SystemExit(1)
    print("SEO válido: canónicas, sitemap, metas sociales, datos estructurados, noindex y enlaces internos.")


if __name__ == "__main__":
    main()
