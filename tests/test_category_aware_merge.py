"""Evitar que titulares similares vacíen secciones editoriales distintas."""
import unittest
from datetime import datetime, timezone

from fetch_noticias import merge, select


class CategoryAwareMergeTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)

    def article(self, category, link, source="Medio A",
                title="Avances de nueva investigación científica en Chile"):
        return {
            "category": category, "link": link, "title": title,
            "source": source, "published": "2026-10-20T17:00:00Z",
            "summary": "", "image": "",
        }

    def test_identical_headline_from_different_sections_keeps_both_when_urls_differ(self):
        items = [
            self.article("nacional", "https://a.example/avances"),
            self.article("salud-ciencia", "https://b.example/estudio"),
        ]
        stories = []
        self.assertEqual(merge(stories, items, self.now), 2)
        self.assertEqual({s["category"] for s in stories},
                         {"nacional", "salud-ciencia"})
        self.assertIn("salud-ciencia", select(stories, self.now)["by_category"])

    def test_same_article_across_categories_is_not_duplicated_by_tracking(self):
        items = [
            self.article("nacional", "https://medio.example/noticia?utm_source=rss"),
            self.article("medioambiente", "https://medio.example/noticia?oc=5",
                         source="Medio B", title="Titular editorial diferente"),
        ]
        stories = []
        self.assertEqual(merge(stories, items, self.now), 1)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["sources"], ["Medio A", "Medio B"])

    def test_distinct_media_same_section_still_group_as_coverage(self):
        items = [
            self.article("salud-ciencia", "https://a.example/nota", source="Medio A"),
            self.article("salud-ciencia", "https://b.example/nota", source="Medio B"),
        ]
        stories = []
        self.assertEqual(merge(stories, items, self.now), 1)
        self.assertEqual(stories[0]["sources"], ["Medio A", "Medio B"])
        self.assertEqual(len(stories[0]["coverages"]), 2)

    def test_invalid_url_is_ignored(self):
        stories = []
        count = merge(stories, [self.article("nacional", "javascript:alert(1)")], self.now)
        self.assertEqual(count, 0)
        self.assertFalse(stories)


if __name__ == "__main__":
    unittest.main()
