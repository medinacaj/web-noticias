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

    def test_click_pause_and_mouse_drag(self):
        for marker in ('pointerdown', 'pointermove', 'pointerup',
                       'pressX = event.clientX',
                       'startScroll - delta', 'event.preventDefault()',
                       'paused = !paused', 'dataset.paused', 'setInterval',
                       'scrollTo({left:0', 'scrollBy({left:90'):
            self.assertIn(marker, self.html)

    def test_accessible_motion_preferences_and_keyboard(self):
        for marker in ('prefers-reduced-motion: reduce',
                       'event.key === "Enter"', 'event.key === "ArrowRight"',
                       'aria-label="Carrusel de secciones;',
                       'tabindex="0"', 'touch-action:pan-x'):
            self.assertIn(marker, self.html)

    def test_mobile_menu_is_preserved(self):
        for marker in ('id="menu-toggle"', 'id="site-nav"',
                       'nav.classList.toggle("open", open)',
                       '.js .site-nav.open{display:block;}',
                       'window.innerWidth > 767'):
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
