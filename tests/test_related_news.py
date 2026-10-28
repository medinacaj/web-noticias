"""Coberturas adicionales con fecha propia, sin crear noticias ni acuerdos ficticios."""
from datetime import datetime, timedelta, timezone
from html import escape
import json
import sys
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

    def test_dialog_never_assigns_the_groups_earliest_date_to_the_primary_editor(self):
        children = (rss_item('España: imágenes del choque de trenes', 'CNN Chile',
                             'www.cnnchile.com', 'cnn')
                    + rss_item('España: nuevas imágenes del choque de trenes', 'Teletrece',
                               'www.t13.cl', 't13', 'Wed, 28 Oct 2026 11:15:00 GMT'))
        items, _ = self.collect_fixture(children)
        stories = []
        news.merge(stories, items, NOW)
        news.merge(stories, [{'category': 'internacional', 'title': stories[0]['title'],
                             'source': 'Teletrece', 'source_url': 'https://www.t13.cl',
                             'link': GOOGLE + 't13earlier', 'published': '2026-10-28T11:00:00Z'}], NOW)
        self.assertEqual(stories[0]['published'], '2026-10-28T11:00:00Z')
        dialog = news.coverage_control(stories[0], NOW)
        self.assertNotIn('class="coverage-source">BioBioChile</span>', dialog)
        self.assertIn('class="coverage-source">Teletrece</span>', dialog)
        self.assertIn('datetime="2026-10-28T11:15:00Z"', dialog)

    def test_satire_is_excluded_from_collected_and_saved_references(self):
        satire = rss_item('España: imágenes del choque de trenes', 'El Chigüire Bipolar',
                          'www.elchiguirebipolar.net', 'satire')
        items, _ = self.collect_fixture(satire)
        self.assertFalse(items[0].get('related_coverages'))
        stories = []
        incoming = {**items[0], 'related_coverages': [
            {'title': 'España: imágenes del choque de trenes', 'source': 'El Chigüire Bipolar',
             'source_url': 'https://www.elchiguirebipolar.net', 'link': GOOGLE + 'satire',
             'published': NOW.isoformat()}]}
        news.merge(stories, [incoming], NOW)
        self.assertFalse(stories[0].get('related_coverages'))

    def test_a_restricted_cluster_lead_does_not_hide_other_permitted_editors(self):
        description = cluster().replace('</ol>', '<li><a href="' + GOOGLE + 'bbcLive">'
            'Qué se sabe del choque de trenes en España</a><font>BBC</font></li></ol>')
        lead = rss_item('Choque de trenes en España', 'DW.com', 'www.dw.com',
                        'restricted', description=description)
        bbc = rss_item('Qué se sabe del choque de trenes en España', 'BBC News Mundo',
                       'www.bbc.com', 'bbc', 'Wed, 28 Oct 2026 11:01:00 GMT')
        bbc = bbc.replace('<source url="https://www.bbc.com">BBC News Mundo</source>', '')
        bbc = bbc.replace(GOOGLE + 'bbc', 'https://www.bbc.com/mundo/nota')
        extra = (rss_item('España: imágenes del choque de trenes', 'CNN Chile',
                          'www.cnnchile.com', 'cnn')
                 + rss_item('Qué se sabe del choque de trenes en España', 'BBC',
                            'www.bbc.com', 'bbcLive'))
        world = news.category_google_url(next(c for c in news.CATEGORIES if c['key'] == 'internacional'))

        def response(url):
            query = parse_qs(urlsplit(url).query).get('q', [''])[0]
            body = lead if url == world else bbc if 'feeds.bbci.co.uk' in url else (
                extra if all(w in query for w in ('choque', 'espana', 'trenes')) else '')
            return '<rss><channel>' + body + '</channel></rss>'

        with patch.object(news, 'GNEWS_API_KEY', ''), patch.object(news, 'http_get', side_effect=response):
            items = news.collect(NOW)
        allowed = next(item for item in items if item['source'] == 'BBC News Mundo')
        blocked = next(item for item in items if item['source'] == 'DW.com')
        self.assertEqual([row['source'] for row in allowed.get('related_coverages', [])], ['CNN Chile'])
        self.assertFalse(blocked.get('related_coverages'))

    def test_already_published_allowed_story_can_receive_related_references(self):
        description = cluster().replace('</ol>', '<li><a href="' + GOOGLE + 'bbcLive">'
            'Qué se sabe del choque de trenes en España</a><font>BBC</font></li></ol>')
        lead = rss_item('Choque de trenes en España', 'DW.com', 'www.dw.com',
                        'restricted', description=description)
        child = rss_item('España: imágenes del choque de trenes', 'CNN Chile',
                         'www.cnnchile.com', 'cnn')
        world = news.category_google_url(next(c for c in news.CATEGORIES if c['key'] == 'internacional'))

        def response(url):
            query = parse_qs(urlsplit(url).query).get('q', [''])[0]
            body = lead if url == world else child if all(w in query for w in ('choque', 'espana', 'trenes')) else ''
            return '<rss><channel>' + body + '</channel></rss>'

        existing = {'category': 'internacional', 'title': 'Qué se sabe del choque de trenes en España',
                    'link': 'https://www.bbc.com/mundo/nota', 'source_url': 'https://www.bbc.com',
                    'sources': ['BBC News Mundo'], 'published': '2026-10-28T11:01:00Z',
                    'first_seen': '2026-10-28T11:02:00Z', 'image': '', 'summary': ''}
        with tempfile.TemporaryDirectory() as folder:
            history = Path(folder, 'history.json')
            news.save_history(history, [existing], NOW)
            argv = ['fetch_noticias.py', '--historial', str(history), '--salida', str(Path(folder, 'site')),
                    '--ahora', NOW.isoformat()]
            with patch.object(sys, 'argv', argv), patch.object(news, 'GNEWS_API_KEY', ''), \
                 patch.object(news, 'http_get', side_effect=response), \
                 patch('scripts.article_images.enrich_visible_images'), \
                 patch('scripts.agenda.load_agenda', return_value=[]), \
                 patch('scripts.satire.collect_satire', return_value=[]):
                news.main()
            saved = next(item for item in news.load_history(history) if item['link'] == existing['link'])
            self.assertEqual([row['source'] for row in saved.get('related_coverages', [])], ['CNN Chile'])
            self.assertEqual(saved['published'], existing['published'])
            self.assertEqual(saved['first_seen'], existing['first_seen'])

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
