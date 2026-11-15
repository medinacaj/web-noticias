import unittest
from datetime import datetime, timezone

from fetch_noticias import safe_article_url, title_link, render_coverage_radar, merge


class SafeArticleLinksTest(unittest.TestCase):
    def test_rejects_unsafe_schemes_and_malformed_hosts(self):
        invalid = [
            "javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
            "vbscript:alert(1)", "file:///tmp/test", "//example.org/article",
            "https://user:pass@example.org/article", "https:///missing-host",
            "https://example.org/article\nother", "https://example.org/\\evil",
            "https://example.org:invalid/article", 25, None,
        ]
        for value in invalid:
            with self.subTest(value=value):
                self.assertEqual(safe_article_url(value), "")

    def test_http_https_articles_keep_their_real_destinations(self):
        for value in [
            "https://example.org/nota?ref=abc#comentarios",
            "http://example.org/nota-antigua",
            "https://noticias.example.org/ruta%20con%20espacios",
        ]:
            with self.subTest(url=value):
                self.assertEqual(safe_article_url(value), value)

    def test_old_unsafe_history_entry_cannot_render_executable_link(self):
        story = {
            "title": "<Titular de prueba>",
            "category": "nacional",
            "link": "javascript:alert(1)",
            "source": "Medio demo",
            "sources": ["Medio demo"],
        }
        rendered = title_link(story)
        self.assertNotIn("href=", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("&lt;Titular de prueba&gt;", rendered)
        story["link"] = "https://example.org/noticia"
        self.assertIn('href="https://example.org/noticia"', title_link(story))

    def test_collector_does_not_merge_a_malicious_url(self):
        now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        stories = []
        sample = {
            "title": "Un titular de prueba", "source": "Medio demo",
            "category": "nacional", "link": "javascript:alert(1)",
            "published": now.isoformat(),
        }
        added = merge(stories, [sample], now)
        self.assertEqual(added, 0)
        self.assertEqual(stories, [])

    def test_radar_does_not_link_to_an_invalid_historical_url(self):
        story = {
            "title": "Una noticia de prueba",
            "category": "nacional",
            "sources": ["A", "B", "C", "D"],
            "link": "javascript:alert(1)",
        }
        self.assertEqual(render_coverage_radar([story]), "")


if __name__ == "__main__":
    unittest.main()
