"""Regresiones para pulido visual editorial y fallback fotográfico auténtico."""
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH


class EditorialVisualSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_featured_photography_and_typography(self):
        for css in ("aspect-ratio:16/9;height:auto;max-height:280px",
                    "font-size:clamp(29px,3vw,42px)",
                    "text-wrap:balance", "text-wrap:pretty",
                    "object-fit:cover;object-position:center"):
            self.assertIn(css, self.source)

    def test_card_heights_and_meta_alignment(self):
        for css in ("min-height:164px", ".news-body{flex:1;min-width:0;display:flex;flex-direction:column",
                    ".section-grid .meta{margin-top:auto",
                    ".compact .meta{margin-top:auto",
                    ".card-footer > .meta{flex:1 1 140px"):
            self.assertIn(css, self.source)

    def test_section_photos_use_landscape_thumbnails_and_respect_dense_views(self):
        self.assertIn(".section-grid .media{flex:0 0 104px;width:104px;height:auto;min-height:0;align-self:flex-start;aspect-ratio:4/3;", self.source)
        self.assertIn(".section-grid .media{flex-basis:92px;width:92px;height:auto;min-height:0;}", self.source)
        self.assertIn(".media > img{width:100%;height:100%;object-fit:cover;object-position:center", self.source)
        self.assertIn(".is-compact .section-grid .media{display:none;}", self.source)
        self.assertIn(".is-headlines .section-grid .media,.is-headlines .section-grid .dek{display:none;}", self.source)
        self.assertIn(".section-grid .media--source{padding:8px;}", self.source)

    def test_missing_photos_fallback_to_real_source(self):
        for code in ("figure.classList.add(\"media--source\")",
                     'figure.setAttribute("role", "img")',
                     "mark.cloneNode(true)", "label.textContent = name ? name.textContent.trim()",
                     'img.addEventListener("error", fallback)'):
            self.assertIn(code, self.source)
        self.assertNotIn("if (f) f.remove()", self.source)

    def test_motion_and_touch_are_respected(self):
        self.assertIn("@media (hover:hover) and (pointer:fine)", self.source)
        self.assertIn("prefers-reduced-motion:reduce", self.source)
        self.assertIn("min-height:0;", self.source)
        self.assertIn("@media (max-width:767px)", self.source)

    def test_existing_visual_identity_and_features_unchanged(self):
        for marker in ("--paper:#F3F1F8", "--card-bg:#FFFFFF",
                       "box-shadow:var(--card-shadow-hover)", "width:7px;height:7px;border-radius:50%",
                       "%%NAV%%", "%%TOP%%", "%%SECTIONS%%", "data-show-more"):
            self.assertIn(marker, self.source)


if __name__ == "__main__":
    unittest.main()
