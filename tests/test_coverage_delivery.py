"""Casos de omisión entre RSS, selección y portada; sátira fuera de noticias."""
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fetch_noticias as news


class CoverageDeliveryTests(unittest.TestCase):
    now = datetime(2026, 10, 27, 16, tzinfo=timezone.utc)

    def story(self, index, category='cultura', **extra):
        return {'title': f'Artículo cultural {index}', 'category': category,
                'link': f'https://medio.example/nota/{index}', 'sources': [f'Medio {index}'],
                'source_url': 'https://medio.example', 'published': self.now.isoformat(),
                'summary': '', 'image': '', **extra}

    def test_google_can_scan_beyond_15_without_enlarging_direct_feeds(self):
        self.assertIn('limit', inspect.signature(news.fetch_rss).parameters)
        xml = '<rss><channel>' + ''.join(
            f'<item><title>Brasil, publicación {i}</title><link>https://medio.example/{i}</link>'
            '<source url="https://medio.example">Medio</source>'
            '<pubDate>Tue, 27 Oct 2026 15:00:00 GMT</pubDate></item>' for i in range(40)) + '</channel></rss>'
        with patch.object(news, 'http_get', return_value=xml):
            self.assertEqual(len(news.fetch_rss('https://medio.example/rss', 'latinoamerica')), 15)
            extended = news.fetch_rss('https://news.google.com/rss/search?q=Brasil', 'latinoamerica', limit=60)
        self.assertEqual(len(extended), 40)
        self.assertIn('39', extended[-1]['title'])

    def test_more_than_24_candidates_remain_available_in_the_published_section(self):
        stories = [self.story(i) for i in range(40)]
        selected = news.select(stories, self.now)
        links = {s['link'] for s in selected['by_category'].get('cultura', [])}
        links.update(s['link'] for s in selected['secondary'])
        if selected['lead']:
            links.add(selected['lead']['link'])
        self.assertEqual(len(links), 40)

    def test_latam_discovery_respects_disabled_world_sources(self):
        item = {'category': 'latinoamerica', 'title': 'Brasil anuncia novedades',
                'source': 'CNN en Español', 'source_url': 'https://cnnespanol.cnn.com',
                'link': 'https://cnnespanol.cnn.com/brasil/nota', 'published': self.now.isoformat()}
        blocked = {'name': 'CNN en Español', 'domain': 'cnn.com', 'enabled': False,
                   'permission_status': 'pending'}
        with patch('scripts.regional_sources.load_catalog', return_value=[]), \
             patch('scripts.global_sources.load_catalog', return_value=[blocked]), \
             patch.object(news, 'GNEWS_API_KEY', ''), \
             patch.object(news, 'fetch_rss', side_effect=lambda url, cat, **kw: [item] if cat == 'latinoamerica' else []):
            found = news.collect(self.now)
        self.assertFalse(any(s.get('source') == 'CNN en Español' for s in found))

    def test_satire_is_never_a_news_lead_or_latest_story(self):
        satire = self.story(99, sources=['El Chigüire Bipolar'],
                            source_url='https://www.elchiguirebipolar.net', image='https://images.example/photo.jpg')
        selected = news.select([satire, self.story(1, 'nacional')], self.now)
        self.assertNotEqual(selected['lead']['link'], satire['link'])
        self.assertTrue(all(s['link'] != satire['link'] for s in selected.get('latest', [])))

    def test_satire_is_labelled_inside_culture_and_excluded_from_feeds_and_schema(self):
        self.assertIn('satire_items', inspect.signature(news.build_site).parameters)
        satire = self.story(99, title='Ejemplo satírico claramente separado',
                            link='https://www.elchiguirebipolar.net/ejemplo/', sources=['El Chigüire Bipolar'])
        stories = [self.story(i, 'cultura' if i else 'nacional') for i in range(5)]
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories + [satire], self.now, folder, satire_items=[satire])
            html = Path(folder, 'index.html').read_text()
            culture = html.split('id="cat-cultura"', 1)[1].split('</section>', 1)[0]
            self.assertIn('Sátira y humor', culture)
            self.assertIn(satire['title'], culture)
            schema = html.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
            json.loads(schema)
            self.assertNotIn(satire['title'], schema)
            self.assertNotIn(satire['title'], Path(folder, 'rss.xml').read_text())


if __name__ == '__main__':
    unittest.main()
