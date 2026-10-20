"""Regresión: comparación de coberturas reales sin inflar las tarjetas."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from fetch_noticias import (
    TEMPLATE_PATH, merge, coverage_items, coverage_control, meta_html,
)


def item(source, link, title="Municipio anuncia nuevo proyecto"):
    return {"category": "nacional", "source": source, "title": title,
            "link": link, "published": "2026-10-20T06:00:00Z"}


class CoverageComparisonTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 7, 0, tzinfo=timezone.utc)

    def test_grouping_keeps_distinct_original_urls_and_titles(self):
        stories = []
        first = item("Medio Uno", "https://medio1.cl/nota")
        second = item("Medio Dos", "https://medio2.cl/nota", "Municipio anuncia nuevo proyecto")
        merge(stories, [first, second], self.now)
        self.assertEqual(len(stories), 1)
        self.assertEqual(len(coverage_items(stories[0])), 2)
        result = coverage_control(stories[0])
        self.assertIn("Comparar", result)
        self.assertIn("https://medio1.cl/nota", result)
        self.assertIn("https://medio2.cl/nota", result)
        self.assertIn("Publicaciones relacionadas", result)
        self.assertIn('aria-haspopup="dialog"', result)

    def test_single_source_or_unverifiable_google_link_does_not_show_comparison(self):
        stories = []
        merge(stories, [item("Uno", "https://uno.cl/uno"),
                        item("Dos", "https://news.google.com/article/abc")], self.now)
        self.assertEqual(len(stories), 1)
        self.assertEqual(len(coverage_items(stories[0])), 1)
        self.assertEqual(coverage_control(stories[0]), "")

    def test_duplicate_source_does_not_create_fake_comparison(self):
        stories = []
        merge(stories, [item("Uno", "https://uno.cl/a"),
                        item("Uno", "https://uno.cl/b")], self.now)
        self.assertEqual(len(coverage_items(stories[0])), 1)
        self.assertEqual(coverage_control(stories[0]), "")

    def test_existing_history_without_coverages_works(self):
        legacy = {"sources": ["Uno", "Dos"], "link": "https://uno.cl/a"}
        self.assertEqual(coverage_items(legacy), [])
        self.assertEqual(coverage_control(legacy), "")

    def test_content_is_escaped_and_modal_accessible(self):
        stories = []
        merge(stories, [item("Uno", "https://uno.cl/a", "<bad> Ejemplo"),
                        item("Dos", "https://dos.cl/a", "<bad> Ejemplo")], self.now)
        content = coverage_control(stories[0])
        self.assertIn("&lt;bad&gt;", content)
        self.assertNotIn("<bad>", content)
        template = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
        for marker in ('dialog.showModal()', 'dialog.addEventListener("close"',
                       'template.content.cloneNode(true)', "previousFocus.focus()",
                       ".coverage-dialog", ".coverage-trigger"):
            self.assertIn(marker, template)

    def test_metadata_keeps_comparison_inside_existing_card(self):
        stories = []
        merge(stories, [item("Uno", "https://uno.cl/a"),
                        item("Dos", "https://dos.cl/a")], self.now)
        html = meta_html(stories[0], self.now)
        self.assertIn('data-coverage-trigger', html)
        self.assertIn('class="meta"', html)


if __name__ == "__main__":
    unittest.main()
