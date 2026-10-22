"""La agrupación visual conserva datos de origen, filtros y anclas antiguas."""
import copy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest

import fetch_noticias as news


class PageInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.anchors = []
        self.ids = []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "section" and "section" in data.get("class", "").split():
            self.sections.append(data["id"])
        if tag == "a":
            self.anchors.append(data)


class GroupedSiteTests(unittest.TestCase):
    def test_search_metadata_includes_sources_omitted_from_visible_label(self):
        story = {"category": "nacional", "title": "Una noticia de varios medios",
                 "link": "https://medio.example/nota", "sources": ["A", "B", "C", 'D "&']}
        parser = PageInspector()
        parser.feed(news.title_link(story))
        self.assertEqual(json.loads(parser.anchors[0]["data-sources"]), story["sources"])

    def test_generation_groups_sections_and_preserves_original_categories(self):
        now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
        stories = []
        for category, count in (("nacional", 35), ("tecnologia", 15),
                                ("salud-ciencia", 4), ("medioambiente", 4)):
            for i in range(count):
                stories.append({"title": f"Noticia {category} número {i}", "category": category,
                                "sources": [f"Editor {i}"], "published": now.isoformat(),
                                "link": f"https://medio{i}.example/{category}/{i}",
                                "image": "", "summary": ""})
        before = copy.deepcopy(stories)
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, now, folder)
            text = Path(folder, "index.html").read_text()
        parser = PageInspector();parser.feed(text)
        self.assertEqual(parser.sections, ["cat-nacional", "cat-tecnologia"])
        self.assertIn("Ciencia, salud y tecnología", text)
        self.assertIn("cat-salud-ciencia", parser.ids)
        self.assertIn("cat-medioambiente", parser.ids)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertTrue(any(a.get("data-key") == "salud-ciencia" for a in parser.anchors))
        self.assertTrue(any(a.get("data-key") == "medioambiente" for a in parser.anchors))
        self.assertEqual(stories, before)


if __name__ == "__main__":
    unittest.main()
