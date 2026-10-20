"""Contratos de navegación desplazable y composición editorial."""
from pathlib import Path
import unittest

from fetch_noticias import TEMPLATE_PATH, CATEGORIES


class NavigationPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_manual_controls_have_accessible_names(self):
        for marker in ('id="nav-prev"', 'id="nav-next"', 'id="nav-pause"',
                       'aria-label="Secciones anteriores"',
                       'aria-label="Secciones siguientes"',
                       'aria-label="Pausar desplazamiento automático"'):
            self.assertIn(marker, self.html)

    def test_scroll_has_keyboard_and_hover_pause(self):
        for marker in ('strip.addEventListener("mouseenter"',
                       'strip.addEventListener("focusin"',
                       'strip.addEventListener("pointerdown"',
                       'strip.scrollBy({left: sign',
                       'strip.scrollWidth > strip.clientWidth',
                       'manualPaused', 'window.matchMedia',
                       'prefers-reduced-motion: reduce'):
            self.assertIn(marker, self.html)

    def test_mobile_menu_is_preserved(self):
        for marker in ('id="menu-toggle"', 'id="site-nav"',
                       'nav.classList.toggle("open", open)',
                       '.js .site-nav.open{display:block;}',
                       '.nav-controls,.js .nav-controls{display:none;}'):
            self.assertIn(marker, self.html)

    def test_category_palette_and_news_functions_remain(self):
        self.assertGreaterEqual(len(CATEGORIES), 10)
        for marker in ('%%NAV%%', '%%SECTIONS%%', '%%TOP%%',
                       'data-show-more', 'var(--cat', 'class="search-results"'):
            self.assertIn(marker, self.html)

    def test_visual_polish_preserves_responsive_rules(self):
        for marker in ('box-shadow:0 7px 20px', '.site-nav a.is-active',
                       '@media (max-width:767px)', 'scroll-behavior:auto !important',
                       'color-mix(in srgb,var(--cat'):
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
