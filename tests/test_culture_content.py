"""Presentación compartida sin convertir guías ni ficción en noticias."""
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import fetch_noticias as news

try:
    culture=importlib.import_module('scripts.culture_content')
except ModuleNotFoundError:
    culture=None

NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)


def guide(**changes):
    return {'title':'Estrenos Netflix del 26 al 30 de octubre de 2026',
            'source':'Cine PREMIERE','source_url':'https://cinepremiere.com.mx',
            'link':'https://cinepremiere.com.mx/estrenos/semana',
            'published':'2026-10-26T07:00:00Z',**changes}


def satire(**changes):
    return {'title':'Una historia satírica de prueba','source':'El Chigüire Bipolar',
            'source_url':'https://www.elchiguirebipolar.net',
            'link':'https://www.elchiguirebipolar.net/29/10/2026/prueba/',
            'published':'2026-10-29T11:00:00Z',**changes}


def story(index=0,**changes):
    return {'title':f'Noticia cultural de prueba {index}','category':'cultura',
            'sources':['Medio de prueba'],'source_url':'https://qa.example',
            'link':f'https://qa.example/noticia/{index}','published':'2026-10-29T10:00:00Z',
            'first_seen':'2026-10-29T10:00:00Z','summary':'','image':'',**changes}


class CultureContentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(culture,'Falta integrar entretenimiento con las tarjetas de Cultura')

    def test_display_separates_cinema_and_keeps_satire_in_culture_without_mutating_news(self):
        original={'cultura':[story()]}
        result=culture.add_culture_content(original,NOW,satire_items=[satire()],release_guides=[guide()])
        self.assertEqual(len(original['cultura']),1)
        self.assertIs(result['cultura'][0],original['cultura'][0])
        self.assertEqual(len(result['cultura']),2)
        self.assertEqual({s.get('content_kind') for s in result['cultura']},{None,'satire'})
        self.assertEqual(len(result['cine-streaming']),1)
        for item in result['cultura'][1:]:
            self.assertEqual(item['category'],'cultura')
            self.assertEqual(item.get('first_seen',''),'')
            self.assertEqual((item['summary'],item['image']),('',''))
        self.assertEqual(result['cine-streaming'][0]['published'],guide()['published'])
        self.assertEqual(result['cine-streaming'][0]['category'],'cine-streaming')

    def test_existing_urls_are_not_duplicated_even_when_they_are_in_the_front_page(self):
        original={'cultura':[story(link=guide()['link'])]}
        result=culture.add_culture_content(original,NOW,release_guides=[guide()])
        self.assertEqual(len(result['cultura']),1)
        result=culture.add_culture_content({},NOW,release_guides=[guide()],existing=[story(link=guide()['link'])])
        self.assertNotIn('cultura',result)

    def test_new_culture_section_and_previous_premieres_anchor_are_unique(self):
        body=news.render_sections({},NOW,release_guides=[guide(),guide(link='https://cinepremiere.com.mx/otra')])
        self.assertEqual(body.count('id="cat-cine-streaming"'),1)
        self.assertNotIn('id="cat-cultura"',body)
        self.assertEqual(body.count('id="estrenos-semana"'),1)

    def test_unavailable_satire_keeps_a_source_card_without_a_fabricated_publication(self):
        result=culture.add_culture_content({},NOW,satire_items=[])
        item=result['cultura'][0]
        self.assertEqual(item['content_kind'],'satire-source')
        self.assertEqual(item['title'],'El Chigüire Bipolar')
        self.assertFalse(item.get('published'))
        rendered=news.render_sections(result,NOW)
        self.assertIn('Sátira y humor',rendered)
        self.assertIn('Humor y ficción',rendered)
        self.assertNotIn('<time',rendered)
        self.assertNotIn('hace 1 min',rendered)

    def test_blocked_source_has_no_article_or_homepage_card(self):
        blocked={'name':'El Chigüire Bipolar','domain':'elchiguirebipolar.net',
                 'enabled':False,'permission_status':'pending'}
        with patch('scripts.regional_sources.load_catalog',return_value=[blocked]):
            for items in ([],[satire()]):
                self.assertNotIn('cultura',culture.add_culture_content({},NOW,satire_items=items))

    def test_stale_guides_and_malformed_satire_cannot_enter_the_common_grid(self):
        bad=[None,satire(title=[]),satire(source_url='https://evil.example'),
             satire(link='javascript:alert(1)'),satire(published=None)]
        result=culture.add_culture_content({},NOW,satire_items=bad,
                   release_guides=[guide(published='2026-10-20T07:00:00Z')])
        self.assertEqual([s['content_kind'] for s in result['cultura']],['satire-source'])

    def test_common_grid_has_labels_escaped_titles_and_the_same_category_filters(self):
        result=culture.add_culture_content({'cultura':[story()]},NOW,
                    satire_items=[satire(title='<script>Ficción</script>')],release_guides=[guide()])
        rendered=news.render_sections(result,NOW)
        self.assertEqual(rendered.count('class="section-grid section-grid--balanced"'),1)
        self.assertEqual(rendered.count('class="section-grid section-grid--single"'),1)
        self.assertIn('data-content-kind="guide"',rendered)
        self.assertIn('data-content-kind="satire"',rendered)
        self.assertIn('Guía publicada',rendered)
        self.assertIn('Guía de México',rendered)
        self.assertIn('Cine y streaming',rendered)
        self.assertIn('Sátira y humor',rendered)
        self.assertIn('Ficción satírica',rendered)
        self.assertIn('&lt;script&gt;',rendered)
        self.assertNotIn('<script>',rendered)
        self.assertNotIn('weekly-releases',rendered)
        self.assertNotIn('satire-links',rendered)
        self.assertNotIn('release-grid',rendered)
        self.assertNotIn('target="_blank"',rendered)
        self.assertEqual(rendered.count('data-key="cultura"'),2)
        self.assertEqual(rendered.count('data-key="cine-streaming"'),1)
        self.assertIn('2 contenidos',rendered)
        self.assertIn('1 guía',rendered)

    def test_site_keeps_one_culture_menu_and_does_not_promote_guides_or_satire_as_news(self):
        with tempfile.TemporaryDirectory() as folder:
            news.build_site([story(category='nacional')],NOW,folder,
                            satire_items=[satire()],release_guides=[guide()])
            page=(Path(folder)/'index.html').read_text()
            feed=(Path(folder)/'rss.xml').read_text()
        self.assertIn('id="cat-cultura"',page)
        self.assertIn('href="#cat-cultura"',page)
        self.assertIn('href="#cat-cine-streaming"',page)
        self.assertNotIn('nav-subitem',page)
        self.assertNotIn('href="#estrenos-semana"',page)
        self.assertIn('id="estrenos-semana"',page)
        self.assertIn('data-news-count="1"',page)
        data=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',page,re.S)[1])
        self.assertNotIn('Cine PREMIERE',json.dumps(data))
        self.assertNotIn('El Chigüire',feed)
        self.assertNotIn('Cine PREMIERE',feed)
        self.assertNotIn('%%',page)

    def test_cinema_is_a_display_category_and_does_not_add_news_feed_queries(self):
        from scripts.culture_content import section_categories
        self.assertNotIn('cine-streaming',{c['key'] for c in news.CATEGORIES})
        categories=section_categories(news.CATEGORIES)
        keys=[c['key'] for c in categories]
        self.assertEqual(keys.count('cine-streaming'),1)
        self.assertEqual(keys.index('cine-streaming'),keys.index('cultura')+1)
        self.assertEqual(next(c['label'] for c in categories if c['key']=='cine-streaming'),'Cine y streaming')
        display=culture.add_culture_content({},NOW,release_guides=[guide(published=news.to_iso(NOW))])
        self.assertEqual(news.merge([],display['cine-streaming'],NOW),0)


if __name__=='__main__':unittest.main()
