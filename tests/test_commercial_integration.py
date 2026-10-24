"""Build output enforces the same commercial gates on every public page."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_noticias as news


class CommercialIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
        self.story = {"title": "Noticia de prueba para el portal", "category": "nacional",
                      "link": "https://medio.example/noticia", "sources": ["Medio"],
                      "published": self.now.isoformat(), "first_seen": self.now.isoformat(),
                      "summary": "", "image": ""}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.publisher = "ca-pub-8231746902358174"  # Fixture, never deployment configuration.
        self.ads = {"ADSENSE_PUBLISHER_ID": self.publisher, "ADSENSE_READY": "true",
                    "ADSENSE_ROOT_CONTROLLED": "true",
                    "ADSENSE_PRIVACY_URL": "https://editor.example/privacy"}
        self.signup = {"NEWSLETTER_READY": "true", "NEWSLETTER_PROVIDER": "Proveedor de prueba",
                       "NEWSLETTER_SUBSCRIBE_URL": "https://editor.example/subscribe",
                       "NEWSLETTER_PRIVACY_URL": "https://editor.example/privacy",
                       "NEWSLETTER_UNSUBSCRIBE_URL": "https://editor.example/unsubscribe"}

    def build(self, env=None, site="https://medinacaj.github.io/web-noticias"):
        with patch.dict("os.environ", env or {}, clear=True), patch.object(news, "SITE_URL", site):
            news.build_site([self.story], self.now, self.temp.name)
        return ((self.output / "index.html").read_text(),
                (self.output / "boletin-diario.html").read_text())

    def test_default_build_is_public_preview_without_ads_or_signup(self):
        home, preview = self.build()
        for page in (home, preview):
            self.assertIn("Suscripciones próximamente", page)
            self.assertNotIn('href="https://editor.example/subscribe"', page)
            self.assertNotIn("adsbygoogle.js", page)
            self.assertNotIn("google-adsense-account", page)
            self.assertNotRegex(page, r"%%[A-Z_]+%%")
        self.assertIn("Noticia de prueba", home)
        self.assertIn("Noticia de prueba", preview)
        self.assertFalse((self.output / "ads.txt").exists())

    def test_partial_newsletter_never_publishes_signup_on_either_page(self):
        for missing in self.signup:
            with self.subTest(missing=missing):
                env = dict(self.signup)
                env.pop(missing)
                home, preview = self.build(env)
                for page in (home, preview):
                    self.assertIn("Suscripciones próximamente", page)
                    self.assertNotIn('href="https://editor.example/subscribe"', page)

    def test_complete_newsletter_links_signup_privacy_and_cancel_consistently(self):
        home, preview = self.build(self.signup)
        for page in (home, preview):
            self.assertIn('href="https://editor.example/subscribe"', page)
            self.assertIn('href="https://editor.example/privacy"', page)
            self.assertNotIn("Suscripciones próximamente", page)
            self.assertNotIn("<form", page)
            self.assertNotIn("adsbygoogle.js", page)
        self.assertIn('href="https://editor.example/unsubscribe"', preview)
        self.assertIn("no representa un correo enviado", preview)

    def test_id_verifies_current_project_without_activating_ads(self):
        home, preview = self.build(self.ads)
        self.assertIn('name="google-adsense-account"', home)
        self.assertIn(self.publisher, home)
        self.assertNotIn("adsbygoogle.js", home)
        self.assertNotIn("google-adsense-account", preview)
        self.assertFalse((self.output / "ads.txt").exists())

    def test_root_ads_require_every_gate_and_only_load_once_on_homepage(self):
        for missing in self.ads:
            with self.subTest(missing=missing):
                env = dict(self.ads)
                env.pop(missing)
                home, _ = self.build(env, site="https://editor.cl")
                self.assertNotIn("adsbygoogle.js", home)
        home, preview = self.build(self.ads, site="https://editor.cl")
        self.assertEqual(home.count("adsbygoogle.js?client=" + self.publisher), 1)
        self.assertIn('href="https://editor.example/privacy"', home)
        self.assertIn("adsbygoogle.js", home.split("</head>", 1)[0])
        for name in ("boletin-diario.html", "sobre-el-portal.html", "404.html"):
            self.assertNotIn("adsbygoogle.js", (self.output / name).read_text())
        self.assertEqual((self.output / "ads.txt").read_text(),
                         "google.com, pub-8231746902358174, DIRECT, f08c47fec0942fa0\n")

    def test_disabled_or_project_build_removes_previous_root_ads_txt(self):
        for env in ({}, self.ads):
            with self.subTest(env=bool(env)):
                (self.output / "ads.txt").write_text("stale publisher authorization\n")
                self.build(env)
                self.assertFalse((self.output / "ads.txt").exists())


if __name__ == "__main__":
    unittest.main()
