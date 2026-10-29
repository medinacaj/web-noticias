"""Guías semanales: su fecha de publicación no es una fecha de estreno."""
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

import fetch_noticias as news

try:
    releases = importlib.import_module('scripts.weekly_releases')
except ModuleNotFoundError:
    releases = None

NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def guide(index=0, domain='cinepremiere.com.mx', **changes):
    return {'title':f'Estrenos Netflix del 26 al 30 de octubre de 2026 · {index}',
            'source':'Cine PREMIERE', 'source_url':f'https://{domain}',
            'link':f'https://{domain}/estrenos/{index}',
            'published':'2026-10-26T07:00:00Z', 'summary':'No copiar',
            'image':'https://example.org/poster.jpg', **changes}


class WeeklyReleasesTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(releases, 'Falta el bloque de estrenos semanales')

    def collect(self, records, **options):
        return releases.collect_releases(NOW,fetch=lambda *a,**k:records,
                                         restrictions=options.pop('restrictions',[]),**options)

    def test_week_rollover_uses_chilean_date_and_monday_to_sunday(self):
        start,end=releases.week_bounds(datetime(2026,10,26,1,tzinfo=timezone.utc))
        self.assertEqual(start.date().isoformat(),'2026-10-19')
        self.assertEqual(end.date().isoformat(),'2026-10-26')
        start,end=releases.week_bounds(NOW)
        self.assertEqual((start.day,end.day),(26,2))
        self.assertEqual((end-start).days,7)

    def test_collect_preserves_headline_publication_and_only_metadata(self):
        result=self.collect([guide()])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['title'],guide()['title'])
        self.assertEqual(result[0]['published'],guide()['published'])
        self.assertEqual(result[0]['market'],'México')
        self.assertEqual(result[0]['platforms'],['Netflix'])
        self.assertEqual(result[0]['format'],'Streaming')
        self.assertEqual((result[0]['summary'],result[0]['image']),('',''))
        self.assertNotIn('release_date',result[0])

    def test_old_future_naive_and_missing_publications_are_excluded(self):
        invalid=['2026-10-26T02:59:59Z',None,'2026-10-28T12:00:00',
                 news.to_iso(NOW+timedelta(minutes=16))]
        for stamp in invalid:
            with self.subTest(stamp=stamp):
                self.assertEqual(self.collect([guide(published=stamp)]),[])

    def test_newly_published_old_calendars_monthly_guides_and_rankings_are_excluded(self):
        titles=['Estrenos Netflix del 19 al 25 de octubre de 2026',
                'Estrenos Netflix del 26 al 30 de octubre de 2025',
                'Los estrenos de Netflix en noviembre de 2026',
                'Las diez mejores películas de Netflix esta semana',
                'Ranking Netflix: qué ver esta semana',
                'Una nueva serie llegará a Netflix el 18 de noviembre',
                'Apple TV y sus próximos estrenos de películas y series',
                'Estrenos Netflix del 31 de febrero de 2026']
        for title in titles:
            with self.subTest(title=title):
                self.assertEqual(self.collect([guide(title=title)]),[])
        self.assertEqual(len(self.collect([guide(title='Qué ver esta semana en Netflix y Disney+')])),1)

    def test_malformed_records_untrusted_hosts_and_unsafe_links_are_ignored(self):
        records=[None,[],guide(title=[]),guide(source=[]),
                 guide(source_url='https://cinepremiere.com.mx.evil.test'),
                 guide(source_url='https://127.0.0.1'),
                 guide(source_url='https://user:pass@cinepremiere.com.mx'),
                 guide(link='javascript:alert(1)'),
                 guide(link='https://news.google.com.evil.test/rss/articles/forged')]
        self.assertEqual(self.collect(records),[])
        self.assertEqual(len(self.collect([guide(link='https://news.google.com/rss/articles/verified')])),1)

    def test_month_long_intervals_are_excluded_and_a_week_crossing_months_is_valid(self):
        for title in ('Estrenos Netflix del 1 al 31 de octubre de 2026',
                      'Estrenos Netflix del 1 de octubre al 1 de noviembre de 2026'):
            with self.subTest(title=title):
                self.assertEqual(self.collect([guide(title=title)]),[])
        weekly='Qué ver del 26 de octubre al 1 de noviembre de 2026 en Netflix'
        self.assertEqual(len(self.collect([guide(title=weekly)])),1)

    def test_existing_source_restrictions_apply_before_queries_and_results(self):
        blocked={'name':'Cine PREMIERE','domain':'cinepremiere.com.mx','enabled':False,
                 'permission_status':'pending'}
        calls=[]
        result=releases.collect_releases(NOW,restrictions=[blocked],fetch=lambda url,*a,**k:calls.append(url) or [guide()])
        self.assertEqual(result,[])
        self.assertTrue(all('cinepremiere.com.mx' not in parse_qs(urlsplit(u).query)['q'][0] for u in calls))

    def test_bounded_diverse_results_and_cinema_share_the_weekly_block(self):
        records=[guide(i) for i in range(20)]
        records += [guide(25,domain='espinof.com',source='Espinof'),
                    guide(26,domain='as.com',source='Diario AS'),
                    guide(27,domain='clarin.com',source='Clarín'),
                    guide(28,domain='los40.cl',source='LOS40',title='Estrenos de cine en Chile esta semana')]
        calls=[]
        def fetch(url,category,**options):
            calls.append((url,options))
            return iter(records)
        result=releases.collect_releases(NOW,fetch=fetch,restrictions=[])
        self.assertLessEqual(len(calls),3)
        self.assertTrue(all(o['metadata_only'] and o['limit']==40 for _,o in calls))
        self.assertEqual(len(result),6)
        self.assertEqual(len({x['source_url'] for x in result[:5]}),5)
        self.assertEqual(sum(x['source']=='Cine PREMIERE' for x in result),2)
        self.assertIn('Cine',{x['format'] for x in result})
        self.assertTrue(all(urlsplit(u).hostname=='news.google.com' for u,_ in calls))

    def test_one_failed_query_does_not_hide_other_guides(self):
        def fetch(url,*args,**options):
            if 'cinepremiere.com.mx' in parse_qs(urlsplit(url).query)['q'][0]:
                return [guide()]
            raise OSError('offline')
        self.assertEqual(len(releases.collect_releases(NOW,fetch=fetch,restrictions=[])),1)

    def test_render_is_attributed_escaped_and_labels_the_guide_date(self):
        result=self.collect([guide(title='Estrenos Netflix esta semana <script>bad()</script>')])
        body=releases.render_releases(result,NOW)
        self.assertIn('Estrenos de la semana',body)
        self.assertIn('26 oct',body)
        self.assertIn('1 nov',body)
        self.assertIn('Guía de México',body)
        self.assertIn('Guía publicada',body)
        self.assertIn('Cine PREMIERE',body)
        self.assertNotIn('<script>',body)
        self.assertNotIn('target="_blank"',body)
        self.assertNotIn('data-key=',body)
        self.assertNotIn('<img',body)
        self.assertEqual(releases.render_releases([],NOW),'')
        self.assertEqual(releases.render_releases(result,NOW+timedelta(days=7)),'')

    def test_site_includes_culture_and_its_menu_even_when_there_are_only_release_guides(self):
        story={'title':'Otra noticia nacional','link':'https://news.example/nacional',
               'category':'nacional','sources':['Prueba'],'source_url':'https://news.example',
               'published':news.to_iso(NOW),'first_seen':news.to_iso(NOW),'image':'','summary':''}
        result=self.collect([guide()])
        with tempfile.TemporaryDirectory() as folder:
            news.build_site([story],NOW,folder,release_guides=result)
            page=(Path(folder)/'index.html').read_text()
        self.assertIn('href="#cat-cultura"',page)
        self.assertIn('href="#estrenos-semana"',page)
        self.assertEqual(page.count('id="estrenos-semana"'),1)
        self.assertIn('data-news-count="1"',page)
        self.assertNotIn('Cine PREMIERE',page.split('<script type="application/ld+json">')[1].split('</script>')[0])
        self.assertNotIn('%%',page)


if __name__=='__main__':
    unittest.main()
