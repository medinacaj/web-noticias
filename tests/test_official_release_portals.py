"""Fuentes oficiales visibles sin confundir páginas corporativas con estrenos."""
from datetime import datetime, timezone
import unittest
from urllib.parse import urlsplit

import fetch_noticias as news
from scripts.official_release_portals import official_portals, render_official_portals

NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def guide():
    return {
        "title": "Estrenos Netflix del 26 al 30 de octubre de 2026",
        "source": "Cine PREMIERE", "source_url": "https://cinepremiere.com.mx",
        "link": "https://cinepremiere.com.mx/estrenos/semana",
        "published": "2026-10-26T07:00:00Z",
    }


class OfficialReleasePortalsTests(unittest.TestCase):
    def test_portals_cover_five_platforms_and_have_safe_official_urls(self):
        portals = official_portals()
        self.assertEqual({p["brand"] for p in portals},
                         {"Netflix", "HBO Max", "Prime Video", "Disney+", "Mega / MegaGo"})
        self.assertEqual(len(portals), 7)
        hosts = {
            "Netflix": "about.netflix.com",
            "HBO Max": "press.wbd.com",
            "Prime Video": "www.aboutamazon.com",
            "Disney+": "press.disneyplus.com",
            "Mega / MegaGo": "www.mega.cl",
        }
        for portal in portals:
            with self.subTest(portal=portal["label"]):
                url = urlsplit(portal["url"])
                self.assertEqual(url.scheme, "https")
                self.assertEqual(url.hostname, hosts[portal["brand"]])
                self.assertTrue(portal["discovery_only"])
                self.assertFalse(url.username or url.password)

    def test_render_is_a_small_accessible_source_directory(self):
        rendered = render_official_portals()
        self.assertIn('aria-label="Fuentes oficiales de estrenos"', rendered)
        self.assertIn("Portales oficiales", rendered)
        self.assertIn("no garantizan un estreno en Chile", rendered)
        self.assertEqual(rendered.count('<a href="'), 7)
        self.assertEqual(rendered.count('rel="noopener noreferrer"'), 7)
        self.assertNotIn('target="_blank"', rendered)
        self.assertNotIn('<article', rendered)
        self.assertNotIn('<time ', rendered)

    def test_guides_are_preserved_and_official_links_are_not_news_cards(self):
        html = news.render_sections({}, NOW, release_guides=[guide()])
        self.assertIn("Estrenos Netflix del 26 al 30", html)
        self.assertIn('data-content-kind="guide"', html)
        self.assertIn("Guía publicada", html)
        self.assertIn("Fuentes oficiales de estrenos", html)
        self.assertIn("www.mega.cl/temas/megashorts/", html)
        self.assertEqual(html.count('data-content-kind="guide"'), 2)
        self.assertEqual(html.count('class="official-release-portals"'), 1)
        self.assertEqual(news.render_sections({}, NOW), "")


if __name__ == "__main__":
    unittest.main()
