"""AdSense condicionado: no cargar publicidad sin aprobación y transparencia."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import fetch_noticias as news
from scripts.adsense import configured_adsense


PUB = "ca-pub-1234567890123456"
OWNED_SITE = "https://noticias.example.cl"
PAGES_SITE = "https://medinacaj.github.io/web-noticias"
PRIVACY = "https://noticias.example.cl/privacidad"


class AdsenseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "ADSENSE_PUBLISHER_ID": PUB,
            "ADSENSE_PRIVACY_URL": PRIVACY,
            "ADSENSE_READY": "true",
        }
        self.now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        self.story = {
            "title": "Titular de prueba", "category": "nacional",
            "link": "https://medio.example/nota",
            "sources": ["Medio"],
            "published": self.now.isoformat(),
            "summary": "", "image": "",
        }

    def test_default_has_no_ads_or_tracking_request(self):
        config = configured_adsense({}, PAGES_SITE)
        self.assertFalse(config["enabled"])
        self.assertEqual(config["meta"], "")
        self.assertEqual(config["code"], "")
        self.assertEqual(config["ads_txt"], "")
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {}, clear=True), patch.object(news, "SITE_URL", PAGES_SITE):
                news.build_site([self.story], self.now, directory)
            home = (Path(directory) / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("pagead2.googlesyndication.com", home)
            self.assertNotIn('name="google-adsense-account"', home)
            self.assertFalse((Path(directory) / "ads.txt").exists())
            self.assertNotIn("%%ADSENSE", home)

    def test_valid_id_can_verify_without_loading_script(self):
        config = configured_adsense({"ADSENSE_PUBLISHER_ID": PUB}, PAGES_SITE)
        self.assertIn('name="google-adsense-account"', config["meta"])
        self.assertEqual(config["code"], "")
        self.assertEqual(config["ads_txt"], "")
        self.assertFalse(config["enabled"])

    def test_invalid_or_injected_id_is_rejected(self):
        for bad in ("pub-1234567890123456", "ca-pub-abc", "ca-pub-1234",
                    'ca-pub-1234567890123456"><script>alert(1)</script>',
                    "ca-pub-12345678901234567"):
            settings = configured_adsense({**self.env, "ADSENSE_PUBLISHER_ID": bad}, OWNED_SITE)
            self.assertEqual(settings["meta"], "")
            self.assertFalse(settings["enabled"])
            self.assertEqual(settings["ads_txt"], "")

    def test_no_ads_with_missing_or_unsafe_privacy_link(self):
        for value in ("", "http://example.cl/privacidad",
                      "javascript:alert(1)", "https://user:pass@example.cl"):
            config = configured_adsense({**self.env, "ADSENSE_PRIVACY_URL": value}, OWNED_SITE)
            self.assertFalse(config["enabled"])
            self.assertEqual(config["code"], "")

    def test_project_pages_domain_never_loads_ads(self):
        conf = configured_adsense(self.env, PAGES_SITE)
        self.assertFalse(conf["owned_root"])
        self.assertFalse(conf["enabled"])
        self.assertEqual(conf["code"], "")
        self.assertEqual(conf["ads_txt"], "")

    def test_root_github_pages_can_be_configured_without_buying_domain(self):
        # Un sitio de usuario es un host registrable bajo el sufijo público github.io,
        # distinto de una página de proyecto bajo /web-noticias/.
        root = "https://medinacaj.github.io/"
        candidate = configured_adsense(self.env, root)
        self.assertTrue(candidate["owned_root"])
        self.assertTrue(candidate["enabled"])
        self.assertIn("adsbygoogle.js", candidate["code"])
        self.assertIn("google.com, pub-", candidate["ads_txt"])
        disabled = configured_adsense({**self.env, "ADSENSE_READY": "false"}, root)
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["code"], "")

    def test_not_every_github_subdomain_is_registrable(self):
        for candidate in ("https://github.io/", "https://sub.medinacaj.github.io/",
                          "https://medinacaj.github.io/web-noticias",
                          "https://medinacaj.github.io:9999/"):
            self.assertFalse(configured_adsense(self.env, candidate)["enabled"])

    def test_owned_custom_root_is_opt_in_and_ads_txt_valid(self):
        cfg = configured_adsense({**self.env, "ADSENSE_READY": ""}, OWNED_SITE)
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["code"], "")
        self.assertEqual(cfg["ads_txt"], "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n")
        enabled = configured_adsense(self.env, OWNED_SITE)
        self.assertTrue(enabled["enabled"])
        self.assertEqual(enabled["code"].count("adsbygoogle.js"), 1)
        self.assertIn("crossorigin=\"anonymous\"", enabled["code"])
        self.assertIn("Privacidad y publicidad", enabled["footer"])

    def test_generator_renders_only_with_explicit_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", self.env), patch.object(news, "SITE_URL", OWNED_SITE):
                news.build_site([self.story], self.now, directory)
            home = (Path(directory) / "index.html").read_text(encoding="utf-8")
            self.assertIn('name="google-adsense-account"', home)
            self.assertIn("adsbygoogle.js?client=" + PUB, home)
            self.assertIn('href="' + PRIVACY + '"', home)
            self.assertEqual((Path(directory) / "ads.txt").read_text(encoding="utf-8"),
                             "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n")
            self.assertEqual(home.count("adsbygoogle.js"), 1)

    def test_domain_must_be_root_without_query_or_credentials(self):
        for domain in ("https://noticias.example.cl/seccion", "http://noticias.example.cl",
                       "https://foo.github.io/noticias", "https://github.io/",
                       "https://noticias.example.cl/?q=1",
                       "https://u:p@noticias.example.cl/"):
            self.assertFalse(configured_adsense(self.env, domain)["enabled"])

    def test_no_ad_placeholders_or_fake_cards(self):
        template = Path(news.TEMPLATE_PATH).read_text(encoding="utf-8")
        self.assertIn("%%ADSENSE_META%%", template)
        self.assertIn("%%ADSENSE_CODE%%", template)
        self.assertNotIn("adsbygoogle.js?", template)
        self.assertNotIn('class="ad-placeholder"', template)


if __name__ == "__main__":
    unittest.main()
