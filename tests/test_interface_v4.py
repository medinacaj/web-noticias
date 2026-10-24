"""Regresiones V4: búsqueda local, filtros, móvil y preferencias visuales."""
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH


class InterfaceV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_local_search_has_real_filters_and_safe_highlights(self):
        for part in ('id="search-category"', 'id="search-source"',
                     'id="search-date"', "function updateResults()",
                     "createElement(\"mark\")", "mark.textContent = part",
                     "d.createTextNode(part)", 'input.addEventListener("input", updateResults)'):
            self.assertIn(part, self.page)
        self.assertNotIn("a.innerHTML = item.title", self.page)

    def test_no_private_read_filters_or_hidden_cards(self):
        for marker in ('id="reading-filter"', 'value="unread"', 'value="read"',
                       'data-filter-hidden', 'function applyReadingFilter()',
                       'id="reading-status"'):
            self.assertNotIn(marker, self.page)
        self.assertIn('data-show-more', self.page)
        self.assertIn('id="text-size"', self.page)

    def test_text_prefs_and_density_both_exist(self):
        for part in ('id="text-size"', 'noticias:text-size:v1', 'data-text-size="large"',
                     'id="density-switch"', 'noticias:density:v1', 'is-compact'):
            # attribute selector data-text-size is authored as CSS, not HTML
            if part == 'data-text-size="large"':
                self.assertIn('[data-text-size="large"]', self.page)
            else:
                self.assertIn(part, self.page)

    def test_keyboard_mobile_and_navigation(self):
        for part in ('id="back-to-top"', 'window.scrollTo({top:0',
                     'event.ctrlKey || event.metaKey', 'event.key.toLowerCase() === "k"',
                     '@media(max-width:360px)', '@media (max-width:767px)',
                     'prefers-reduced-motion:reduce', 'aria-live="polite"'):
            self.assertIn(part, self.page)

    def test_prior_editorial_features_preserved(self):
        for part in ('--paper:#F2F1ED', '--card-bg:#FFFFFF',
                     'dialog.className = "coverage-dialog"', 'data-coverage-trigger',
                     'dialog.showModal()', 'src="reader-ui.js"',
                     'data-show-more', '.media--source', '%%TOP%%', '%%SECTIONS%%'):
            self.assertIn(part, self.page)


if __name__ == "__main__":
    unittest.main()
