import unittest
from scripts.dedupe_history import canonical_key, deduplicate


class HistoryQualityTests(unittest.TestCase):
    def test_tracking_does_not_create_another_story(self):
        first = {"link": "https://www.bbc.com/mundo/articles/abc?utm_source=rss",
                 "title": "Titular original", "sources": ["Medio A"]}
        duplicate = {"link": "https://www.bbc.com/mundo/articles/abc?oc=5",
                     "title": "Titular alternativo", "sources": ["Medio B"]}
        data = deduplicate([first, duplicate])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Titular original")
        self.assertEqual(data[0]["sources"], ["Medio A", "Medio B"])

    def test_does_not_change_inputs_and_is_idempotent(self):
        item = {"link": "https://ejemplo.org/noticia", "title": "Uno", "sources": ["A"]}
        first = deduplicate([item])
        self.assertEqual(deduplicate(first), first)
        self.assertEqual(item["sources"], ["A"])

    def test_rejects_invalid_url(self):
        with self.assertRaises(ValueError):
            canonical_key("javascript:alert(1)")


if __name__ == "__main__":
    unittest.main()
