"""Distribución de fuentes en portada de categorías, sin excluir noticias."""
import unittest

from fetch_noticias import balance_section_sources


def item(source, number):
    # Cada editor del fixture publica en su propio dominio.
    domain = source.lower().replace(" ", "-")
    return {"title": f"Noticia {number}", "sources": [source], "link": f"https://{domain}.example/{number}"}


class BalancedSourcesTests(unittest.TestCase):
    def test_multiple_publishers_share_initial_six_slots(self):
        a = [item("Medio A", i) for i in range(8)]
        b = [item("Medio B", i + 8) for i in range(3)]
        c = [item("Medio C", i + 11) for i in range(2)]
        result = balance_section_sources(a + b + c)
        self.assertEqual(len(result), len(a + b + c))
        self.assertEqual({i["sources"][0] for i in result[:6]},
                         {"Medio A", "Medio B", "Medio C"})
        self.assertEqual(sum(i["sources"][0] == "Medio A" for i in result[:6]), 2)
        self.assertEqual({id(x) for x in result}, {id(x) for x in a + b + c})

    def test_one_publisher_keeps_original_order_and_fills_six(self):
        articles = [item("Medio A", i) for i in range(12)]
        self.assertEqual(balance_section_sources(articles), articles)

    def test_limit_and_short_category_are_respected(self):
        articles = [item("A", i) for i in range(2)]
        self.assertEqual(balance_section_sources(articles), articles)
        self.assertEqual(len(balance_section_sources(articles, limit=1)), 1)
        many = [item("A", i) for i in range(30)]
        self.assertEqual(len(balance_section_sources(many)), 24)
        self.assertEqual(len({id(x) for x in balance_section_sources(many)}), 24)

    def test_no_sources_falls_back_without_error(self):
        articles = [{"title": f"Item {i}", "sources": []} for i in range(8)]
        self.assertEqual(balance_section_sources(articles), articles)


if __name__ == "__main__":
    unittest.main()

