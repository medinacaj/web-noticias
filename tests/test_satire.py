"""Sátira separada: identidad del editor, metadatos válidos y salida escapada."""
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

NOW = datetime(2026, 10, 27, 16, tzinfo=timezone.utc)


def entry(index=0, **changes):
    return {'title': f'Titular satírico {index}', 'source': 'El Chigüire Bipolar',
            'source_url': 'https://www.elchiguirebipolar.net',
            'link': f'https://www.elchiguirebipolar.net/27/10/2026/nota-{index}/',
            'published': (NOW - timedelta(hours=1)).isoformat(),
            'summary': 'Texto que no se incorpora', 'image': 'https://cdn.example/foto.jpg',
            **changes}


class SatireTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.satire'),
                             'Falta la separación explícita de sátira')
        return importlib.import_module('scripts.satire')

    def test_exact_publisher_identity_excludes_mentions_and_lookalike_hosts(self):
        satire = self.module()
        for story in ({'source': 'El Chigüire Bipolar'}, {'sources': ['El Chigüire Bipolar']},
                      {'source_url': 'https://www.elchiguirebipolar.net'},
                      {'link': 'https://elchiguirebipolar.net/nota/'}):
            with self.subTest(story=story): self.assertTrue(satire.is_satire(story))
        for story in ({'title': 'El Chigüire Bipolar presenta su edición'},
                      {'source': 'El Chigüire Bipolar Noticias'},
                      {'source_url': 'https://elchiguirebipolar.net.evil.example'},
                      {'link': 'https://evil.example/elchiguirebipolar.net/nota'}):
            with self.subTest(story=story): self.assertFalse(satire.is_satire(story))

    def test_collection_keeps_three_unique_recent_links_without_article_content(self):
        satire = self.module()
        requests = []
        def fetch(url, category, **kwargs):
            requests.append((url, category, kwargs))
            return [entry(0), entry(0, link=entry(0)['link']+'?utm_source=ig'),
                    entry(1, link='https://news.google.com/rss/articles/SATIRA'), entry(2), entry(3)]
        records = satire.collect_satire(NOW, fetch=fetch)
        self.assertEqual([x['title'] for x in records], ['Titular satírico 0', 'Titular satírico 1', 'Titular satírico 2'])
        self.assertTrue(all(x['metadata_only'] and not x['summary'] and not x['image'] for x in records))
        self.assertTrue(all(x['category'] == 'satira' and x['source'] == 'El Chigüire Bipolar' for x in records))
        self.assertEqual(len(requests), 1)
        params = parse_qs(urlsplit(requests[0][0]).query)
        self.assertEqual(params['q'], ['site:elchiguirebipolar.net when:1d'])
        self.assertTrue(requests[0][2]['metadata_only'])

    def test_collection_rejects_spoofed_editor_invalid_links_and_dates_before_limit(self):
        satire = self.module()
        invalid = [entry(source='Otro medio'), entry(source_url='https://evil.example'),
                   entry(source_url='https://www.elchiguirebipolar.net.evil.example'),
                   entry(link='https://otro.example/noticia'), entry(link='javascript:alert(1)'),
                   entry(link='https://news.google.com.evil.example/rss/articles/ABC'),
                   entry(link='https://news.google.com/rss/articles/'),
                   entry(link='https://www.elchiguirebipolar.net/'),
                   entry(link='https://www.elchiguirebipolar.net:444/nota'),
                   entry(link='https://www.elchiguirebipolar.net/nota\nfin'),
                   entry(link='https://www.elchiguirebipolar.net/\\nota'),
                   entry(published=None), entry(published='2026-10-27T15:00:00'),
                   entry(published=(NOW - timedelta(hours=24, seconds=1)).isoformat()),
                   entry(published=(NOW + timedelta(minutes=16)).isoformat()), entry(title='')]
        records = satire.collect_satire(NOW, fetch=lambda *a, **k: invalid + [entry(30)])
        self.assertEqual([x['title'] for x in records], ['Titular satírico 30'])

    def test_failure_is_empty_and_widget_preserves_labelled_official_link(self):
        satire = self.module()
        def unavailable(*args, **kwargs): raise OSError('RSS no disponible')
        self.assertEqual(satire.collect_satire(NOW, fetch=unavailable), [])
        rendered = satire.render_satire([])
        self.assertIn('Sátira', rendered)
        self.assertIn('https://www.elchiguirebipolar.net/', rendered)

    def test_catalog_restriction_prevents_query_even_when_editor_is_satire(self):
        satire = self.module()
        blocked = {'name': 'El Chigüire Bipolar', 'domain': 'elchiguirebipolar.net',
                   'enabled': False, 'permission_status': 'pending'}
        with patch('scripts.regional_sources.load_catalog', return_value=[blocked]):
            records = satire.collect_satire(NOW, fetch=lambda *a, **k: self.fail('Consultó fuente bloqueada'))
        self.assertEqual(records, [])

    def test_widget_escapes_titles_and_links_and_does_not_create_news_cards(self):
        satire = self.module()
        record = entry(title='<img src=x onerror=alert(1)> & humor',
                       link='https://www.elchiguirebipolar.net/nota?tema=a&otro="valor"')
        rendered = satire.render_satire([record])
        self.assertIn('&lt;img src=x onerror=alert(1)&gt; &amp; humor', rendered)
        self.assertIn('&amp;otro=&quot;valor&quot;', rendered)
        self.assertNotIn('<img', rendered)
        self.assertNotIn('data-key=', rendered)
        self.assertNotIn('data-story-id=', rendered)
        self.assertIn('humor', rendered)


if __name__ == '__main__': unittest.main()
