"""Entretenimiento internacional con metadatos originales y sin red en tests."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import fetch_noticias as news

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def entry(index=0, **changes):
    return {"title": f"Artista presenta película internacional {index}", "category": "cultura",
            "link": f"https://medio{index}.example/articulo/{index}",
            "source": f"Medio {index}", "source_url": f"https://medio{index}.example",
            "published": (NOW - timedelta(hours=1)).isoformat(),
            "summary": "Extracto que no debe copiarse", "image": "https://medio.example/foto.jpg", **changes}


class EntertainmentTests(unittest.TestCase):
    def test_editions_outside_chile_preserve_metadata_only_and_limit_work(self):
        from scripts.entertainment import collect_entertainment
        calls = []
        def fetch(url, category, **kwargs):
            calls.append((url, category, kwargs))
            return [entry(i) for i in range(20)]
        items = collect_entertainment(NOW, fetch=fetch)
        # Ediciones ES y MX más dos búsquedas temáticas en Chile (cine y conciertos).
        self.assertEqual(len(calls), 4)
        self.assertEqual({parse_qs(urlsplit(url).query)['gl'][0] for url, _, _ in calls}, {'ES', 'MX', 'CL'})
        self.assertTrue(all(kwargs.get('metadata_only') for _, _, kwargs in calls))
        self.assertLessEqual(len(items), 24)  # hasta seis por edición o búsqueda
        self.assertTrue(items)
        self.assertTrue(all(item['category'] == 'cultura' and item['metadata_only']
                            and item['summary'] == item['image'] == '' for item in items))
        self.assertTrue(all(item['published'] == entry()['published'] for item in items))

    def test_failure_of_one_edition_does_not_drop_the_other(self):
        from scripts.entertainment import collect_entertainment
        calls = []
        def fetch(url, *args, **kwargs):
            calls.append(url)
            if len(calls) == 1: raise OSError('feed down')
            return [entry()]
        self.assertEqual(len(collect_entertainment(NOW, fetch=fetch)), 1)
        self.assertEqual(len(calls), 4)

    def test_invalid_dates_links_and_restricted_editors_are_not_accepted(self):
        from scripts.entertainment import collect_entertainment
        invalid = [entry(published=None), entry(published='2026-10-24T11:00:00'),
                   entry(published=(NOW - timedelta(days=2)).isoformat()),
                   entry(published=(NOW + timedelta(hours=1)).isoformat()),
                   entry(link='https://127.0.0.1/private'), entry(source_url='https://localhost'),
                   entry(link='javascript:alert(1)'), entry(title=''),
                   entry(link='https://medio0.example/'),
                   entry(link='https://otro.example/articulo'),
                   entry(link='https://medio0.example/\\articulo'),
                   entry(link='https://medio0.example/arti\nculo'),
                   entry(source_url='https://www.theguardian.com', link='https://www.theguardian.com/culture/a')]
        self.assertEqual(collect_entertainment(NOW, fetch=lambda *a, **kw: invalid), [])

    def test_regional_and_world_catalog_gates_apply_to_new_editions(self):
        from scripts.entertainment import collect_entertainment
        for domain in ('milenio.com', 'infobae.com', 'elnacional.com', 'reuters.com', 'theguardian.com'):
            with self.subTest(domain=domain):
                item = entry(link=f'https://{domain}/cultura/articulo', source_url=f'https://{domain}')
                self.assertEqual(collect_entertainment(NOW, fetch=lambda *a, **kw: [item]), [])

    def test_collection_is_integrated_without_more_gnews_requests(self):
        with patch.object(news, 'GNEWS_API_KEY', ''), patch.object(news, 'fetch_rss', return_value=[]), \
             patch('scripts.entertainment.collect_entertainment', return_value=[entry()]) as extra, \
             patch('scripts.global_sources.collect_world', return_value=[]), \
             patch('scripts.regional_sources.collect_regional', return_value=[]), \
             patch.object(news, 'fetch_gnews') as gnews:
            self.assertEqual(news.collect(NOW), [entry()])
            extra.assert_called_once()
            gnews.assert_not_called()

    def test_edition_survives_merge_reload_and_balances_first_six(self):
        from scripts.entertainment import balance_entertainment
        local = [{**entry(i), 'sources': [f'Medio {i}']} for i in range(8)]
        foreign = [entry(i, discovery_edition='ES', metadata_only=True) for i in range(10, 14)]
        stories = list(local)
        news.merge(stories, foreign, NOW)
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'history.json')
            news.save_history(path, stories, NOW)
            loaded = news.load_history(path)
        selected = balance_entertainment(loaded, 24)
        self.assertEqual(len(selected), 12)
        self.assertEqual(sum(s.get('discovery_edition') in ('ES', 'MX') for s in selected[:6]), 3)
        self.assertEqual({s['link'] for s in selected}, {s['link'] for s in loaded})
        visible = news.select(loaded, NOW)['by_category']['cultura'][:6]
        self.assertGreaterEqual(sum(s.get('discovery_edition') in ('ES', 'MX') for s in visible), 3)

    def test_no_international_items_does_not_remove_local_stories(self):
        from scripts.entertainment import balance_entertainment
        stories = [{**entry(i), 'sources': ['Medio']} for i in range(8)]
        self.assertEqual(len(balance_entertainment(stories, 24)), 8)
        self.assertEqual(len(balance_entertainment(stories, 2)), 2)


class FilmAndConcertSearchTests(unittest.TestCase):
    def test_chile_searches_cover_film_and_concerts_and_stay_in_cultura(self):
        from scripts.entertainment import collect_entertainment, SEARCHES
        calls = []
        def fetch(url, category, **kwargs):
            calls.append(url)
            return [entry(len(calls) * 10 + i) for i in range(3)]
        items = collect_entertainment(NOW, fetch=fetch)
        searches = [parse_qs(urlsplit(url).query) for url in calls if "/rss/search" in url]
        self.assertEqual(len(searches), len(SEARCHES))
        self.assertTrue(any("cine" in q["q"][0] for q in searches))
        self.assertTrue(any("concierto" in q["q"][0] for q in searches))
        self.assertTrue(all(q["gl"] == ["CL"] for q in searches))
        labels = {item["discovery_edition"] for item in items}
        self.assertTrue({"CL-CINE", "CL-CONCIERTOS"} <= labels)
        self.assertTrue(all(item["category"] == "cultura" and item["metadata_only"] for item in items))


if __name__ == '__main__': unittest.main()
