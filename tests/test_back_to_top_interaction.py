"""Regresión de interacción: Portada no impide acciones de las noticias."""
from pathlib import Path
import unittest
from fetch_noticias import TEMPLATE_PATH


class BackToTopSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    def test_floating_button_keeps_accessible_name_and_function(self):
        self.assertIn('id="back-to-top"', self.page)
        self.assertIn('aria-label="Volver a la portada"', self.page)
        self.assertIn('window.scrollTo({top:0,behavior:reduced ? "instant" : "smooth"})', self.page)

    def test_action_buttons_cannot_be_occluded_by_floating_button(self):
        self.assertIn('d.querySelectorAll(".card-actions .save-story, .card-actions .share-story")', self.page)
        self.assertIn('function overlaps(a, b, gap)', self.page)
        self.assertIn('top.hidden = actions.some(function (button)', self.page)
        self.assertIn('overlaps(target, button.getBoundingClientRect(), 8)', self.page)
        self.assertIn('window.requestAnimationFrame(function () { pending = false; update(); })', self.page)

    def test_footer_and_initial_view_still_hide_button(self):
        self.assertIn('window.scrollY < 900 || (footer && footer.getBoundingClientRect().top < window.innerHeight)', self.page)


if __name__ == "__main__":
    unittest.main()
