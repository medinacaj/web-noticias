"""La identidad de categorías se muestra en contadores y etiquetas sin inventar datos."""
from datetime import datetime, timezone
from pathlib import Path
import re
import unittest

import fetch_noticias as news

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
CSS = Path(news.TEMPLATE_PATH).read_text(encoding="utf-8")


def story(category, index):
    return {"category": category, "title": f"Nota de prueba {index}",
            "link": f"https://editor.example/nota/{category}-{index}",
            "source_url": "https://editor.example",
            "sources": ["Medio"], "image": "", "summary": "",
            "published": "2026-11-01T09:00:00Z"}


class CategoryBadgesTests(unittest.TestCase):
    def test_section_counts_remain_factual_and_inside_accessible_heading(self):
        html = news.render_sections({
            "nacional": [story("nacional", 1), story("nacional", 2)],
            "deportes": [story("deportes", 3)],
        }, NOW)
        self.assertIn('class="section cat-nacional"', html)
        self.assertIn('class="section cat-deportes"', html)
        self.assertIn('<span class="section-count">2 noticias</span>', html)
        self.assertIn('<span class="section-count">1 noticia</span>', html)
        self.assertEqual(html.count('class="section-count"'), 2)
        self.assertEqual(html.count('class="section-num"'), 2)

    def test_all_section_colors_and_cinema_unique_color_exist(self):
        for name in ("nacional", "latinoamerica", "internacional", "economia",
                     "tecnologia", "deportes", "cultura", "agenda", "regiones",
                     "politica", "medioambiente", "salud-ciencia", "cine-streaming"):
            self.assertIn(".cat-" + name, CSS)
        self.assertIn(".cat-cine-streaming{--cat:color-mix(in srgb,var(--c-internacional) 58%,var(--c-economia));--cat-b:color-mix(in srgb,var(--b-internacional) 55%,var(--b-economia));}", CSS)

    def test_badges_stay_small_tinted_and_legible_in_both_themes(self):
        for marker in (".section-head .section-count{", "border-radius:var(--pill)",
                       "background:color-mix(in srgb,var(--cat) 10%,var(--card-bg))",
                       "color:var(--cat);font:650 11px/1.3 var(--sans)",
                       '.section-head .section-num{',
                       ":root[data-theme=\"dark\"] .section-head .section-count",
                       "color:var(--cat-b);", ".section-grid .kicker{",
                       "max-width:100%;", "@media (max-width:479px)"):
            self.assertIn(marker, CSS)
        self.assertNotIn("background:linear-gradient", CSS[CSS.index("/* Identidad cromática editorial:"):CSS.index("</style>")])
        self.assertIn(".section-grid.section-grid--single{grid-template-columns:minmax(0,1fr);}", CSS)


if __name__ == "__main__":
    unittest.main()
