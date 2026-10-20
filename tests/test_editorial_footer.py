"""Pie editorial compacto: destinos reales, atribución y responsive."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fetch_noticias import TEMPLATE_PATH, build_site


class EditorialFooterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_compact_editorial_footer_uses_real_links(self):
        footer = self.template.split('<footer class="site-footer"', 1)[1].split("</footer>", 1)[0]
        for marker in (
            'href="#contenido"', 'href="#categorias"',
            'href="boletin-diario.html"', 'aria-label="Enlaces útiles"',
            'id="footer-about-title"', '%%UPDATED_HUMAN%%', '%%YEAR%%',
        ):
            self.assertIn(marker, footer)
        self.assertNotIn("%%FOOTER_NAV%%", footer)
        self.assertNotIn("NEWSLETTER_SUBSCRIBE_URL", footer)
        self.assertIn('id="categorias"', self.template)
        self.assertEqual(self.template.count('id="categorias"'), 1)

    def test_source_attribution_is_true_and_brief(self):
        footer = self.template.split('<footer class="site-footer"', 1)[1].split("</footer>", 1)[0]
        self.assertIn("Recopilamos automáticamente", footer)
        self.assertIn("sus respectivos medios de origen", footer)
        self.assertNotIn("Los titulares se recopilan automáticamente desde Google Noticias y GNews.", footer)
        self.assertNotIn("© %%YEAR%% Noticias del Momento · Última", footer)

    def test_footer_has_lighter_geometry_and_responsive_layout(self):
        for token in (
            ".site-footer{background:var(--navy-dark);color:var(--on-navy-soft);margin-top:0;padding:32px 0 18px",
            ".footer-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));",
            ".footer-nav a:focus-visible{outline:2px solid var(--on-navy)",
            "@media (max-width:540px)",
            ".footer-nav ul{grid-template-columns:repeat(2,minmax(0,1fr));",
            ".footer-bottom{margin-top:24px;",
        ):
            self.assertIn(token, self.template)
        self.assertNotIn("margin-top:80px;padding:52px 0 28px", self.template)

    def test_produced_newsletter_destination_exists(self):
        story = {
            "category": "nacional", "title": "Noticia para probar el pie",
            "link": "https://example.org/nota", "sources": ["Medio de prueba"],
            "published": "2026-10-20T07:00:00Z", "summary": "",
            "image": "",
        }
        now = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            build_site([story], now, directory)
            page = (Path(directory) / "index.html").read_text(encoding="utf-8")
            self.assertTrue((Path(directory) / "boletin-diario.html").is_file())
            self.assertIn('href="#categorias"', page)
            self.assertIn('id="categorias"', page)
            self.assertIn("© 2026 Noticias del Momento", page)
            self.assertNotIn("%%FOOTER_NAV%%", page)
            self.assertNotIn("%%UPDATED_HUMAN%%", page)


if __name__ == "__main__":
    unittest.main()
