"""Presentation groups preserve the original editorial records."""
import copy
import unittest

from scripts.presentation_groups import (
    PRESENTATION_LABELS, canonical_section, group_sections,
)


def stories(category, count):
    return [{"category": category, "link": f"/{category}/{i}"}
            for i in range(count)]


class PresentationGroupsTests(unittest.TestCase):
    def test_science_and_technology_fit_without_losing_stories(self):
        technology = stories("tecnologia", 15)
        science = stories("salud-ciencia", 4)
        result = group_sections({"tecnologia": technology, "salud-ciencia": science})
        self.assertEqual(list(result), ["tecnologia"])
        self.assertEqual(result["tecnologia"], technology + science)

    def test_four_climate_stories_survive_full_national_section(self):
        national = stories("nacional", 35)
        climate = stories("medioambiente", 4)
        result = group_sections({"nacional": national, "medioambiente": climate})
        self.assertEqual(result["nacional"], national[:20] + climate)
        self.assertEqual(len(result["nacional"]), 24)

    def test_group_uses_earliest_member_position_without_overwriting(self):
        science = stories("salud-ciencia", 2)
        technology = stories("tecnologia", 3)
        national = stories("nacional", 2)
        climate = stories("medioambiente", 1)
        result = group_sections({
            "economia": [], "salud-ciencia": science, "deportes": [],
            "medioambiente": climate, "tecnologia": technology,
            "nacional": national, "cultura": [],
        })
        self.assertEqual(list(result), [
            "economia", "tecnologia", "deportes", "nacional", "cultura",
        ])
        self.assertEqual(result["tecnologia"], technology + science)
        self.assertEqual(result["nacional"], national + climate)

    def test_missing_destination_still_displays_all_available_subtopic(self):
        science = stories("salud-ciencia", 12)
        result = group_sections({"salud-ciencia": science})
        self.assertEqual(result["tecnologia"], science)

    def test_extra_subtopic_fills_remaining_room_in_relevance_order(self):
        national = stories("nacional", 2)
        climate = stories("medioambiente", 30)
        result = group_sections({"nacional": national, "medioambiente": climate})
        self.assertEqual(result["nacional"], national + climate[:22])

    def test_custom_limit_reserves_available_subtopic_and_caps_other_sections(self):
        national = stories("nacional", 10)
        climate = stories("medioambiente", 10)
        sports = stories("deportes", 10)
        result = group_sections({"nacional": national, "medioambiente": climate,
                                 "deportes": sports}, limit=6)
        self.assertEqual(result["nacional"], national[:2] + climate[:4])
        self.assertEqual(result["deportes"], sports[:6])

    def test_repeated_object_is_not_cloned_and_equal_distinct_stories_survive(self):
        shared = stories("nacional", 1)[0]
        equal_but_distinct = dict(shared)
        climate = stories("medioambiente", 4)
        result = group_sections({"nacional": [shared, shared, equal_but_distinct],
                                 "medioambiente": [shared] + climate})
        self.assertEqual(len(result["nacional"]), 6)
        self.assertEqual(sum(item is shared for item in result["nacional"]), 1)
        self.assertTrue(any(item is equal_but_distinct for item in result["nacional"]))
        self.assertTrue(all(any(item is original for original in
                               [shared, equal_but_distinct] + climate)
                            for item in result["nacional"]))

    def test_input_and_original_categories_are_unchanged(self):
        data = {"salud-ciencia": stories("salud-ciencia", 4),
                "tecnologia": stories("tecnologia", 15)}
        before = copy.deepcopy(data)
        result = group_sections(data)
        self.assertEqual(data, before)
        self.assertIsNot(result, data)
        self.assertIsNot(result["tecnologia"], data["tecnologia"])
        self.assertEqual(sum(s["category"] == "salud-ciencia"
                             for s in result["tecnologia"]), 4)

    def test_empty_input_and_zero_limit(self):
        self.assertEqual(group_sections({}), {})
        self.assertEqual(group_sections({"nacional": stories("nacional", 2)},
                                        limit=0), {"nacional": []})

    def test_canonical_sections_and_labels_only_change_presentation(self):
        self.assertEqual(canonical_section("salud-ciencia"), "tecnologia")
        self.assertEqual(canonical_section("medioambiente"), "nacional")
        self.assertEqual(canonical_section("cultura"), "cultura")
        self.assertEqual(PRESENTATION_LABELS["tecnologia"],
                         "Ciencia, salud y tecnología")
        self.assertEqual(PRESENTATION_LABELS["nacional"], "Nacional")


if __name__ == "__main__":
    unittest.main()
