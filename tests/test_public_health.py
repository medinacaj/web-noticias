"""Pruebas sin red del monitor de GitHub Pages."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.check_news_site import assess, DEFAULT_SITE, MAX_AGE_HOURS


class PublicHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        self.sitemap = (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{DEFAULT_SITE}</loc></url></urlset>'
        )

    def page(self, hours=1):
        timestamp = (self.now - timedelta(hours=hours)).isoformat()
        return ('<!doctype html><html><head><title>Noticias del Momento</title></head>'
                '<body><time id="updated-at" datetime="' + timestamp
                + '">Actualizado</time></body></html>')

    def test_healthy(self):
        self.assertEqual(assess(self.page(), self.sitemap, self.now), [])

    def test_stale_publication(self):
        warnings = assess(self.page(MAX_AGE_HOURS + 1), self.sitemap, self.now)
        self.assertTrue(any("desactualizada" in x for x in warnings))

    def test_missing_timestamp_and_title(self):
        warnings = assess("<html><body>Fuera de servicio</body></html>", self.sitemap, self.now)
        self.assertEqual(len(warnings), 2)

    def test_bad_sitemap_or_failed_deployment(self):
        warnings = assess(self.page(), "<wrong/>", self.now, deployment="failure")
        self.assertTrue(any("despliegue" in x for x in warnings))
        self.assertTrue(any("sitemap" in x for x in warnings))

    def test_monitor_is_separate_and_least_privileged(self):
        workflow = Path(".github/workflows/monitor.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("Vigilar Web Noticias publicado", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("secrets.GNEWS_API_KEY", workflow)


if __name__ == "__main__":
    unittest.main()
