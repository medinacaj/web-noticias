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

    def test_menu_exposes_grouped_topics_and_lead_only_category(self):
        from scripts.presentation_groups import group_sections
        now = datetime(2026, 10, 25, tzinfo=timezone.utc)
        def article(category, i):
            return {'title': f'Nota {category} {i}', 'category': category, 'sources': [f'Medio {i}'],
                    'link': f'https://medio.example/{category}/{i}', 'published': now.isoformat(), 'image': '', 'summary': ''}
        topics = ['deportes'] + ['nacional'] * 4 + ['medioambiente'] * 3 + ['tecnologia'] * 4 + ['salud-ciencia'] * 3
        stories = [article(category, i) for i, category in enumerate(topics)]
        sel = news.select(stories, now)
        sel['by_category'] = group_sections(sel['by_category'])
        menu = PageInspector(); menu.feed(news.render_nav(sel))
        html = news.render_top(sel, now) + news.render_sections(sel['by_category'], now)
        body = PageInspector(); body.feed(html)
        hrefs = {a.get('href') for a in menu.anchors}
        # Salud vive dentro de «Ciencia y tecnología»: sin entrada aparte en el menú (2026-10-25).
        for topic in set(topics) - {'salud-ciencia'}:
            self.assertIn('#cat-' + topic, hrefs)
        self.assertNotIn('#cat-salud-ciencia', hrefs)
        for href in hrefs:
            self.assertIn(href[1:], body.ids)
        self.assertEqual(len(body.ids), len(set(body.ids)))
        nav = news.render_nav(sel)
        self.assertIn('>Medioambiente<', nav)
        self.assertIn('>Ciencia y tecnología<', nav)
        self.assertNotIn('>Salud<', nav)

    def test_health_only_lead_uses_science_menu_and_preserves_legacy_anchor(self):
        from scripts.presentation_groups import group_sections
        now = datetime(2026, 10, 25, tzinfo=timezone.utc)
        story = {'title':'Avance médico', 'category':'salud-ciencia', 'sources':['Medio'],
                 'link':'https://medio.example/salud', 'published':now.isoformat(), 'image':'', 'summary':''}
        sel = news.select([story], now)
        sel['by_category'] = group_sections(sel['by_category'])
        menu = news.render_nav(sel)
        self.assertIn('href="#cat-tecnologia">Ciencia y tecnología</a>', menu)
        self.assertNotIn('href="#cat-salud-ciencia"', menu)
        body = PageInspector(); body.feed(news.render_top(sel, now))
        self.assertIn('cat-tecnologia', body.ids)
        self.assertIn('cat-salud-ciencia', body.ids)
        self.assertEqual(len(body.ids), len(set(body.ids)))

    def test_sections_render_recent_first_without_changing_editorial_input(self):
        from datetime import timedelta
        now = datetime(2026,10,25,15,tzinfo=timezone.utc)
        stories = [{'title':f'Noticia {i}', 'category':'nacional', 'sources':['Medio'],
                    'link':f'https://medio.example/{i}', 'published':(now-timedelta(hours=3-i)).isoformat(),
                    'image':'', 'summary':''} for i in range(3)]
        original = copy.deepcopy(stories)
        parser = PageInspector(); parser.feed(news.render_sections({'nacional':stories}, now))
        self.assertEqual([a['href'] for a in parser.anchors if a.get('data-key') == 'nacional'],
                         [stories[i]['link'] for i in (2,1,0)])
        self.assertEqual(stories, original)

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
        self.assertEqual(parser.sections, ["cat-nacional", "cat-tecnologia", "cat-medioambiente"])
        self.assertIn("Ciencia y tecnología", text)
        self.assertIn("cat-salud-ciencia", parser.ids)
        self.assertIn("cat-medioambiente", parser.ids)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertTrue(any(a.get("data-key") == "salud-ciencia" for a in parser.anchors))
        self.assertTrue(any(a.get("data-key") == "medioambiente" for a in parser.anchors))
        self.assertEqual(stories, before)


if __name__ == "__main__":
    unittest.main()
