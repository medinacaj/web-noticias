"""Regresiones de miniaturas editoriales (sin peticiones a la red)."""
import unittest
from datetime import datetime, timezone

from fetch_noticias import source_domain, source_mark, meta_html, merge, figure_html, render_sections


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

    def test_badge_over_image_keeps_original_image_and_logo(self):
        story = {"image": "https://example.com/photo.jpg",
                 "source_url": "https://medio.cl", "sources": ["Medio"]}
        rendered = figure_html(story)
        self.assertIn('class="media-badge"', rendered)
        self.assertIn('class="source-mark"', rendered)
        self.assertIn("photo.jpg", rendered)
        self.assertIn("medio.cl", rendered)
        self.assertLess(rendered.index("photo.jpg"), rendered.index('class="media-badge"'))

    def test_missing_photo_displays_publisher_thumbnail(self):
        rendered = figure_html({"image": "", "sources": ["Medio"],
                                "source_url": "https://medio.cl"})
        self.assertIn('class="media media--source"', rendered)
        self.assertIn('class="source-visual"', rendered)
        self.assertIn("medio.cl", rendered)
        self.assertNotIn('class="media-badge"', rendered)

    def test_no_domain_still_has_visible_monogram(self):
        rendered = figure_html({"image": "", "sources": ["Medio"],
                                "link": "https://news.google.com/rss/articles/abc"})
        self.assertIn('class="source-initial">M', rendered)
        self.assertIn("Medio", rendered)

    def test_publisher_name_is_escaped_in_image_placeholder(self):
        rendered = figure_html({"image": "", "sources": ['<bad attr="x">']})
        self.assertNotIn("<bad", rendered)
        self.assertIn("&lt;bad", rendered)

    def test_section_uses_compact_media_for_all_six_stories(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        stories = [
            {"category": "nacional", "title": f"Noticia de prueba número {i}",
             "sources": ["Medio"], "source_url": "https://medio.cl",
             "image": "", "link": f"https://medio.cl/{i}",
             "published": "2026-10-20T00:00:00Z", "summary": ""}
            for i in range(6)
        ]
        rendered = render_sections({"nacional": stories}, now)
        self.assertEqual(rendered.count('class="media media--source"'), 6)
        self.assertEqual(rendered.count('class="news-body"'), 6)
        self.assertEqual(rendered.count('class="compact"'), 5)
        self.assertEqual(rendered.count('class="feature"'), 1)

    def test_merge_preserves_editorial_url(self):
        now = datetime(2026, 10, 19, tzinfo=timezone.utc)
        stories = []
        merge(stories, [{"category": "nacional", "title": "Titular único verificado",
                        "link": "https://news.google.com/rss/articles/abc",
                        "source": "Mi Medio", "source_url": "https://mimedio.cl"}], now)
        self.assertEqual(stories[0]["source_url"], "https://mimedio.cl")


if __name__ == "__main__":
    unittest.main()
