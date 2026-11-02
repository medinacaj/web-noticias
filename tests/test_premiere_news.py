"""Noticias individuales vigentes sin inferir la fecha ni el mercado del estreno."""
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import re
import tempfile
import unittest

import fetch_noticias as news
from scripts.culture_content import add_culture_content

try:
    discovery=importlib.import_module('scripts.premiere_news')
except ModuleNotFoundError:
    discovery=None

NOW=datetime(2026,11,3,12,tzinfo=timezone.utc)


def item(**changes):
    return {'title':"'Horizonte': la nueva serie de Netflix ya tiene fecha de estreno",
            'source':'Espinof','source_url':'https://www.espinof.com',
            'link':'https://www.espinof.com/series-de-ficcion/horizonte-estreno',
            'published':'2026-11-02T11:00:00Z','image':'https://qa.example/not-authorized.jpg',
            'summary':'No se debe copiar el contenido del editor',**changes}


class PremiereNewsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(discovery,'Falta renovar noticias individuales de estrenos')

    def test_original_metadata_has_no_invented_release_date_or_artwork(self):
        found=discovery.current_news([item()],NOW,restrictions=[])
        self.assertEqual(len(found),1)
        record=found[0]
        self.assertEqual(record['title'],item()['title'])
        self.assertEqual(record['published'],item()['published'])
        self.assertEqual(record['link'],item()['link'])
        self.assertEqual(record['content_kind'],'premiere-news')
        self.assertEqual((record['image'],record['summary']),('',''))
        self.assertNotIn('release_date',record)
        self.assertNotIn('verification_url',record)
        self.assertNotIn('platform',record)

    def test_roundups_rankings_music_and_generic_trailer_history_are_rejected(self):
        titles=['Estrenos Netflix del 2 al 6 de noviembre de 2026',
                "Los mejores estrenos de la semana: 'Horizonte' y otras series de Netflix",
                "Las 10 mejores series de Netflix: 'Horizonte' lidera el ranking",
                "'Horizonte', el nuevo disco que estrena el cantante este viernes",
                "'GTA 6': el videojuego ya tiene fecha de estreno para PS5",
                "El tráiler de 'Origen' esconde la historia de su icónico sonido",
                '5 meses después de un paso discreto en salas de cine, se estrena en ‘streaming’ una de las películas del año',
                'SensaCine: Cine, cartelera, estrenos, películas y series']
        for title in titles:
            with self.subTest(title=title):
                self.assertEqual(discovery.current_news([item(title=title)],NOW,restrictions=[]),[])

    def test_named_film_release_and_a_new_series_trailer_are_accepted(self):
        for title in ("‘Horizonte’ se estrena en cines: fecha y tráiler de la película",
                      "Netflix presenta el primer tráiler de la nueva serie 'Horizonte'",
                      'La serie «Horizonte» llega a Prime Video este viernes'):
            with self.subTest(title=title):
                self.assertEqual(len(discovery.current_news([item(title=title)],NOW,restrictions=[])),1)

    def test_untrusted_origins_invalid_and_stale_dates_are_rejected(self):
        values=[item(source_url='https://espinof.com.evil.example'),
                item(link='javascript:alert(1)'),item(link='https://evil.example/noticia'),
                item(published=None),item(published='2026-10-20T10:00:00Z'),
                item(published=(NOW+timedelta(hours=1)).isoformat()),item(title=[])]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(discovery.current_news([value],NOW,restrictions=[]),[])

    def test_week_change_preserves_news_date_without_rejuvenating_a_confirmed_release(self):
        older=item(published='2026-10-31T11:00:00Z')
        display=add_culture_content({},NOW,premiere_news=[older])
        self.assertEqual(display['cine-streaming'][0]['published'],older['published'])
        self.assertNotIn('release_date',display['cine-streaming'][0])
        self.assertEqual(discovery.current_news([older],NOW+timedelta(days=8),restrictions=[]),[])

    def test_blocked_publishers_are_not_queried_or_accepted(self):
        blocked=[{'domain':s[0],'enabled':False,'permission_status':'pending'} for s in discovery.SOURCES]
        calls=[]
        found=discovery.collect_news(NOW,fetch=lambda *a,**k:calls.append(a),restrictions=blocked)
        self.assertEqual((found,calls),([],[]))
        self.assertEqual(discovery.current_news([item()],NOW,restrictions=blocked),[])

    def test_discovery_budget_deduplication_and_per_publisher_cap(self):
        calls=[]
        def fetch(url,category,**options):
            calls.append((url,category,options))
            return [item(link=f'https://www.espinof.com/series-de-ficcion/nota-{i}') for i in range(80)]
        found=discovery.collect_news(NOW,fetch=fetch,restrictions=[])
        self.assertLessEqual(len(calls),3)
        self.assertTrue(all(c[1]=='cultura' and c[2]['metadata_only'] is True and c[2]['limit']==40 for c in calls))
        self.assertTrue(all('news.google.com/rss/search?' in c[0] for c in calls))
        self.assertEqual(len(found),2)
        self.assertEqual(len({r['link'] for r in found}),len(found))

    def test_failure_is_bounded_and_does_not_create_fake_news(self):
        def unavailable(*args,**kwargs):raise OSError('Unavailable')
        self.assertEqual(discovery.collect_news(NOW,fetch=unavailable,restrictions=[]),[])

    def test_display_news_do_not_enter_factual_counts_rss_or_history(self):
        with tempfile.TemporaryDirectory() as folder:
            news.build_site([],NOW,folder,premiere_news=[item()])
            body=Path(folder,'index.html').read_text()
            rss=Path(folder,'rss.xml').read_text()
        self.assertIn('Noticia de estreno',body)
        self.assertIn('Horizonte',body)
        self.assertIn('data-news-count="0"',body)
        structured=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',body,re.S)[1])
        self.assertNotIn('Horizonte',json.dumps(structured))
        self.assertNotIn('Horizonte',rss)
        display=add_culture_content({},NOW,premiere_news=[item()])
        self.assertEqual(news.merge([],display['cine-streaming'],NOW),0)


if __name__=='__main__':unittest.main()
