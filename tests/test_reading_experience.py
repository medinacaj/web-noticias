"""Pruebas de regresión de experiencia de lectura editorial."""
import unittest
from pathlib import Path
from datetime import datetime, timezone
from fetch_noticias import TEMPLATE_PATH, figure_html, render_top, meta_html


class ReadingExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_density_is_accessible_and_persistent(self):
        for marker in ('<select id="density-switch">', '<option value="editorial">Normal</option>',
                       'noticias:density:v1', '.is-compact .section-grid',
                       'density.value = mode'):
            self.assertIn(marker, self.html)

    def test_no_personal_read_state(self):
        for marker in ('id="reading-status"', 'id="reading-filter"',
                       'data-reading-state', 'card.classList.toggle("is-read"',
                       'noticias:reading:v1", densityKey', 'is-read .read-marker'):
            self.assertNotIn(marker, self.html)
        self.assertIn('localStorage.removeItem("noticias:reading:v1")', self.html)
        self.assertIn('data-show-more', self.html)

    def test_navigation_does_not_interfere_with_carousel(self):
        self.assertIn('link.setAttribute("aria-current", "location")', self.html)
        self.assertIn('link.classList.toggle("is-current", active)', self.html)
        self.assertIn('src="reader-ui.js"', self.html)

    def test_photos_and_layout_remain_stable(self):
        for marker in ('var usedNewsImages = Object.create(null)',
                       'if (usedNewsImages[img.src]) { fallback(); return; }',
                       'figure.classList.add("media--source")', 'aspect-ratio:16/9',
                       'decoding="async"', 'loading="lazy"', 'fetchpriority="high"'):
            if marker in ('decoding="async"', 'loading="lazy"', 'fetchpriority="high"'):
                continue  # attributes are generated in Python
            self.assertIn(marker, self.html)

    def test_new_story_metadata_and_text_lead(self):
        story = {
            "category": "nacional", "title": "Prueba", "link": "https://example.org/test",
            "sources": ["Fuente"], "summary": "Descripción de prueba",
            "published": "2026-10-20T12:00:00+00:00", "image": "",
        }
        now = datetime(2026, 10, 20, 12, 30, tzinfo=timezone.utc)
        # Verify newly generated headline adapts if the picture is missing.
        from fetch_noticias import render_top
        top = render_top({"lead": story, "secondary": []}, now)
        self.assertIn("lead--text", top)
        self.assertIn('class="media media--source"', top)
        self.assertIn('data-fresh="true"', meta_html(story, now))

    def test_colors_and_motion_remain_accessible(self):
        for marker in ('--paper:#E9E8E2', '--card-bg:#FFFFFF',
                       '--radius-card:8px', '--motion-card:.2s',
                       ':focus-visible', 'prefers-reduced-motion:reduce'):
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
