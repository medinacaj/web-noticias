"""Contratos de navegación desplazable y composición editorial."""
from pathlib import Path
import unittest

from fetch_noticias import TEMPLATE_PATH, CATEGORIES


class NavigationPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_old_controls_removed(self):
        for marker in ('id="nav-prev"', 'id="nav-next"', 'id="nav-pause"',
                       'class="nav-controls"'):
            self.assertNotIn(marker, self.html)

    def test_navigation_is_static_and_has_no_duplicated_automatic_track(self):
        self.assertNotIn('requestAnimationFrame(animate)', self.html)
        self.assertNotIn('clone.setAttribute("aria-hidden", "true")', self.html)
        self.assertNotIn('Carrusel de secciones;', self.html)
        self.assertIn('aria-label="Secciones de noticias"', self.html)

    def test_compact_header_has_one_brand_and_no_long_claim(self):
        self.assertEqual(self.html.count('<h1'), 1)
        self.assertIn('class="brand-logo"', self.html)
        self.assertNotIn('Lo más relevante de Chile y el mundo, actualizado cada hora', self.html)

    def test_mobile_and_desktop_share_the_section_navigation(self):
        self.assertEqual(self.html.count('id="site-nav"'), 1)
        self.assertIn('aria-controls="site-nav"', self.html)
        self.assertIn('.js .site-nav.open{display:block;}', self.html)
        self.assertIn('id="nav-backdrop"', self.html)
        self.assertIn('@media (min-width:1024px)', self.html)

    def test_category_palette_and_news_functions_remain(self):
        self.assertGreaterEqual(len(CATEGORIES), 10)
        for marker in ('%%NAV%%', '%%SECTIONS%%', '%%TOP%%',
                       'data-show-more', 'var(--cat', 'class="search-results"'):
            self.assertIn(marker, self.html)

    def test_visual_polish_preserves_responsive_rules(self):
        for marker in ('box-shadow:var(--card-shadow-hover)', '.site-nav a.is-active',
                       '@media (max-width:767px)', 'scroll-behavior:auto !important',
                       'color-mix(in srgb,var(--cat'):
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
