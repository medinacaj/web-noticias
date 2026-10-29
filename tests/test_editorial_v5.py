"""Regresiones para opciones de lectura, radar y QA del sitio V5."""
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH, render_coverage_radar


class EditorialV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_options_are_in_a_single_collapsible_panel(self):
        for marker in ('id="view-options-panel" hidden', 'id="view-options-toggle"',
                       'id="source-preference"', 'id="category-preference"',
                       'id="source-sort"', 'id="library-toggle"', 'id="density-switch"',
                       'id="text-size"'):
            self.assertIn(marker, self.page)

    def test_library_is_local_and_bounded(self):
        for marker in ('id="library-panel" hidden', 'id="saved-stories"',
                       'noticias:library:v1', 'MAX_RECORDS = 120',
                       'DAYS = 30 * 86400000', 'aria-pressed'):
            self.assertIn(marker, self.page)

    def test_portal_has_no_personal_read_tracking(self):
        for token in ('id="reading-filter"', 'id="reading-status"', 'id="reading-history"',
                      'id="clear-reader-history"', 'function applyReadingFilter()'):
            self.assertNotIn(token, self.page)

    def test_share_and_save_are_optional_actions_not_read_status(self):
        for marker in ('className = "share-story"', 'navigator.share(news)',
                       'navigator.clipboard.writeText(link.href)',
                       'className = "save-story"', 'noticias:library:v1'):
            self.assertIn(marker, self.page)
        self.assertNotIn('card.classList.toggle("is-read"', self.page)

    def test_third_layout_is_independent_from_editorial(self):
        for marker in ('.is-headlines .section-grid', '.is-compact .section-grid',
                       'mode === "headlines"', 'setDensity(mode)',
                       'noticias:density:v1'):
            self.assertIn(marker, self.page)

    def test_radar_needs_four_distinct_outlets(self):
        story = {"title": "Ejemplo", "link": "https://medio.cl/nota",
                 "sources": ["A", "B", "C"]}
        self.assertEqual(render_coverage_radar([story]), "")
        story["sources"].append("D")
        html = render_coverage_radar([story])
        self.assertIn("Radar de cobertura", html)
        self.assertIn("4 medios distintos", html)
        self.assertIn("No implica", html)
        self.assertNotIn("crecimiento verificado", html)

    def test_radar_does_not_double_count_same_outlet(self):
        story = {"title": "Ejemplo", "link": "https://medio.cl/nota",
                 "sources": ["A", "B", "C", "C"]}
        self.assertEqual(render_coverage_radar([story]), "")

    def test_quality_and_visual_scripts_are_present(self):
        root = Path(TEMPLATE_PATH).resolve().parent
        audit = (root / "scripts/audit_editorial_quality.py").read_text(encoding="utf-8")
        visual = (root / "scripts/visual_qa.py").read_text(encoding="utf-8")
        workflow = (root / ".github/workflows/visual-qa.yml").read_text(encoding="utf-8")
        self.assertIn("imagenes_repetidas", audit)
        self.assertIn("enlaces_invalidos", audit)
        self.assertIn("320, 375, 768, 1024, 1440", visual)
        self.assertIn("scrollWidth > window.innerWidth", visual)
        self.assertIn("upload-artifact@v4", workflow)

    def test_headline_is_the_only_full_story_link(self):
        from datetime import datetime, timezone
        from fetch_noticias import meta_html
        story = {"title": "Titular", "category": "nacional",
                 "link": "https://medio.cl/noticia", "sources": ["Medio"],
                 "published": "2026-10-20T07:00:00Z"}
        output = meta_html(story, datetime(2026, 10, 20, 8, tzinfo=timezone.utc), True)
        self.assertNotIn("Ver noticia completa", output)
        self.assertNotIn('class="read"', output)

    def test_existing_comparison_and_colors_survive(self):
        for marker in ('dialog.showModal()', 'data-coverage-trigger',
                       '--paper:#F3F1F8', '--card-bg:#FFFFFF',
                       'box-shadow:var(--card-shadow-hover)', '%%TOP%%',
                       '%%RADAR%%', '%%SECTIONS%%'):
            self.assertIn(marker, self.page)


if __name__ == "__main__":
    unittest.main()
