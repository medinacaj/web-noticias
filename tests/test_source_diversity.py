"""Diversidad editorial estable, conservando los candidatos originales."""
from collections import Counter
from copy import deepcopy
import unittest

from scripts.source_diversity import diverse_prefix, publisher_key


def story(publisher, number, **fields):
    return {"title": f"Noticia {number}", "sources": [publisher], **fields}


class PublisherKeyTests(unittest.TestCase):
    def test_source_domain_precedes_direct_link_and_primary_name(self):
        article = story("Otro nombre", 1, source_url="https://www.editor.example/rss",
                        link="https://different.example/article")
        self.assertEqual(publisher_key(article), "editor.example")

    def test_direct_link_fallback_groups_www(self):
        a = story("Nombre A", 1, link="https://www.editor.example/one")
        b = story("Nombre B", 2, link="https://editor.example/two")
        self.assertEqual(publisher_key(a), publisher_key(b))

    def test_google_urls_fall_back_to_primary_publisher_name(self):
        a = story("Medio A", 1, source_url="https://news.google.com/rss",
                  link="https://news.google.com/articles/one")
        b = story("Medio B", 2, link="https://news.google.com/articles/two")
        self.assertEqual(publisher_key(a), publisher_key(story("  MEDIO A  ", 3)))
        self.assertNotEqual(publisher_key(a), publisher_key(b))
        self.assertNotIn("google", publisher_key(a))

    def test_google_source_url_does_not_hide_a_direct_editorial_link(self):
        article = story("Nombre", 1, source_url="https://news.google.com/rss",
                        link="https://editor.example/one")
        self.assertEqual(publisher_key(article), "editor.example")

    def test_bbc_aliases_share_one_editor(self):
        versions = [story(name, i) for i, name in enumerate(("BBC", "BBC News Mundo"))]
        versions.extend(story("Otro nombre", i, source_url=url) for i, url in enumerate((
            "https://www.bbc.com/mundo", "https://www.bbc.co.uk/mundo")))
        self.assertEqual({publisher_key(article) for article in versions}, {"bbc.com"})

    def test_biobio_aliases_share_one_editor(self):
        versions = [story(name, i) for i, name in enumerate(("BioBioChile", "Bio Bio"))]
        versions.append(story("Otro nombre", 3, source_url="https://www.biobiochile.cl/"))
        self.assertEqual({publisher_key(article) for article in versions}, {"biobiochile.cl"})

    def test_secondary_sources_do_not_determine_primary_identity(self):
        article = {"sources": ["Medio A", "BBC News Mundo", "Bio Bio"]}
        self.assertEqual(publisher_key(article), publisher_key(story("Medio A", 1)))
        self.assertNotEqual(publisher_key(article), publisher_key(story("BBC", 2)))


class DiversePrefixTests(unittest.TestCase):
    def test_six_slots_are_shared_two_each_in_rank_order(self):
        candidates = [story(name, i) for name in ("A", "B", "C") for i in range(4)]
        result = diverse_prefix(candidates, 6)
        self.assertEqual(result, [candidates[i] for i in (0, 1, 4, 5, 8, 9)])
        self.assertEqual(Counter(publisher_key(item) for item in result), {"a": 2, "b": 2, "c": 2})

    def test_one_editor_fills_all_slots_in_original_order(self):
        candidates = [story("A", i) for i in range(8)]
        self.assertEqual(diverse_prefix(candidates, 6), candidates[:6])

    def test_initial_counts_reserve_lead_editor_before_fallback(self):
        candidates = [story("A", i) for i in range(3)] + [story("B", 3), story("C", 4)]
        counts = {publisher_key(candidates[0]): 1}
        result = diverse_prefix(candidates, 4, max_per_source=1, initial_counts=counts)
        self.assertEqual(result, [candidates[i] for i in (3, 4, 0, 1)])
        self.assertEqual(counts, {"a": 1})

    def test_candidates_and_nested_data_remain_unchanged_and_available(self):
        candidates = [story(name, i) for i, name in enumerate(("A", "A", "A", "B"))]
        before = deepcopy(candidates)
        result = diverse_prefix(candidates, 2, max_per_source=1)
        self.assertEqual(candidates, before)
        self.assertEqual(len(candidates), 4)
        self.assertIs(result[0], candidates[0])
        self.assertIs(result[1], candidates[3])
        self.assertEqual(diverse_prefix(candidates, 10), [candidates[i] for i in (0, 1, 3, 2)])

    def test_empty_or_zero_sized_selection_is_empty(self):
        self.assertEqual(diverse_prefix([], 6), [])
        self.assertEqual(diverse_prefix([story("A", 1)], 0), [])


if __name__ == "__main__":
    unittest.main()
