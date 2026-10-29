"""Identidades verificables y descubrimiento empresarial acotado por RSS existente."""
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import fetch_noticias as news

try:
    business = importlib.import_module('scripts.business_sources')
except ModuleNotFoundError:
    business = None

NOW = datetime(2026, 10, 29, 0, tzinfo=timezone.utc)


def source(index=0, **changes):
    domain=f'editor{index}.example'
    return {'id':f'biz-{index}', 'request_id':None, 'name':f'Editor {index}',
            'domain':domain, 'url':f'https://{domain}', 'kind':'news',
            'group':'startups', 'category':'economia', 'identity_status':'indexed',
            'discovery_enabled':True,
            'evidence':{'source_url':f'https://{domain}',
                        'query_url':f'https://news.google.com/rss/search?q=site%3A{domain}'},
            **changes}


def item(media, index=0, **changes):
    return {'title':f'Startup de prueba consigue inversión {index}',
            'link':f'https://{media["domain"]}/news/{index}',
            'source':media['name'], 'source_url':media['url'],
            'published':news.to_iso(NOW-timedelta(hours=1)),
            'image':'https://images.example/never-fetch.jpg',
            'summary':'Texto que no debe copiarse', **changes}


class BusinessSourcesTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(business, 'Falta la ampliación empresarial por RSS existente')

    def collect(self, catalog, fetch, **options):
        return business.collect_business(NOW,catalog=catalog,fetch=fetch,restrictions=options.pop('restrictions',[]),**options)

    def test_catalog_preserves_every_request_and_distinguishes_unconfirmed_sources(self):
        catalog=business.load_catalog()
        ids={s.get('request_id') for s in catalog if isinstance(s.get('request_id'),int)}
        self.assertEqual(ids,set(range(1,101)))
        self.assertGreaterEqual(sum(s.get('request_id') is None for s in catalog),14)
        self.assertEqual(len({s['id'] for s in catalog}),len(catalog))
        for s in catalog:
            if s.get('identity_status')!='indexed' or s.get('kind')=='academic':
                self.assertFalse(s.get('discovery_enabled'))
        for number in (1,34,61):
            self.assertFalse(next(s for s in catalog if s['request_id']==number)['discovery_enabled'])
        self.assertIn('forbes.cl',{s.get('domain') for s in catalog if s['request_id']==78})

    def test_collection_keeps_original_dates_and_only_metadata(self):
        media=source()
        records=self.collect([media],lambda *a,**k:[item(media)])
        self.assertEqual(len(records),1)
        record=records[0]
        self.assertEqual(record['title'],item(media)['title'])
        self.assertEqual(record['published'],item(media)['published'])
        self.assertEqual(record['category'],'economia')
        self.assertEqual(record['publisher_id'],media['id'])
        self.assertEqual(record['source_kind'],'news')
        self.assertTrue(record['metadata_only'])
        self.assertEqual((record['summary'],record['image']),('',''))

    def test_unknown_academic_and_review_sources_are_not_queried(self):
        catalog=[source(identity_status='unconfirmed'),source(1,kind='academic'),
                 source(2,discovery_enabled=False),source(3,domain='127.0.0.1'),
                 source(4,evidence={}),source(5,group=[]),source(6,name=None)]
        calls=[]
        self.assertEqual(self.collect(catalog,lambda *a,**k:calls.append(a) or []),[])
        self.assertEqual(calls,[])

    def test_existing_catalog_restrictions_cannot_be_overridden_by_new_registry(self):
        media=source(domain='reuters.com',url='https://reuters.com',
                     evidence={'source_url':'https://reuters.com','query_url':'https://news.google.com/rss/search?q=Reuters'})
        calls=[]
        blocked={'name':media['name'],'domain':media['domain'],'enabled':False,'permission_status':'pending'}
        self.assertEqual(self.collect([media],lambda *a,**k:calls.append(a) or [],restrictions=[blocked]),[])
        self.assertEqual(calls,[])

    def test_invalid_source_link_or_date_is_rejected(self):
        media=source()
        variants=[{'source_url':'https://editor0.example.evil.test'},
                  {'source_url':'https://user:password@editor0.example'},
                  {'link':'https://news.google.com.evil.test/rss/articles/test'},
                  {'link':'javascript:alert(1)'}, {'published':None},
                  {'published':'2026-10-28T23:00:00'},
                  {'published':news.to_iso(NOW-timedelta(hours=24,seconds=1))},
                  {'published':news.to_iso(NOW+timedelta(minutes=15,seconds=1))}]
        for changes in variants:
            with self.subTest(changes=changes):
                self.assertEqual(self.collect([media],lambda *a,**k:[item(media,**changes)]),[])

    def test_queries_are_bounded_and_never_fetch_editor_websites(self):
        catalog=[source(i) for i in range(170)]
        calls=[]
        self.collect(catalog,lambda url,*a,**k:calls.append((url,k)) or [])
        self.assertLessEqual(len(calls),12)
        self.assertTrue(calls)
        for url,options in calls:
            self.assertEqual(urlsplit(url).hostname,'news.google.com')
            q=parse_qs(urlsplit(url).query)['q'][0]
            self.assertIn('when:1d',q)
            self.assertLessEqual(q.count('site:'),12)
            self.assertTrue(options['metadata_only'])

    def test_source_cap_diversity_canonical_dedupe_and_failed_search_isolation(self):
        catalog=[source(i) for i in range(15)]
        calls=[]
        def fetch(url,*a,**k):
            calls.append(url)
            query=parse_qs(urlsplit(url).query)['q'][0]
            if 'site:editor0.example' in query:raise OSError('feed unavailable')
            return [item(media,i) for media in catalog if 'site:'+media['domain'] in query for i in range(5)]
        records=self.collect(catalog,fetch)
        self.assertTrue(records)
        self.assertLessEqual(len(records),80)
        for media in catalog:
            self.assertLessEqual(sum(r['publisher_id']==media['id'] for r in records),2)
        self.assertEqual(len({r['link'] for r in records}),len(records))
        first=[r['publisher_id'] for r in records[:len({r['publisher_id'] for r in records})]]
        self.assertEqual(len(first),len(set(first)))

    def test_existing_article_is_not_replaced_by_metadata_discovery(self):
        media=source();existing=item(media)
        original=dict(existing)
        incoming=item(media,link=existing['link']+'?utm_source=test')
        self.assertEqual(self.collect([media],lambda *a,**k:[incoming],existing=[existing]),[])
        self.assertEqual(existing,original)

    def test_broad_economic_sources_require_relevant_technology_business_content(self):
        media=source(group='business_media',category='tecnologia')
        records=self.collect([media],lambda *a,**k:[item(media,title='Resultado del partido y tabla de posiciones')])
        self.assertEqual(records,[])
        self.assertEqual(len(self.collect([media],lambda *a,**k:[item(media,title='Empresas incorporan inteligencia artificial y software') ])),1)

    def test_unverified_resource_subdomain_is_not_promoted_as_the_newsroom(self):
        media=source()
        records=self.collect([media],lambda *a,**k:[item(media,source_url='https://resources.editor0.example')])
        self.assertEqual(records,[])

    def test_verified_section_scope_is_preserved_and_invalid_scope_is_disabled(self):
        media=source(search_scope='editor0.example/innovacion');calls=[]
        self.collect([media],lambda url,*a,**k:calls.append(url) or [])
        self.assertIn('site:editor0.example/innovacion',parse_qs(urlsplit(calls[0]).query)['q'][0])
        calls=[]
        self.collect([source(search_scope='editor0.example OR site:other.test')],lambda *a,**k:calls.append(a) or [])
        self.assertEqual(calls,[])

    def test_a_malformed_existing_link_cannot_break_other_discovery(self):
        media=source()
        records=self.collect([media],lambda *a,**k:[item(media)],existing=[{'link':'https://[invalid'}])
        self.assertEqual(len(records),1)

    def test_the_global_cap_does_not_permanently_exclude_publishers_at_the_tail(self):
        catalog=[source(i) for i in range(90)]
        def fetch(url,*a,**k):
            query=parse_qs(urlsplit(url).query)['q'][0]
            return [item(media) for media in catalog if 'site:'+media['domain'] in query]
        first=self.collect(catalog,fetch)
        second=business.collect_business(NOW+timedelta(hours=1),catalog=catalog,fetch=fetch,restrictions=[])
        self.assertEqual(len(first),80)
        self.assertEqual(len(second),80)
        self.assertEqual({r['publisher_id'] for r in first+second},{s['id'] for s in catalog})

    def test_directory_links_verified_publishers_and_escapes_names(self):
        good=source(name='Medio <script>alert(1)</script>')
        pending=source(1,name='Fuente pendiente',identity_status='unconfirmed',url=None,discovery_enabled=False)
        academic=source(2,kind='academic',group='academic',discovery_enabled=False)
        body=business.render_directory([good,pending,academic])
        self.assertIn('https://editor0.example',body)
        self.assertNotIn('<script>',body)
        self.assertNotIn('target="_blank"',body)
        self.assertIn('Investigación',body)
        self.assertIn('Fuente pendiente',body)
        self.assertNotIn('href="https://editor1.example',body)

    def test_business_collection_is_integrated_without_extra_gnews_calls(self):
        media=source();api=[]
        def fetch(url,*a,**k):
            return [item(media)] if 'site%3Aeditor0.example' in url else []
        with patch.object(news,'GNEWS_API_KEY','fixture'), \
             patch.object(news,'fetch_rss',side_effect=fetch), \
             patch.object(news,'fetch_gnews',side_effect=lambda cat:api.append(cat['key']) or []), \
             patch('scripts.business_sources.load_catalog',return_value=[media]), \
             patch('scripts.regional_sources.collect_regional',return_value=[]):
            records=news.collect(NOW)
        self.assertEqual(len(api),6)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['publisher_id'],media['id'])

    def test_source_kind_survives_persistence_and_labels_institutional_content(self):
        media=source(kind='institutional');records=self.collect([media],lambda *a,**k:[item(media)])
        stories=[];news.merge(stories,records,NOW)
        self.assertEqual(stories[0]['source_kind'],'institutional')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.json';news.save_history(str(path),stories,NOW)
            loaded=news.load_history(str(path));self.assertEqual(loaded[0]['source_kind'],'institutional')
            news.build_site(loaded,NOW,folder)
            self.assertIn('Institucional',Path(folder,'index.html').read_text())

    def test_malformed_historical_source_kind_is_ignored_when_rendering(self):
        story={'title':'Ejemplo','sources':['Fuente'],'source_url':'https://editor.example',
               'link':'https://editor.example/news','category':'economia',
               'published':news.to_iso(NOW),'source_kind':{'unexpected':'object'}}
        body=news.meta_html(story,NOW)
        self.assertNotIn('Institucional',body)


if __name__=='__main__':unittest.main()
