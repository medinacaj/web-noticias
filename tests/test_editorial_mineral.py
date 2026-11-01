"""Regresiones del sistema Editorial Mineral aprobado para Noticias del Momento."""
from pathlib import Path
import re
import unittest

from fetch_noticias import TEMPLATE_PATH


def palette(css, dark=False):
    selector = r':root\[data-theme="dark"\]' if dark else r':root'
    block = re.search(selector + r'\{([^}]+)\}', css).group(1)
    return dict(re.findall(r'(--[a-z-]+):(#(?:[0-9A-Fa-f]{6}))', block))


def luminance(hex_color):
    parts = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    parts = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in parts]
    return sum(w * v for w, v in zip((.2126, .7152, .0722), parts))


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + .05) / (low + .05)


class EditorialMineralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
        cls.css = cls.page.split("<style>", 1)[1].split("</style>", 1)[0]
        cls.light, cls.dark = palette(cls.css), palette(cls.css, dark=True)

    def test_semantic_identity_is_mineral_not_violet(self):
        for token, expected in {
            "--paper": "#E9E8E2", "--ink": "#252C2C",
            "--surface": "#FFFFFF", "--card-bg": "#FFFFFF",
            "--card-rule": "#D5D9D5", "--card-link": "#285D63",
            "--brand": "#285D63", "--wash": "#DDEBEA",
            "--callout-bg": "#DDEBEA", "--callout-ink": "#285D63",
        }.items():
            with self.subTest(token=token):
                self.assertEqual(self.light[token], expected)

    def test_dark_theme_is_neutral_and_petrolic(self):
        for token, expected in {
            "--paper": "#111315", "--surface": "#1C1F23",
            "--card-bg": "#343A43", "--card-ink": "#F7F6F2",
            "--card-muted": "#CCD1D6", "--card-link": "#B4DCC8",
            "--brand": "#B4DCC8", "--wash": "#27362F",
            "--card-rule": "#66717D", "--callout-bg": "#27362F",
            "--callout-ink": "#DEEDDE",
        }.items():
            with self.subTest(token=token):
                self.assertEqual(self.dark[token], expected)

    def test_legacy_violet_does_not_leak_into_live_styles(self):
        for obsolete in ("#4A3E8A", "#8D6FDE", "#EBE5FF", "#D9CFFA",
                         "#5B3F9E", "#B39AF5", "#C7B2E8", "#30283F"):
            self.assertNotIn(obsolete.lower(), self.css.lower())

    def test_text_colors_meet_aa_on_actual_surfaces(self):
        for color, surface, theme in (
            (self.light["--card-ink"], self.light["--card-bg"], "light ink"),
            (self.light["--card-muted"], self.light["--card-bg"], "light muted"),
            (self.light["--card-link"], self.light["--card-bg"], "light link"),
            (self.light["--callout-ink"], self.light["--callout-bg"], "light callout"),
            (self.dark["--card-ink"], self.dark["--card-bg"], "dark ink"),
            (self.dark["--card-muted"], self.dark["--card-bg"], "dark muted"),
            (self.dark["--card-link"], self.dark["--card-bg"], "dark link"),
            (self.dark["--callout-ink"], self.dark["--callout-bg"], "dark callout"),
        ):
            with self.subTest(theme=theme):
                self.assertGreaterEqual(contrast(color, surface), 4.5)

    def test_dark_background_and_controls_are_separate(self):
        self.assertGreaterEqual(contrast(self.dark["--card-bg"], self.dark["--paper"]), 1.6)
        self.assertGreaterEqual(contrast(self.dark["--card-rule"], self.dark["--card-bg"]), 2.25)
        self.assertGreaterEqual(contrast(self.dark["--card-muted"], self.dark["--card-bg"]), 7)
        self.assertIn(':root[data-theme="dark"] .save-story,', self.css)
        self.assertIn(':root[data-theme="dark"] .share-story{', self.css)
        self.assertIn('background:var(--callout-bg);', self.css)
        self.assertIn('border:1px solid #789087;', self.css)
        self.assertIn(':root[data-theme="dark"] .back-to-top{', self.css)
        self.assertGreaterEqual(contrast("#789087", self.dark["--card-bg"]), 3)
        self.assertGreaterEqual(contrast(self.dark["--card-link"], self.dark["--callout-bg"]), 4.5)

    def test_categories_keep_distinct_colors_instead_of_violet(self):
        for theme in (self.light, self.dark):
            colors = [theme["--c-economia"], theme["--c-internacional"],
                      theme["--c-tecnologia"]]
            self.assertEqual(len(set(colors)), len(colors))
        self.assertEqual(self.light["--c-tecnologia"], "#39766C")
        self.assertEqual(self.dark["--c-tecnologia"], "#9ED0CC")

    def test_editorial_typography_and_mobile_navigation(self):
        self.assertIn('--serif:Georgia,"Times New Roman",serif;', self.css)
        self.assertIn('.site-nav a{display:flex;align-items:center;min-height:44px;', self.css)
        self.assertIn('font:500 13px/1.4 var(--sans)', self.css)
        self.assertIn('.nav-heading{font:700 11px/1.4 var(--sans)', self.css)
        self.assertIn('.section-head .section-count{min-height:29px;padding:5px 10px;font-size:11px;}', self.css)
        self.assertIn(':focus-visible{outline:2px solid var(--brand)', self.css)
        self.assertIn('.section-grid .feature', self.css)
        self.assertIn('box-shadow:var(--card-shadow);', self.css)


if __name__ == "__main__":
    unittest.main()
