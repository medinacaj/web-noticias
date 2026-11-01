"""Regresiones de tarjetas sin foto: respaldo visible y fotos auténticas."""
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fetch_noticias as news

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
TEMPLATE = Path(news.TEMPLATE_PATH).read_text(encoding="utf-8")


def story(kind="", image=""):
    return {
        "category": "cine-streaming" if kind else "tecnologia",
        "content_kind": kind, "title": "Noticia de prueba",
        "image": image, "source_url": "https://medio.example",
        "link": "https://medio.example/nota",
        "sources": ["Medio de prueba"], "summary": "",
        "published": "2026-11-01T09:00:00Z",
        "format": "Cine", "platform": "",
        "release_date": "2026-11-01",
    }


class VisualFallbackTests(unittest.TestCase):
    def test_culture_card_with_valid_photo_uses_actual_photo(self):
        html = news.figure_html(story("premiere", "https://medio.example/obra.jpg"))
        self.assertIn('<img src="https://medio.example/obra.jpg"', html)
        self.assertNotIn("media--source", html)

    def test_culture_card_without_photo_shows_source_mark_not_empty_space(self):
        for kind in ("premiere", "guide", "satire", "satire-source"):
            with self.subTest(kind=kind):
                html = news.figure_html(story(kind))
                self.assertIn('class="media media--source"', html)
                self.assertIn('class="source-visual"', html)
                self.assertIn("Medio de prueba", html)
                self.assertNotIn('src="https://medio.example/obra.jpg"', html)

    def test_regular_news_keeps_image_and_source_fallback(self):
        self.assertIn('<img src="https://medio.example/foto.webp"',
                      news.figure_html(story(image="https://medio.example/foto.webp")))
        self.assertIn('media--source', news.figure_html(story()))
        self.assertIn('media--source', news.figure_html(story(image="http://unsafe.example/photo.jpg")))

    def test_all_visible_fallbacks_are_not_hidden_by_css(self):
        self.assertNotIn('.media--source:not(.media--date):not(.media--region){display:none;}', TEMPLATE)
        self.assertIn('.section-grid .media--source,.rail-item > .media--source{background:', TEMPLATE)
        self.assertIn('.section-grid .feature:has(> .media--source)', TEMPLATE)
        self.assertIn('figure.classList.add("media--source")', TEMPLATE)
        self.assertNotIn("usedNewsImages[img.src]", TEMPLATE)

    def test_cinema_sections_get_media_and_original_links(self):
        premiere = story("premiere")
        result = news.render_sections({"cine-streaming": [premiere]}, NOW)
        self.assertIn('class="media media--source"', result)
        self.assertIn('href="https://medio.example/nota"', result)
        self.assertIn('data-content-kind="premiere"', result)
        self.assertNotIn('src="https://medio.example/obra.jpg"', result)


if __name__ == "__main__":
    unittest.main()
