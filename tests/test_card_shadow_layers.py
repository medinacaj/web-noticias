"""Mantener sombras de tarjetas con elevación suave sin alterar geometría."""
from pathlib import Path
import re
import unittest
from fetch_noticias import TEMPLATE_PATH


class CardShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_restrained_shadows_have_no_inset_or_heavy_layers(self):
        for token in ("--card-shadow", "--card-shadow-hover"):
            match = re.search(rf"{re.escape(token)}:([^;]+);", self.css)
            self.assertIsNotNone(match)
            shadow = match.group(1)
            self.assertEqual(shadow.count("rgba("), 1)
            self.assertNotIn("inset", shadow)

    def test_card_hover_and_focus_use_shared_tokens(self):
        for token in ("box-shadow:var(--card-shadow);",
                      "box-shadow:var(--card-shadow-hover)",
                      ".lead:focus-within,.feature:focus-within",
                      "prefers-reduced-motion:reduce"):
            self.assertIn(token, self.css)

    def test_highlight_does_not_move_cards(self):
        # Pedido del usuario (2026-10-25): resaltar sin desplazar ni desalinear tarjetas.
        rule = re.search(r"\.lead:focus-within,[^{]+\{([^}]+)\}", self.css).group(1)
        self.assertNotIn("transform", rule)
        self.assertIn("outline-color:var(--card-accent)", rule)
        self.assertIn("@media (hover:hover)", self.css)
        self.assertIn(".compact-list li:active", self.css)

    def test_no_new_card_height_or_padding_rules(self):
        self.assertIn("--radius-card:17px", self.css)
        self.assertIn(".lead{grid-column:1 / span 7;--pad:22px;", self.css)


if __name__ == "__main__":
    unittest.main()
