"""Evita una fila vacía encima de las noticias y conserva ajustes accesibles."""
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH


class TopViewOptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_controls_stay_in_top_bar_not_main(self):
        nav = self.page.split('<div class="sticky-bar">', 1)[1].split('<div class="search-panel"', 1)[0]
        main = self.page.split('<main id="contenido" class="container">', 1)[1].split('%%TOP%%', 1)[0]
        self.assertIn('id="view-options-toggle"', nav)
        self.assertIn('id="view-options-panel" hidden', nav)
        self.assertIn('id="text-size"', nav)
        self.assertIn('id="density-switch"', nav)
        self.assertNotIn('class="news-toolbar"', main)

    def test_accessible_popover_and_persisted_prefs(self):
        for key in ('aria-expanded="false"', 'aria-controls="view-options-panel"',
                    'toggle.setAttribute("aria-expanded", String(open))',
                    'if (event.key === "Escape" && !panel.hidden)',
                    'd.getElementById("text-size").focus()',
                    'noticias:density:v1', 'noticias:text-size:v1'):
            self.assertIn(key, self.page)

    def test_portal_keeps_public_news(self):
        for excluded in ('id="reading-filter"', 'id="reading-status"',
                         'function applyReadingFilter()', 'data-filter-hidden'):
            self.assertNotIn(excluded, self.page)
        self.assertIn('data-show-more', self.page)
        self.assertIn('--card-shadow-hover', self.page)


if __name__ == "__main__":
    unittest.main()
