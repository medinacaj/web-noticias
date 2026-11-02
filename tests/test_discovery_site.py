import copy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
import fetch_noticias as news

NOW=datetime(2026,11,2,12,tzinfo=timezone.utc)


class DiscoveryIntegrationTests(unittest.TestCase):
    def items(self):
        return [{'title':f'Subsidio de vivienda: nuevos plazos para postular {i}','category':'nacional',
                 'sources':['A','B','C','D'],'link':f'https://medio{i}.example/n',
                 'source_url':f'https://medio{i}.example','published':(NOW-timedelta(hours=i+1)).isoformat(),
                 'summary':'','image':''} for i in range(3)]

    def test_site_generates_summary_and_radar_links_to_existing_topic_pages(self):
        items=self.items();before=copy.deepcopy(items)
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(items,NOW,folder)
            root=Path(folder);index=(root/'index.html').read_text()
            self.assertTrue((root/'hoy.html').exists())
            self.assertIn('href="hoy.html"',index)
            self.assertIn('class="discovery-shortcuts"',index)
            class RadarLinks(HTMLParser):
                def __init__(self):super().__init__();self.links=[]
                def handle_starttag(self,tag,attrs):
                    data=dict(attrs)
                    if tag=='a' and data.get('href','').startswith('temas/'):self.links.append(data['href'])
            parser=RadarLinks();parser.feed(index)
            self.assertTrue(parser.links)
            for path in parser.links:self.assertTrue((root/path).is_file(),path)
            self.assertIn('data-news-count="3"',index)
            self.assertTrue((root/'rss.xml').is_file())
            self.assertNotIn('hoy.html',(root/'rss.xml').read_text())
        self.assertEqual(items,before)

    def test_shortcuts_only_link_to_available_reading_sections(self):
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(self.items(),NOW,folder)
            index=Path(folder,'index.html').read_text();daily=Path(folder,'hoy.html').read_text()
            class Targets(HTMLParser):
                def __init__(self):super().__init__();self.links=[];self.ids=[]
                def handle_starttag(self,tag,attrs):
                    attrs=dict(attrs)
                    if tag=='a' and attrs.get('href','').startswith('hoy.html#'):self.links.append(attrs['href'].split('#')[1])
                    if attrs.get('id'):self.ids.append(attrs['id'])
            home=Targets();home.feed(index);page=Targets();page.feed(daily)
            for fragment in home.links:self.assertIn(fragment,page.ids)

    def test_rebuild_removes_only_expired_generated_topic_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'temas').mkdir();(root/'temas/expired.html').write_text('viejo')
            (root/'personal.txt').write_text('conservar')
            news.build_site(self.items(),NOW,folder)
            self.assertFalse((root/'temas/expired.html').exists())
            self.assertEqual((root/'personal.txt').read_text(),'conservar')
