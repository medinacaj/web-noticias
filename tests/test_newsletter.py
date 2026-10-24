"""Newsletter seguro: selección reciente, enlaces, escapado y activación."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.newsletter import newsletter_stories, render_newsletter, safe_external_url
from scripts import newsletter
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

    def configured(self, env):
        configure = getattr(newsletter, "configured_newsletter", None)
        self.assertTrue(callable(configure), "Falta gate central de newsletter")
        return configure(env)

    def complete_env(self):
        return {"NEWSLETTER_READY": "true", "NEWSLETTER_PROVIDER": "Proveedor contratado",
                "NEWSLETTER_SUBSCRIBE_URL": "https://editor.example/subscribe",
                "NEWSLETTER_PRIVACY_URL": "https://editor.example/privacy",
                "NEWSLETTER_UNSUBSCRIBE_URL": "https://editor.example/unsubscribe"}

    def test_urls_alone_never_activate_preview_signup(self):
        page = render_newsletter([self.story()], self.now, "https://example.org",
                                 "https://example.org/subscribe", "https://example.org/unsubscribe")
        self.assertNotIn("Suscribirme al boletín", page)
        self.assertIn("Suscripciones próximamente", page)

    def test_configured_external_signup_is_link_not_form(self):
        config = self.configured(self.complete_env())
        page = render_newsletter([self.story()], self.now, "https://example.org", configuration=config)
        self.assertIn("Suscribirme al boletín", page)
        self.assertIn("https://editor.example/unsubscribe", page)
        self.assertIn("https://editor.example/privacy", page)
        self.assertNotIn("<form", page)

    def test_newsletter_requires_provider_and_each_url_and_ready(self):
        for key in self.complete_env():
            with self.subTest(missing=key):
                env = self.complete_env()
                env.pop(key)
                config = self.configured(env)
                self.assertFalse(config["enabled"])
                self.assertEqual(config["subscribe_url"], "")
                self.assertNotIn('class="newsletter-link"', config["signup_html"])
                self.assertIn("Suscripciones próximamente", config["signup_html"])

    def test_signup_fragment_escapes_urls_and_provider_stays_internal(self):
        env = self.complete_env()
        env["NEWSLETTER_SUBSCRIBE_URL"] += '?q="text"&a=1'
        config = self.configured(env)
        self.assertTrue(config["enabled"])
        self.assertIn("&quot;text&quot;&amp;a=1", config["signup_html"])
        self.assertNotIn("Proveedor contratado", config["signup_html"])

    def test_newsletter_environment_fallback_respects_empty_mapping(self):
        with patch.dict("os.environ", self.complete_env(), clear=True):
            self.assertTrue(newsletter.configured_newsletter()["enabled"])
            self.assertFalse(self.configured({})["enabled"])

    def test_malformed_url_is_rejected_instead_of_crashing(self):
        for candidate in ("https://[broken", "https://example.org:bad/privacy", "https://example.org\n/privacy",
                          "https://example.org\\@evil.org", "https://", "https://user@example.org"):
            with self.subTest(candidate=candidate):
                self.assertEqual(safe_external_url(candidate), "")

    def test_unsafe_newsletter_url_disables_all_signup_links(self):
        for key in ("NEWSLETTER_SUBSCRIBE_URL", "NEWSLETTER_PRIVACY_URL", "NEWSLETTER_UNSUBSCRIBE_URL"):
            with self.subTest(key=key):
                env = self.complete_env()
                env[key] = "https://[broken"
                self.assertFalse(self.configured(env)["enabled"])

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
