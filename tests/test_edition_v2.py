"""Regresiones para nueva edición de Noticias del Momento."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import fetch_noticias as news


class EditionV2Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, tzinfo=timezone.utc)

    def make_story(self, category, index, image=""):
        return {
            "category": category,
            "title": f"Noticia número {index} sobre {category}",
            "sources": ["Medio oficial"],
            "link": f"https://medio.example/nota/{category}/{index}",
            "image": image,
            "summary": "",
            "published": "2026-10-20T00:00:00Z",
            "first_seen": "2026-10-20T00:00:00Z",
        }

    def test_new_sections_all_have_valid_feed_urls(self):
        keys = ("regiones", "politica", "medioambiente", "salud-ciencia")
        self.assertTrue(all(k in news.CATEGORY_LABELS for k in keys))
        for cat in news.CATEGORIES:
            url = news.category_google_url(cat)
            self.assertTrue(url.startswith("https://news.google.com/rss/"))
            if cat["key"] in keys:
                self.assertIn("search?q=", url)

    def test_new_category_feeds_work_without_gnews_api(self):
        xml = "<rss><channel><item><title>Política informativa del congreso</title><link>https://news.google.com/rss/articles/abc</link><source url='https://medio.example'>Medio</source></item></channel></rss>".encode("utf-8")
        with patch.object(news, "http_get", return_value=xml):
            found = news.fetch_rss(news.category_google_url(
                next(c for c in news.CATEGORIES if c["key"] == "politica")), "politica")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["category"], "politica")

    def test_more_shows_six_first_then_more_and_keeps_content_server_rendered(self):
        items = [self.make_story("nacional", i) for i in range(15)]
        html = news.render_sections({"nacional": items}, self.now)
        self.assertEqual(html.count('data-extra'), 9)
        self.assertEqual(html.count('class="compact"'), 14)
        self.assertEqual(html.count('data-show-more'), 1)
        self.assertIn('aria-controls="noticias-nacional"', html)

    def test_no_more_button_for_fewer_than_seven(self):
        items = [self.make_story("nacional", i) for i in range(5)]
        html = news.render_sections({"nacional": items}, self.now)
        self.assertNotIn("data-show-more", html)

    def test_select_retains_48_category_stories(self):
        items = [self.make_story("politica", i) for i in range(60)]
        result = news.select(items, self.now)
        self.assertEqual(len(result["by_category"]["politica"]), 48)

    def test_lead_prefers_real_photo_among_highest_ranked(self):
        items = [self.make_story("nacional", i) for i in range(6)]
        items[2]["image"] = "https://medio.example/imagen.jpg"
        result = news.select(items, self.now)
        self.assertIs(result["lead"], items[2])

    def test_template_has_progressive_controls_and_responsive_layout(self):
        from pathlib import Path
        template = Path(news.TEMPLATE_PATH).read_text(encoding="utf-8")
        self.assertIn('d.querySelectorAll("[data-show-more]")', template)
        self.assertIn('.js .section-grid [data-extra]', template)
        self.assertIn('button.hidden = true', template)
        self.assertIn('grid-column:1 / span 7', template)
        self.assertIn('grid-column:8 / span 5', template)
        self.assertIn('.lead .media{', template)
        self.assertIn('@media (max-width:767px)', template)

    def test_generated_categories_retain_existing_selections(self):
        keys = {c["key"] for c in news.CATEGORIES}
        self.assertTrue({"nacional", "internacional", "economia", "tecnologia",
                         "deportes", "cultura"}.issubset(keys))


if __name__ == "__main__":
    unittest.main()
