"""Publicidad opcional: verificar propiedad no autoriza carga de terceros."""
import unittest
from unittest.mock import patch

try:
    from scripts.adsense import configured_adsense
except ModuleNotFoundError:
    configured_adsense = None


class AdsenseTests(unittest.TestCase):
    def config(self, env=None, site="https://medinacaj.github.io/"):
        self.assertTrue(callable(configured_adsense), "Falta configuración AdSense fail-closed")
        return configured_adsense(env, site)

    def setUp(self):
        # Identificador de fixture, nunca configuración de publicación.
        self.publisher = "ca-pub-8231746902358174"
        self.env = {"ADSENSE_PUBLISHER_ID": self.publisher,
                    "ADSENSE_READY": "true",
                    "ADSENSE_ROOT_CONTROLLED": "true",
                    "ADSENSE_PRIVACY_URL": "https://editor.example/privacy"}

    def test_default_omits_all_advertising_artifacts(self):
        config = self.config({})
        self.assertFalse(config["enabled"])
        for key in ("meta", "script", "footer", "ads_txt"):
            self.assertEqual(config[key], "")

    def test_id_alone_can_verify_but_never_load_ads(self):
        config = self.config({"ADSENSE_PUBLISHER_ID": self.publisher})
        self.assertIn('name="google-adsense-account"', config["meta"])
        self.assertIn(self.publisher, config["meta"])
        self.assertEqual(config["script"], "")
        self.assertEqual(config["ads_txt"], "")

    def test_explicit_complete_root_configuration_uses_official_code(self):
        config = self.config(self.env)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["script"],
                         '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
                         'adsbygoogle.js?client=ca-pub-8231746902358174" crossorigin="anonymous"></script>')
        self.assertEqual(config["ads_txt"],
                         "google.com, pub-8231746902358174, DIRECT, f08c47fec0942fa0\n")
        self.assertIn('href="https://editor.example/privacy"', config["footer"])

    def test_every_gate_is_required_for_ads(self):
        for key in self.env:
            with self.subTest(missing=key):
                env = dict(self.env)
                env.pop(key)
                self.assertFalse(self.config(env)["enabled"])

    def test_project_path_never_authorizes_host_root_even_with_ready(self):
        config = self.config(self.env, "https://medinacaj.github.io/web-noticias/")
        self.assertFalse(config["enabled"])
        self.assertEqual(config["ads_txt"], "")
        self.assertEqual(config["script"], "")

    def test_malformed_nonpublic_or_nonroot_site_fails_closed(self):
        for site in ("https://localhost", "https://intranet", "https://127.0.0.1",
                     "https://[::1]", "https://[broken", "http://editor.cl",
                     "https://github.io", "https://a.b.github.io", "https://editor.cl/path",
                     "https://editor.cl/?q=1", "https://editor.cl/#frag", "https://editor.cl:443/",
                     "https://user:pass@editor.cl", "https://editor.cl\\@evil.cl",
                     "https://editor.cl\n/"):
            with self.subTest(site=site):
                config = self.config(self.env, site)
                self.assertFalse(config["enabled"])
                self.assertEqual(config["ads_txt"], "")

    def test_rejects_invalid_or_documentation_publisher_ids(self):
        for publisher in ("", "ca-pub-123", "pub-8231746902358174", "ca-pub-" + "0" * 16,
                          "ca-pub-1234567890123456", 'ca-pub-8231746902358174\"><script>',
                          "ca-pub-８２３１７４６９０２３５８１７４"):
            with self.subTest(publisher=publisher):
                env = dict(self.env, ADSENSE_PUBLISHER_ID=publisher)
                config = self.config(env)
                self.assertFalse(config["enabled"])
                self.assertEqual(config["meta"], "")
                self.assertEqual(config["ads_txt"], "")

    def test_invalid_privacy_does_not_load_ads_or_publish_privacy_link(self):
        for privacy in ("", "http://editor.cl/privacy", "javascript:alert(1)", "https://[broken"):
            with self.subTest(privacy=privacy):
                config = self.config(dict(self.env, ADSENSE_PRIVACY_URL=privacy))
                self.assertFalse(config["enabled"])
                self.assertEqual(config["footer"], "")

    def test_privacy_link_escapes_attribute_values(self):
        config = self.config(dict(self.env, ADSENSE_PRIVACY_URL='https://editor.example/privacy?q="hello"&a=1'))
        self.assertIn("&quot;hello&quot;&amp;a=1", config["footer"])

    def test_only_true_flag_enables_ads(self):
        for value in ("1", "yes", "false", ""):
            with self.subTest(flag=value):
                self.assertFalse(self.config(dict(self.env, ADSENSE_READY=value))["enabled"])

    def test_environment_fallback_is_explicit_and_mapping_is_not_mutated(self):
        with patch.dict("os.environ", self.env, clear=True):
            self.assertTrue(self.config()["enabled"])
            self.assertFalse(self.config({})["enabled"])
        before = dict(self.env)
        self.config(self.env)
        self.assertEqual(self.env, before)


if __name__ == "__main__":
    unittest.main()
