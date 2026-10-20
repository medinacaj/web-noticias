"""Newsletter seguro: selección reciente, enlaces, escapado y activación."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.newsletter import newsletter_stories, render_newsletter, safe_external_url
from fetch_noticias import build_site


class NewsletterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)

    def story(self, title="Titular de prueba", link="https://editor.cl/noticia",
              source="Editorial", when=None):
        timestamp = when if when is not None else self.now - timedelta(hours=1)
        return {"title": title, "link": link, "category": "nacional",
                "published": timestamp.isoformat(), "sources": [source],
                "first_seen": timestamp.isoformat(), "summary": "", "image": ""}

    def test_https_only(self):
        self.assertEqual(safe_external_url("https://editor.cl/noticia"), "https://editor.cl/noticia")
        for candidate in ["http://example.org", "javascript:alert(1)",
                          "//example.org", "https://user:pass@example.org", ""]:
            self.assertEqual(safe_external_url(candidate), "")

    def test_recent_unique_selection(self):
        new = self.story()
        repeated = self.story(title="Repetición")
        stale = self.story(title="Antigua", link="https://old.cl/news",
                           when=self.now - timedelta(days=4))
        selection = newsletter_stories([new, repeated, stale], self.now)
        self.assertEqual(len(selection), 1)
        self.assertEqual(selection[0]["title"], "Titular de prueba")

    def test_escapes_external_titles(self):
        record = self.story(title='<script>alert("hello")</script>')
        page = render_newsletter([record], self.now, "https://example.org")
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertIn("vista previa pública", page)
        self.assertIn("Suscripciones próximamente", page)

    def test_no_news_is_honest(self):
        page = render_newsletter([], self.now, "https://example.org")
        self.assertIn("No hay noticias suficientes", page)
        self.assertNotIn("Suscribirme al boletín", page)

    def test_configured_external_signup_is_link_not_form(self):
        page = render_newsletter([self.story()], self.now, "https://example.org",
                                 "https://example.org/subscribe", "https://example.org/unsubscribe")
        self.assertIn("Suscribirme al boletín", page)
        self.assertIn("https://example.org/unsubscribe", page)
        self.assertNotIn("<form", page)

    def test_build_site_has_preview_and_disabled_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"NEWSLETTER_READY": "",
                                           "NEWSLETTER_SUBSCRIBE_URL": "https://example.org/subscribe",
                                           "NEWSLETTER_PRIVACY_URL": "https://example.org/privacy",
                                           "NEWSLETTER_UNSUBSCRIBE_URL": "https://example.org/unsubscribe"}):
                build_site([self.story()], self.now, tmp)
            page = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            preview = (Path(tmp) / "boletin-diario.html").read_text(encoding="utf-8")
            self.assertIn('href="boletin-diario.html"', page)
            self.assertIn("Suscripciones próximamente", page)
            self.assertNotIn('class="newsletter-link"', page)
            self.assertIn("Titular de prueba", preview)

    def test_ready_requires_all_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"NEWSLETTER_READY": "true",
                                           "NEWSLETTER_SUBSCRIBE_URL": "https://example.org/subscribe",
                                           "NEWSLETTER_PRIVACY_URL": "",
                                           "NEWSLETTER_UNSUBSCRIBE_URL": "https://example.org/unsubscribe"}):
                build_site([self.story()], self.now, tmp)
            page = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            self.assertIn("Suscripciones próximamente", page)
            self.assertNotIn('class="newsletter-link"', page)


if __name__ == "__main__":
    unittest.main()
