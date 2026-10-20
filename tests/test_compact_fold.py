"""Regresión del espacio sobrante sobre la portada editorial."""
from pathlib import Path
import unittest
from fetch_noticias import TEMPLATE_PATH


class CompactFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_toolbar_reuses_news_strip(self):
        self.assertIn('var strip = d.querySelector(".breaking-inner")', self.page)
        self.assertIn('if (strip && toolbar) strip.appendChild(toolbar)', self.page)
        self.assertIn('main.container{padding-top:14px;}', self.page)
        self.assertIn('.breaking .news-toolbar{flex:none;', self.page)

    def test_existing_controls_remain_available(self):
        for marker in ('id="density-switch"', 'id="text-size"',
                       'noticias:density:v1', 'noticias:text-size:v1',
                       'data-show-more', '%%BREAKING%%', '%%TOP%%'):
            self.assertIn(marker, self.page)

    def test_mobile_stacks_controls(self):
        self.assertIn('@media(max-width:900px){.breaking-inner{flex-wrap:wrap;', self.page)
        self.assertIn('@media(max-width:480px)', self.page)

    def test_no_read_tracking_reintroduced(self):
        for marker in ('id="reading-filter"', 'id="reading-status"',
                       'function applyReadingFilter()', 'is-read .read-marker'):
            self.assertNotIn(marker, self.page)


if __name__ == "__main__":
    unittest.main()
