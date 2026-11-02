"""Lecturas y seguimiento reúnen referencias; no generan hechos nuevos."""
import copy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import unittest

NOW = datetime(2026,11,2,12,tzinfo=timezone.utc)


def story(i=0, category='nacional', age=1, **extra):
    return {'title':f'Información específica del asunto número {i}', 'category':category,
            'link':f'https://medio{i}.example/nota', 'source_url':f'https://medio{i}.example',
            'published':(NOW-timedelta(hours=age)).isoformat(), 'sources':[f'Medio {i}'],
            'summary':'', 'image':'', **extra}


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if attrs.get('id'):self.ids.append(attrs['id'])


class DiscoveryTests(unittest.TestCase):
    def test_brief_uses_five_diverse_current_original_records(self):
        from scripts.discovery import select_brief
        dominant=[story(i, sources=['Dominante']*4, source_url='https://dominante.example') for i in range(6)]
        diverse=[story(20+i,category=cat,age=2) for i,cat in enumerate(('internacional','latinoamerica','economia','tecnologia','cultura'))]
        items=dominant+diverse;before=copy.deepcopy(items)
        result=select_brief(items,NOW)
        self.assertEqual(len(result),5)
        self.assertGreaterEqual(len({s['category'] for s in result}),4)
        self.assertLessEqual(sum(s['source_url']=='https://dominante.example' for s in result),2)
        self.assertTrue(all(any(s is original for original in items) for s in result))
        self.assertEqual(items,before)

    def test_brief_rejects_missing_dates_future_stale_unsafe_and_nonfactual_content(self):
        from scripts.discovery import select_brief
        bad=[story(1,age=25),story(2,age=-1),story(3,published=''),story(4,link='javascript:alert(1)'),
             story(5,link='https://user:pass@medio.example/n'),story(6,link='https://medio.example\\@evil.example/n'),
             story(7,content_kind='satire'),story(8,content_kind='guide'),story(9,content_kind='premiere-news')]
        valid=story(10)
        self.assertEqual(select_brief(bad+[valid,dict(valid)],NOW),[valid])

    def test_useful_stories_require_a_practical_subject_and_appropriate_section(self):
        from scripts.discovery import useful_stories
        utility=story(1,'economia',title='Nuevos plazos para solicitar el subsidio de vivienda')
        sport=story(2,'deportes',title='El salario del futbolista más caro del campeonato')
        politics=story(3,'politica',title='Cruce de declaraciones entre dirigentes')
        self.assertEqual(useful_stories([sport,utility,politics],NOW),[utility])

    def test_discoveries_include_innovation_and_culture_without_generic_finance(self):
        from scripts.discovery import discover_stories
        startup=story(1,'economia',title='Startup anuncia ronda de inversión para su tecnología')
        bank=story(2,'economia',title='El dólar subió durante la sesión')
        science=story(3,'tecnologia',title='Científicos descubren un nuevo planeta')
        arts=story(4,'cultura',title='Nueva exposición internacional abre sus puertas')
        self.assertEqual({s['link'] for s in discover_stories([bank,startup,science,arts],NOW)}, {s['link'] for s in [startup,science,arts]})

    def test_topics_keep_original_dates_and_conservative_same_category_relationships(self):
        from scripts.discovery import build_topics
        current=story(1,title='Observatorio Atacama publica nuevas imágenes de galaxia Andrómeda',category='tecnologia',sources=['Uno','Dos','Tres','Cuatro'])
        earlier=story(2,title=current['title']+' hoy',category='tecnologia',age=30)
        unrelated=story(3,title='Observatorio europeo anuncia un telescopio en otra región',category='tecnologia',age=20)
        other_section=story(4,title=current['title'],category='deportes',age=30)
        items=[current];archive=[earlier,unrelated,other_section];before=copy.deepcopy((items,archive))
        topics=build_topics(items,archive,NOW)
        topic=next(t for t in topics if t['lead']['link']==current['link'])
        self.assertEqual([e['link'] for e in topic['entries']],[earlier['link'],current['link']])
        self.assertEqual([e['published'] for e in topic['entries']],[earlier['published'],current['published']])
        self.assertEqual((items,archive),before)
        again=next(t for t in build_topics([current],archive,NOW+timedelta(minutes=1)) if t['lead']['link']==current['link'])
        self.assertEqual(topic['id'],again['id'])

    def test_related_references_do_not_inflate_supporting_sources(self):
        from scripts.discovery import build_topics
        main=story(1,'internacional',sources=['Uno','Dos','Tres','Cuatro'])
        main['related_coverages']=[{'title':'Otro ángulo del mismo acontecimiento','source':'CNN Chile',
            'source_url':'https://www.cnnchile.com','link':'https://www.cnnchile.com/mundo/nota-de-prueba',
            'published':(NOW-timedelta(hours=3)).isoformat()}]
        topic=build_topics([main],[],NOW)[0]
        self.assertEqual(topic['sources'],main['sources'])
        self.assertEqual([r['source'] for r in topic['references']],['CNN Chile'])
        self.assertNotIn('CNN Chile',topic['sources'])

    def test_topics_exclude_unsafe_and_expired_records(self):
        from scripts.discovery import build_topics
        valid=story(1,sources=['A','B','C','D'])
        expired=story(2,age=200,sources=['A','B','C','D'])
        unsafe=story(3,link='https://evil.example\\@x.example',sources=['A','B','C','D'])
        topics=build_topics([valid,unsafe],[expired],NOW)
        self.assertEqual([t['lead']['link'] for t in topics],[valid['link']])

    def test_old_topic_link_survives_a_change_of_representative_headline(self):
        from scripts.discovery import render_discovery_pages
        import fetch_noticias as news
        old=story(1,title='Observatorio Atacama muestra nuevas imágenes de galaxia Andrómeda',sources=['A','B','C','D'])
        initial=render_discovery_pages([old],[],NOW,'https://portal.example',news.CATEGORIES)
        saved_path=next(p for p in initial if p.startswith('temas/'))
        newer=story(2,title=old['title']+' hoy',age=0,sources=['A','B','C','D','E'])
        updated=render_discovery_pages([newer],[old],NOW+timedelta(minutes=5),'https://portal.example',news.CATEGORIES)
        self.assertIn(saved_path,updated)
        self.assertIn(old['link'],updated[saved_path])

    def test_pages_have_safe_real_links_noindex_and_valid_local_targets(self):
        from scripts.discovery import render_discovery_pages
        import fetch_noticias as news
        item=story(1,title='<img src=x onerror=alert(1)> Subsidio de vivienda',sources=['Uno','Dos','Tres','Cuatro'])
        item['related_coverages']=[{'title':'La información desde otro medio','source':'CNN Chile',
            'source_url':'https://www.cnnchile.com','link':'https://www.cnnchile.com/pais/subsidio',
            'published':(NOW-timedelta(hours=2)).isoformat()}]
        files=render_discovery_pages([item],[],NOW,'https://portal.example/subruta',news.CATEGORIES)
        self.assertIn('hoy.html',files)
        topic_files=[name for name in files if name.startswith('temas/')]
        self.assertEqual(len(topic_files),1)
        for name,page in files.items():
            self.assertIn('name="robots" content="noindex,follow"',page)
            self.assertIn('&lt;img src=x onerror=alert(1)&gt;',page)
            self.assertNotIn('><img src=x onerror=alert(1)>',page)
            self.assertIn('https://portal.example/subruta/reading-pages.css',page)
            parser=Links();parser.feed(page)
            self.assertEqual(len(parser.ids),len(set(parser.ids)))
            for link in parser.links:
                if link.startswith('https://portal.example/subruta/temas/'):
                    self.assertIn(link.removeprefix('https://portal.example/subruta/'),files)
                if link.startswith('#'):self.assertIn(link[1:],parser.ids)
        self.assertIn('Referencias relacionadas',files[topic_files[0]])
        self.assertNotIn('fecha de estreno',files['hoy.html'])

    def test_empty_content_does_not_fabricate_news_or_empty_feature_sections(self):
        from scripts.discovery import render_discovery_pages
        import fetch_noticias as news
        files=render_discovery_pages([],[],NOW,'https://portal.example',news.CATEGORIES)
        self.assertEqual(set(files),{'hoy.html'})
        self.assertIn('No hay titulares recientes disponibles',files['hoy.html'])
        self.assertNotIn('id="para-ti"',files['hoy.html'])
        self.assertNotIn('id="descubre"',files['hoy.html'])
