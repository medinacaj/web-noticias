"""Últimas noticias: orden real, enlaces distintos y degradación sin JavaScript."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import unittest
import tempfile
from pathlib import Path
from fetch_noticias import build_site

from fetch_noticias import render_breaking, select, merge

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def story(index, **changes):
    return {"category": "cultura", "title": f"Artista presenta obra {index}",
            "link": f"https://medio.example/cultura/{index}", "sources": ["Medio"],
            "published": (NOW - timedelta(minutes=index)).isoformat(), **changes}


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "a": self.links.append(dict(attrs)["href"])


class LatestCarouselTests(unittest.TestCase):
    def test_generated_page_references_an_existing_reader_script(self):
        with tempfile.TemporaryDirectory() as folder:
            build_site([story(0, summary="", image="")], NOW, folder)
            page = Path(folder, 'index.html').read_text()
            import re
            for asset in re.findall(r'<script src="([^"]+)"', page):
                self.assertTrue(Path(folder, asset).is_file(), asset)

    def test_three_latest_distinct_links_available_without_js(self):
        stories = [story(i) for i in range(7, -1, -1)]
        selection = select(stories, NOW)
        rendered = render_breaking(selection, NOW)
        self.assertEqual(Links(rendered).links, [story(i)["link"] for i in range(6)])
        self.assertIn('data-carousel', rendered)

    def test_repeated_url_is_not_a_second_slide(self):
        stories = [story(0), story(1, link=story(0)["link"]), story(2), story(3)]
        rendered = render_breaking(select(stories, NOW), NOW)
        self.assertEqual(Links(rendered).links, [story(i)["link"] for i in (0, 2, 3)])

    def test_no_phantom_stories_with_one_item_or_empty_selection(self):
        self.assertEqual(Links(render_breaking(select([story(0)], NOW), NOW)).links,
                         [story(0)["link"]])
        self.assertEqual(render_breaking(select([], NOW), NOW), "")

    def test_merge_first_seen_does_not_make_an_undated_article_recent(self):
        records = []
        merge(records, [story(0, published=None, title="Cantante anuncia una gira mundial"),
                        story(5, title="Festival de cine revela las películas seleccionadas")], NOW)
        self.assertIsNone(records[0].get("published"))
        self.assertIsNotNone(records[0].get('first_seen'))
        rendered = render_breaking(select(records, NOW), NOW)
        self.assertEqual(Links(rendered).links, [story(5)['link']])

    def test_missing_time_does_not_outrank_dated_news(self):
        stories = [story(0, published=None), story(1), story(2)]
        rendered = render_breaking(select(stories, NOW), NOW)
        self.assertEqual(Links(rendered).links, [story(1)["link"], story(2)["link"]])




class EditionCountTests(unittest.TestCase):
    def test_count_uses_published_cards_and_deduplicates_urls(self):
        from fetch_noticias import render_edition_count
        import re
        first = story(0, sources=['Medio', 'Otro'])
        repeated = story(0, sources=['Medio', 'Extra'])
        second = story(1)
        selection = {'lead': first, 'secondary': [repeated],
                     'by_category': {'cultura': [second]},
                     'total': 400, 'outlets': 90, 'latest': [story(2)]}
        text = re.sub('<[^>]+>', '', render_edition_count(selection))
        self.assertEqual(text, '2 noticias · 3 medios')

    def test_singular_and_empty_counts(self):
        from fetch_noticias import render_edition_count
        import re
        for selection, expected in (
            ({'lead': story(0), 'secondary': [], 'by_category': {}}, '1 noticia · 1 medio'),
            ({'lead': None, 'secondary': [], 'by_category': {}}, '0 noticias · 0 medios'),
        ):
            self.assertEqual(re.sub('<[^>]+>', '', render_edition_count(selection)), expected)

if __name__ == "__main__": unittest.main()
