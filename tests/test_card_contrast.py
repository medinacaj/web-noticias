"""Regresión de tema editorial contrastado y sombras de tarjetas."""
import re
import unittest
from pathlib import Path
from fetch_noticias import TEMPLATE_PATH


def luminance(hex_color):
    values = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return sum(weight * (c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4)
               for weight, c in zip((.2126, .7152, .0722), values))


def contrast(a, b):
    first, second = sorted((luminance(a), luminance(b)), reverse=True)
    return (first + .05) / (second + .05)


class ContrastThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_background_stays_light_and_cards_dark(self):
        self.assertIn("--paper:#EEF2F6", self.css)
        self.assertIn("--card-bg:#182639", self.css)
        self.assertIn("background:var(--card-bg);color:var(--card-ink)", self.css)
        self.assertGreater(contrast("#EEF2F6", "#182639"), 10)

    def test_card_readability_wcag_aa(self):
        for fg in ("#F0F4F8", "#C1CFDE", "#C5E1FF"):
            with self.subTest(color=fg):
                self.assertGreaterEqual(contrast(fg, "#182639"), 4.5)
                self.assertGreaterEqual(contrast(fg, "#223247"), 4.5)

    def test_shadows_have_two_layers_and_motion_safe(self):
        self.assertIn("--card-shadow:0 1px 2px", self.css)
        self.assertIn("--card-shadow-hover:0 2px 4px", self.css)
        self.assertIn("box-shadow:var(--card-shadow-hover)", self.css)
        self.assertIn("prefers-reduced-motion:reduce", self.css)

    def test_categories_favicons_and_layout_not_replaced(self):
        for key in (".lead", ".feature", ".compact-list li", ".rail-list li",
                    ".source-mark", ".media-badge", ".top-grid", "%%NAV%%"):
            self.assertIn(key, self.css)

    def test_system_dark_mode_cannot_override_smoke_background(self):
        self.assertNotIn("prefers-color-scheme:dark", self.css)
        self.assertNotIn(":root[data-theme=\"dark\"]", self.css)
        self.assertNotIn("--paper:#0B1420", self.css)
        self.assertIn("color-scheme:light;", self.css)
        self.assertIn("--paper:#EEF2F6", self.css)
        self.assertIn("--card-bg:#182639", self.css)


if __name__ == "__main__":
    unittest.main()
