"""Regresión del diseño editorial sin barras superiores de categoría."""
import unittest
import re
from datetime import datetime, timezone
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH, render_sections


class EditorialCategoryCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
        cls.generator = Path(__file__).resolve().parents[1].joinpath("fetch_noticias.py").read_text(encoding="utf-8")

    def test_cards_are_not_decorated_by_top_border(self):
        card_css = re.search(r"\.lead,\.feature,\.rail-list li,\.compact-list li\{([^}]+)\}",
                             self.template).group(1)
        self.assertNotIn("border-top:", card_css)
        self.assertNotIn("border-top-width:", self.template)
        self.assertIn("background:var(--card-bg)", card_css)
        self.assertIn("box-shadow:var(--card-shadow)", card_css)

    def test_category_identity_is_minimal(self):
        self.assertIn(".lead .kicker::before,.feature .kicker::before", self.template)
        self.assertIn("width:7px;height:7px;border-radius:50%", self.template)
        self.assertIn("background:var(--cat,var(--card-link))", self.template)
        self.assertNotIn(".section-head h2::before", self.template)
        self.assertNotIn("border-top:3px solid var(--cat", self.template)

    def test_categories_reach_feature_and_compact_news(self):
        stories = [{"category": category, "title": "Titular sobre " + category,
                    "link": "https://medio.example/" + category, "sources": ["Medio"],
                    "image": "", "summary": "", "published": "2026-10-22T12:00:00Z"}
                   for category in ("tecnologia", "salud-ciencia")]
        output = render_sections({"tecnologia": stories}, datetime(2026, 10, 22, 12, tzinfo=timezone.utc))
        self.assertIn('<p class="kicker">Ciencia y tecnología</p>', output)
        self.assertIn('<p class="kicker">Salud</p>', output)
        self.assertIn('data-key="salud-ciencia"', output)
        self.assertIn('class="feature-title"', output)

    def test_responsive_and_accessibility_remain(self):
        for marker in ("prefers-reduced-motion:reduce", "@media (max-width:767px)",
                       "box-shadow:var(--card-shadow-hover)", "%%NAV%%",
                       'aria-labelledby="titulo-', "data-show-more"):
            self.assertIn(marker, self.template if marker != 'aria-labelledby="titulo-' else self.generator)


if __name__ == "__main__":
    unittest.main()

