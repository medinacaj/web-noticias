"""Regresiones SEO: indexación, contenido real, canónicas y datos estructurados."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fetch_noticias as news
from scripts.audit_seo import inspect_site, HeadInspector
from scripts.seo_pages import render_about_page, render_sitemap


class TechnicalSEOTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
        self.site = "https://medinacaj.github.io/web-noticias"
        self.story = {
            "category": "nacional", "title": "Información de prueba procedente de un medio",
            "sources": ["Un Medio"], "source_url": "https://medio.example",
            "link": "https://medio.example/noticia-original",
            "published": "2026-10-20T09:00:00Z",
            "first_seen": "2026-10-20T09:00:00Z",
            "summary": "Un breve extracto informativo publicado por la fuente.",
            "image": "https://medio.example/imagen.jpg",
        }

    def test_about_page_is_factual_indexable_and_not_news_article(self):
        html = render_about_page(self.site)
        head = HeadInspector()
        head.feed(html)
        self.assertEqual(head.meta["robots"][0], "index, follow, max-image-preview:large")
        self.assertIn('href="https://medinacaj.github.io/web-noticias/sobre-el-portal.html"', html)
        self.assertIn("ni verifica independientemente", html)
        self.assertIn("no son artículos escritos por este portal", html)
        self.assertNotIn('"@type": "NewsArticle"', html)
        self.assertIn('href="https://medinacaj.github.io/web-noticias/"', html)

    def test_sitemap_only_contains_owned_indexable_pages(self):
        data = render_sitemap(self.site, "2026-10-20T10:00:00Z")
        tree = ET.fromstring(data)
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        urls = [node.text for node in tree.iter(ns + "loc")]
        self.assertEqual(urls, [self.site + "/", self.site + "/sobre-el-portal.html"])
        self.assertNotIn("boletin-diario", data)
        self.assertNotIn("medio.example", data)

    def test_sitemap_xml_escapes_special_characters(self):
        site = "https://example.com/path?foo=1&bar=2"
        data = render_sitemap(site, "2026-10-20T10:00:00Z")
        ET.fromstring(data)
        self.assertIn("&amp;", data)

    def test_offline_audit_of_full_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(news, "SITE_URL", self.site), patch.dict("os.environ", {
                "NEWSLETTER_READY": "",
            }):
                news.build_site([self.story], self.now, tmp)
            issues = inspect_site(tmp)
            self.assertEqual(issues, [])
            index = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            about = (Path(tmp) / "sobre-el-portal.html").read_text(encoding="utf-8")
            self.assertIn('href="sobre-el-portal.html"', index)
            self.assertIn('href="boletin-diario.html"', index)
            self.assertIn('href="https://medinacaj.github.io/web-noticias/"', about)
            self.assertIn('class="masthead-title"', index)
            self.assertIn('fetchpriority="high"', index)
            self.assertIn('decoding="async"', index)
            self.assertNotIn('"@type": "NewsArticle"', index)

    def test_audit_detects_wrong_canonical_in_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(news, "SITE_URL", self.site):
                news.build_site([self.story], self.now, tmp)
            sitemap = Path(tmp) / "sitemap.xml"
            sitemap.write_text(sitemap.read_text(encoding="utf-8").replace(
                self.site + "/sobre-el-portal.html", self.site + "/otra.html"
            ), encoding="utf-8")
            self.assertTrue(any("Sitemap difiere" in error for error in inspect_site(tmp)))

    def test_about_metadata_matches_actual_page_and_description(self):
        about = render_about_page(self.site)
        self.assertIn("<h1>Sobre Noticias del Momento</h1>", about)
        self.assertIn('<meta name="description"', about)
        self.assertIn('property="og:url" content="' + self.site + '/sobre-el-portal.html"', about)
        self.assertIn('type="application/ld+json"', about)
        self.assertIn('"@type": "AboutPage"', about)

    def test_no_new_tracker_or_fake_contact_in_about(self):
        page = render_about_page(self.site)
        self.assertNotIn("google-analytics", page)
        self.assertNotIn("mailto:", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("suscríbete aquí", page.lower())


if __name__ == "__main__":
    unittest.main()
