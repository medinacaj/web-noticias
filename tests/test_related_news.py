"""Coberturas adicionales con fecha propia, sin crear noticias ni acuerdos ficticios."""
from datetime import datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import fetch_noticias as news


NOW = datetime(2026, 10, 28, 13, tzinfo=timezone.utc)
GOOGLE = 'https://news.google.com/rss/articles/'


def rss_item(title, source, domain, token, date='Wed, 28 Oct 2026 12:00:00 GMT', description=''):
    return ('<item><title>' + escape(title + ' - ' + source) + '</title><link>'
            + GOOGLE + token + '</link><source url="https://' + domain + '">'
            + escape(source) + '</source><pubDate>' + escape(date) + '</pubDate>'
            + '<description>' + escape(description) + '</description></item>')


def cluster():
    rows = [('Choque de trenes en España deja personas heridas', 'BioBioChile', 'main'),
            ('España: choque entre trenes provoca una emergencia', 'CNN Chile', 'cnn'),
            ('Imágenes del choque de trenes en España', 'Teletrece', 't13')]
    return '<ol>' + ''.join('<li><a href="' + GOOGLE + token + '">' + title
                           + '</a><font>' + source + '</font></li>' for title, source, token in rows) + '</ol>'


class RelatedDeliveryTests(unittest.TestCase):
    def collect_fixture(self, children, main=None):
        world = news.category_google_url(next(c for c in news.CATEGORIES if c['key'] == 'internacional'))
        main = main or rss_item('Choque de trenes en España deja personas heridas', 'BioBioChile',
                               'www.biobiochile.cl', 'main', description=cluster())
        queries = []

        def response(url):
            query = parse_qs(urlsplit(url).query).get('q', [''])[0]
            if url == world:
                body = main
            elif all(word in query for word in ('choque', 'espana', 'trenes')):
                queries.append(query)
                if isinstance(children, Exception):
                    raise children
                body = children
            else:
                body = ''
            return '<rss><channel>' + body + '</channel></rss>'

        with patch.object(news, 'GNEWS_API_KEY', ''), patch.object(news, 'http_get', side_effect=response):
            items = news.collect(NOW)
        return items, queries

    def test_cluster_coverages_survive_history_and_render_without_extra_news(self):
        children = (rss_item('España: choque entre trenes provoca una emergencia', 'CNN Chile',
                             'www.cnnchile.com', 'cnn', 'Wed, 28 Oct 2026 10:55:00 GMT')
                    + rss_item('Imágenes del choque de trenes en España', 'Teletrece',
                               'www.t13.cl', 't13', 'Wed, 28 Oct 2026 11:05:00 GMT'))
        items, queries = self.collect_fixture(children)
        self.assertEqual(len(queries), 1)
        stories = []
        news.merge(stories, items, NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]['sources'], ['BioBioChile'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, 'history.json')
            news.save_history(path, stories, NOW)
            loaded = news.load_history(path)
            related = loaded[0].get('related_coverages', [])
            self.assertEqual({row['source'] for row in related}, {'CNN Chile', 'Teletrece'})
            self.assertEqual({row['published'] for row in related},
                             {'2026-10-28T10:55:00Z', '2026-10-28T11:05:00Z'})
            self.assertEqual(news.coverage_items(loaded[0]), [])
            news.build_site(loaded, NOW, folder)
            html = Path(folder, 'index.html').read_text()
            self.assertIn('Otras coberturas', html)
            self.assertIn('datetime="2026-10-28T10:55:00Z">hace 2 h</time>', html)
            for title in ('España: choque entre trenes provoca una emergencia',
                          'Imágenes del choque de trenes en España'):
                self.assertIn(title, html)
                self.assertNotIn(title, Path(folder, 'rss.xml').read_text())
                schema = html.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
                self.assertNotIn(title, schema)
            self.assertNotIn('_coverage_cluster', path.read_text())

    def test_related_links_require_dates_sources_and_topic_relevance(self):
        title = 'España: nuevas imágenes del choque de trenes'
        children = rss_item(title, 'CNN Chile', 'www.cnnchile.com', 'valid')
        children += rss_item(title, 'Sin fecha', 'sinf.example', 'nodate', '')
        children += rss_item(title, 'Antiguo', 'old.example', 'old', 'Mon, 26 Oct 2026 12:00:00 GMT')
        children += rss_item(title, 'Futuro', 'future.example', 'future', 'Wed, 28 Oct 2026 14:00:00 GMT')
        children += rss_item(title, 'Alias CNN', 'cnnespanol.cnn.com', 'blocked')
        children += rss_item('España gana un campeonato de fútbol', 'Otro tema', 'sports.example', 'unrelated')
        children += rss_item(title, 'Enlace inseguro', 'unsafe.example', 'unsafe').replace(
            GOOGLE + 'unsafe', 'https://user@news.google.com/rss/articles/unsafe')
        items, _ = self.collect_fixture(children)
        related = items[0].get('related_coverages', [])
        self.assertEqual([row['source'] for row in related], ['CNN Chile'])

    def test_one_link_per_editor_and_related_budget_do_not_inflate_sources(self):
        children = ''.join(rss_item(f'España: imágenes del choque de trenes {i}',
                                   'Editor ' + str(i // 2), f'editor{i // 2}.example', 'ref' + str(i))
                           for i in range(32))
        items, queries = self.collect_fixture(children)
        self.assertEqual(len(queries), 1)
        self.assertEqual(len(items[0].get('related_coverages', [])), 10)
        self.assertEqual(len({row['source'] for row in items[0]['related_coverages']}), 10)
        stories = []
        news.merge(stories, items, NOW)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]['sources'], ['BioBioChile'])

    def test_failed_related_lookup_keeps_the_main_news(self):
        items, queries = self.collect_fixture(OSError('fuente temporalmente caída'))
        self.assertEqual(len(queries), 1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source'], 'BioBioChile')
        self.assertFalse(items[0].get('related_coverages'))

    def test_publishers_in_the_original_cluster_keep_a_place_in_related_links(self):
        children = ''.join(rss_item('España: imágenes del choque de trenes',
                                   'Editor ' + str(i), f'editor{i}.example', 'ref' + str(i))
                           for i in range(15))
        children += rss_item('Imágenes del choque de trenes en España', 'Teletrece',
                             'www.t13.cl', 't13')
        items, _ = self.collect_fixture(children)
        self.assertIn('Teletrece', [row['source'] for row in items[0].get('related_coverages', [])])

    def test_bad_saved_metadata_does_not_break_the_dialog_or_inherit_dates(self):
        story = {'title': 'Choque de trenes en España', 'category': 'internacional',
                 'link': GOOGLE + 'parent', 'source_url': 'https://www.biobiochile.cl',
                 'sources': ['BioBioChile'], 'published': NOW.isoformat(),
                 'related_coverages': [
                     {'title': 'Otra cobertura', 'sources': 123, 'link': GOOGLE + 'broken',
                      'source_url': 'https://www.t13.cl', 'published': NOW.isoformat()},
                     {'title': 'Sin fecha propia', 'source': 'Teletrece', 'link': GOOGLE + 'noDate',
                      'source_url': 'https://www.t13.cl'}]}
        self.assertEqual(news.coverage_control(story, NOW), '')

    def test_malformed_related_containers_are_ignored(self):
        for value in (12, 'texto', {'source': 'Medio'}, [None, 12, 'texto']):
            with self.subTest(value=value):
                self.assertEqual(news.coverage_control({'related_coverages': value}, NOW), '')

    def test_related_references_survive_canonical_url_deduplication(self):
        from scripts.dedupe_history import deduplicate
        children = rss_item('Imágenes del choque de trenes en España', 'Teletrece',
                            'www.t13.cl', 't13')
        items, _ = self.collect_fixture(children)
        stories = []
        news.merge(stories, items, NOW)
        first = {**stories[0], 'link': 'https://www.biobiochile.cl/nota'}
        first.pop('related_coverages', None)
        second = {**stories[0], 'link': first['link'] + '?utm_source=rss'}
        result = deduplicate([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual([row['source'] for row in result[0].get('related_coverages', [])], ['Teletrece'])

    def test_repeated_related_lookup_does_not_renew_a_publication_date(self):
        child = rss_item('España: imágenes del choque de trenes', 'CNN Chile',
                         'www.cnnchile.com', 'same', 'Wed, 28 Oct 2026 10:00:00 GMT')
        variants = [child, child.replace('10:00:00 GMT', '12:00:00 GMT')]
        for order in (variants, list(reversed(variants))):
            with self.subTest(order=order):
                stories = []
                for xml in order:
                    items, _ = self.collect_fixture(xml)
                    news.merge(stories, items, NOW)
                self.assertEqual(stories[0].get('related_coverages', [{}])[0].get('published'),
                                 '2026-10-28T10:00:00Z')

    def test_queries_follow_other_topics_and_respect_two_lookup_budget(self):
        records = []
        for country, noun in [('Francia', 'incendio'), ('Japón', 'terremoto'), ('Italia', 'inundación')]:
            titles = [(f'El {noun} afecta a {country}', 'A'),
                      (f'Grave {noun} golpea a {country}', 'B'),
                      (f'Consecuencias del {noun} en {country}', 'C')]
            token = country.replace('ó', 'o')
            description = '<ol>' + ''.join('<li><a href="' + GOOGLE + token + source + '">'
                          + title + '</a><font>' + source + '</font></li>' for title, source in titles) + '</ol>'
            records.append(rss_item(titles[0][0], 'BioBioChile', 'www.biobiochile.cl',
                                    token, description=description))
        calls = []
        world = news.category_google_url(next(c for c in news.CATEGORIES if c['key'] == 'internacional'))

        def response(url):
            query = parse_qs(urlsplit(url).query).get('q', [''])[0]
            if any(word in query for word in ('incendio', 'terremoto', 'inundacion')):
                calls.append(query)
            body = ''.join(records) if url == world else ''
            return '<rss><channel>' + body + '</channel></rss>'

        with patch.object(news, 'GNEWS_API_KEY', ''), patch.object(news, 'http_get', side_effect=response):
            news.collect(NOW)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all('when:1d' in query for query in calls))
        self.assertFalse(any('trenes' in query or any(ch.isdigit() for ch in query.replace('when:1d', ''))
                             for query in calls))


if __name__ == '__main__':
    unittest.main()
