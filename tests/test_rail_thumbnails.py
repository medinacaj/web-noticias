"""Las Destacadas muestran una miniatura cuadrada, con respaldo del medio sin foto."""
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fetch_noticias as fn

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def story(title, image=""):
    return {"category": "nacional", "title": title, "summary": "", "image": image,
            "sources": ["Mi Medio"], "source_url": "https://medio.cl",
            "link": f"https://medio.cl/{title.lower().replace(' ', '-')}",
            "published": "2026-10-24T11:00:00Z"}


class RailThumbnailTests(unittest.TestCase):
    def render(self, secondary):
        selected = {"lead": story("Portada"), "secondary": secondary}
        return fn.render_top(selected, NOW)

    def test_each_featured_item_has_a_thumbnail(self):
        html = self.render([story("Con foto", "https://medio.cl/foto.jpg"), story("Sin foto")])
        items = re.findall(r'<article class="rail-item">(.*?)</article>', html)
        self.assertEqual(len(items), 2)
        self.assertIn('<figure class="media"><img src="https://medio.cl/foto.jpg"', items[0])
        self.assertIn('loading="lazy"', items[0])
        self.assertIn('class="media media--source"', items[1])
        self.assertIn('aria-label="Medio de origen: Mi Medio"', items[1])

    def test_thumbnail_comes_before_text_and_headline_stays_linked(self):
        html = self.render([story("Con foto", "https://medio.cl/foto.jpg")])
        item = re.search(r'<article class="rail-item">(.*?)</article>', html).group(1)
        self.assertLess(item.index("<figure"), item.index('class="kicker"'))
        self.assertIn('href="https://medio.cl/con-foto"', item)

    def test_template_sizes_square_thumbnail_and_hides_it_in_dense_views(self):
        css = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn(".rail-item > .media{grid-column:2;grid-row:2 / span 2;width:88px;height:88px;", css)
        self.assertIn(".is-compact .rail-item > .media,.is-headlines .rail-item > .media{display:none;}", css)
        self.assertIn('".lead,.feature,.compact-list li,.rail-list li"', css)


if __name__ == "__main__":
    unittest.main()
