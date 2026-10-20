"""Regresiones de miniaturas editoriales (sin peticiones a la red)."""
import unittest
from datetime import datetime, timezone

from fetch_noticias import source_domain, source_mark, meta_html, merge


class SourceFaviconsTests(unittest.TestCase):
    def test_google_news_uses_editorial_source_not_google(self):
        self.assertEqual(
            source_domain("https://www.biobiochile.cl/", "https://news.google.com/rss/articles/abc"),
            "www.biobiochile.cl",
        )
        self.assertEqual(source_domain("", "https://news.google.com/rss/articles/abc"), "")

    def test_rejects_unsafe_domain(self):
        for value in ("javascript:alert(1)", "http://example.com", "https://evil.com@news.google.com/"):
            self.assertEqual(source_domain(value), "")

    def test_mark_contains_favicon_and_fallback(self):
        mark = source_mark({"sources": ["Diario Ejemplo"], "source_url": "https://diario.example/"})
        self.assertIn("google.com/s2/favicons?", mark)
        self.assertIn("diario.example", mark)
        self.assertIn('class="source-initial">D', mark)
        self.assertIn('onerror="this.hidden=true"', mark)

    def test_google_only_has_monogram(self):
        mark = source_mark({"sources": ["Fuente"], "link": "https://news.google.com/rss/articles/abc"})
        self.assertNotIn("<img", mark)
        self.assertIn('class="source-initial">F', mark)

    def test_meta_shows_source_and_time(self):
        now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        story = {"sources": ["Ejemplo"], "source_url": "https://example.com",
                 "published": "2026-10-19T00:00:00Z", "link": "https://example.com/a"}
        html = meta_html(story, now)
        self.assertIn('class="source-mark"', html)
        self.assertIn('class="source-name">Ejemplo', html)
        self.assertIn("<time", html)

    def test_merge_preserves_editorial_url(self):
        now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        stories = []
        merge(stories, [{"category": "nacional", "title": "Titular único verificado",
                        "link": "https://news.google.com/rss/articles/abc",
                        "source": "Mi Medio", "source_url": "https://mimedio.cl"}], now)
        self.assertEqual(stories[0]["source_url"], "https://mimedio.cl")


if __name__ == "__main__":
    unittest.main()
