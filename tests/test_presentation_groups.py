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

    def test_four_health_stories_survive_full_science_section(self):
        technology = stories("tecnologia", 35)
        health = stories("salud-ciencia", 4)
        result = group_sections({"tecnologia": technology, "salud-ciencia": health})
        self.assertEqual(result["tecnologia"], technology[:20] + health)
        self.assertEqual(len(result["tecnologia"]), 24)

    def test_environment_is_its_own_section(self):
        # Decisión del usuario (2026-10-25): Medioambiente no se integra en Nacional.
        national = stories("nacional", 3)
        climate = stories("medioambiente", 2)
        result = group_sections({"nacional": national, "medioambiente": climate})
        self.assertEqual(result, {"nacional": national, "medioambiente": climate})

    def test_group_uses_earliest_member_position_without_overwriting(self):
        science = stories("salud-ciencia", 2)
        technology = stories("tecnologia", 3)
        national = stories("nacional", 2)
        result = group_sections({
            "economia": [], "salud-ciencia": science, "deportes": [],
            "tecnologia": technology, "nacional": national, "cultura": [],
        })
        self.assertEqual(list(result), [
            "economia", "tecnologia", "deportes", "nacional", "cultura",
        ])
        self.assertEqual(result["tecnologia"], technology + science)

    def test_missing_destination_still_displays_all_available_subtopic(self):
        science = stories("salud-ciencia", 12)
        result = group_sections({"salud-ciencia": science})
        self.assertEqual(result["tecnologia"], science)

    def test_extra_subtopic_fills_remaining_room_in_relevance_order(self):
        technology = stories("tecnologia", 2)
        health = stories("salud-ciencia", 30)
        result = group_sections({"tecnologia": technology, "salud-ciencia": health})
        self.assertEqual(result["tecnologia"], technology + health[:22])

    def test_custom_limit_reserves_available_subtopic_and_caps_other_sections(self):
        technology = stories("tecnologia", 10)
        health = stories("salud-ciencia", 10)
        sports = stories("deportes", 10)
        result = group_sections({"tecnologia": technology, "salud-ciencia": health,
                                 "deportes": sports}, limit=6)
        self.assertEqual(result["tecnologia"], technology[:2] + health[:4])
        self.assertEqual(result["deportes"], sports[:6])

    def test_repeated_object_is_not_cloned_and_equal_distinct_stories_survive(self):
        shared = stories("tecnologia", 1)[0]
        equal_but_distinct = dict(shared)
        health = stories("salud-ciencia", 4)
        result = group_sections({"tecnologia": [shared, shared, equal_but_distinct],
                                 "salud-ciencia": [shared] + health})
        self.assertEqual(len(result["tecnologia"]), 6)
        self.assertEqual(sum(item is shared for item in result["tecnologia"]), 1)
        self.assertTrue(any(item is equal_but_distinct for item in result["tecnologia"]))

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
        self.assertEqual(canonical_section("medioambiente"), "medioambiente")
        self.assertEqual(canonical_section("cultura"), "cultura")
        # Un solo nombre por tema: los rótulos vienen de CATEGORIES.
        self.assertEqual(PRESENTATION_LABELS, {})


if __name__ == "__main__":
    unittest.main()
