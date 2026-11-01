"""Regresión de legibilidad de rótulos editoriales en pantallas pequeñas.

No certifica WCAG ni sustituye pruebas de zoom/Safari: QA responsive
comprueba la geometría real de los componentes después del cambio.
"""
import re
import unittest
from pathlib import Path

from fetch_noticias import TEMPLATE_PATH


class MobileEditorialTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = Path(TEMPLATE_PATH).read_text(encoding="utf-8").split("</style>", 1)[0]

    def test_mobile_latest_label_and_headline_not_tiny(self):
        mobile = re.search(
            r"@media\s*\(max-width:767px\)\{[^\n]*\.breaking-label\{[^}]*\}",
            self.css,
        )
        self.assertIsNotNone(mobile)
        self.assertIn("font-size:11px", mobile.group(0))
        self.assertIn(".breaking-item a{font-size:13px;}", self.css)

    def test_category_and_region_labels_are_readable(self):
        self.assertIn("color:var(--card-muted);font-size:11px;letter-spacing:.10em;", self.css)
        self.assertIn(".rail-item .region-label{font-size:11px;line-height:1.15;", self.css)

    def test_breaking_strip_keeps_compact_height(self):
        self.assertIn("--breaking-height:36px", self.css)
        self.assertIn("height:var(--breaking-height)", self.css)


if __name__ == "__main__":
    unittest.main()
