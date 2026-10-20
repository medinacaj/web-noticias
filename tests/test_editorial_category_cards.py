"""Regresión del diseño editorial sin barras superiores de categoría."""
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH, render_sections


class EditorialCategoryCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
        cls.generator = Path(__file__).resolve().parents[1].joinpath("fetch_noticias.py").read_text(encoding="utf-8")

    def test_cards_are_not_decorated_by_top_border(self):
        card_css = self.template.split("/* Tarjetas oscuras sobre gris humo;", 1)[1].split("/* ---------- Portada ---------- */", 1)[0]
        self.assertNotIn("border-top:", card_css)
        self.assertNotIn("border-top-width:", self.template)
        self.assertIn("background:var(--card-bg)", card_css)
        self.assertIn("box-shadow:var(--card-shadow)", card_css)

    def test_category_identity_is_minimal(self):
        self.assertIn(".lead .kicker::before,.feature .kicker::before", self.template)
        self.assertIn("width:7px;height:7px;border-radius:50%", self.template)
        self.assertIn("background:var(--cat-b,var(--card-link))", self.template)
        self.assertNotIn(".section-head h2::before", self.template)
        self.assertNotIn("border-top:3px solid var(--cat", self.template)

    def test_categories_reach_feature_and_compact_news(self):
        self.assertIn('f\'<div class="news-body"><p class="kicker">{esc(cat["label"])}</p>\'', self.generator)
        self.assertIn('f\'<h3>{title_link(s)}</h3>', self.generator)
        self.assertIn('f\'<h3 class="feature-title">{title_link(feature)}</h3>', self.generator)

    def test_responsive_and_accessibility_remain(self):
        for marker in ("prefers-reduced-motion:reduce", "@media (max-width:767px)",
                       "box-shadow:var(--card-shadow-hover)", "%%NAV%%",
                       'aria-labelledby="titulo-', "data-show-more"):
            self.assertIn(marker, self.template if marker != 'aria-labelledby="titulo-' else self.generator)


if __name__ == "__main__":
    unittest.main()
