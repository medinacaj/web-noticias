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

    @classmethod
    def palette(cls, dark=False):
        selector = r':root\[data-theme="dark"\]' if dark else r':root'
        block = re.search(selector + r'\{([^}]+)\}', cls.css).group(1)
        values = dict(re.findall(r'(--[a-z-]+):(#[0-9A-Fa-f]{6})', block))
        return values

    def test_light_cards_and_dark_cards_are_distinct_from_the_background(self):
        light, dark = self.palette(), self.palette(dark=True)
        self.assertGreater(luminance(light['--card-bg']), .9)
        self.assertGreater(luminance(light['--card-bg']), luminance(light['--paper']))
        self.assertGreaterEqual(contrast(dark['--card-bg'], dark['--paper']), 1.5)
        for colors in (light, dark):
            for token in ('--paper', '--card-bg', '--surface'):
                rgb = [int(colors[token][i:i+2], 16) for i in (1, 3, 5)]
                self.assertLessEqual(max(rgb) - min(rgb), 24)

    def test_card_readability_wcag_aa(self):
        for dark in (False, True):
            colors = self.palette(dark)
            for token in ('--card-ink', '--card-muted', '--card-link'):
                with self.subTest(dark=dark, token=token):
                    self.assertGreaterEqual(contrast(colors[token], colors['--card-bg']), 4.5)

    def test_shadows_have_soft_layers_and_motion_safe(self):
        self.assertIn("--card-shadow:0 1px 2px", self.css)
        self.assertIn("--card-shadow-hover:0 8px 24px", self.css)
        self.assertIn("box-shadow:var(--card-shadow-hover)", self.css)
        self.assertIn("prefers-reduced-motion:reduce", self.css)

    def test_categories_favicons_and_layout_not_replaced(self):
        for key in (".lead", ".feature", ".compact-list li", ".rail-list li",
                    ".source-mark", ".media--source", ".top-grid", "%%NAV%%"):
            self.assertIn(key, self.css)

    def test_available_themes_keep_contrast(self):
        for dark in (False, True):
            colors = self.palette(dark)
            for token in ('--ink', '--muted'):
                self.assertGreaterEqual(contrast(colors[token], colors['--surface']), 4.5)


if __name__ == "__main__":
    unittest.main()
