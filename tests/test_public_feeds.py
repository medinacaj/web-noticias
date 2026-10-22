"""RSS de Web Noticias: solo enlaces de origen, atribución y feed válido."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
from copy import deepcopy

from scripts.public_feeds import render_rss, write_public_feeds


class PublicRssTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        self.site = "https://medinacaj.github.io/web-noticias"

    def news(self, number, hours=1, cat="tecnologia", url=None):
        date = (self.now - timedelta(hours=hours)).isoformat()
        return {"title": f"Noticias <relevantes> & {number}",
                "link": url or f"https://medio.example/nota/{number}?a=1&b=2",
                "sources": ["Medio & Co."],
                "source_url": "https://medio.example",
                "category": cat, "published": date,
                "image": "https://foto.example/foto.jpg", "summary": "Texto que no se debe copiar"}

    def test_valid_rss_preserves_original_urls_and_source(self):
        xml = render_rss([self.news(1)], self.now, self.site,
                         "Titulares recientes", "Selección de noticias")
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "rss")
        nodes = root.findall("./channel/item")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].findtext("title"), "Noticias <relevantes> & 1")
        self.assertEqual(nodes[0].findtext("link"), self.news(1)["link"])
        self.assertEqual(nodes[0].findtext("source"), "Medio & Co.")
        self.assertNotIn("Texto que no se debe copiar", xml)
        self.assertNotIn("foto.example", xml)

    def test_rejects_stale_invalid_and_duplicate_urls(self):
        items = [self.news(1), self.news(1), self.news(2, hours=26),
                 self.news(3, url="javascript:alert(1)"),
                 self.news(4, url="https://good.example@evil.example/nota")]
        output = ET.fromstring(render_rss(items, self.now, self.site, "T", "D"))
        self.assertEqual(len(output.findall("./channel/item")), 1)

    def test_unresolved_google_news_links_are_excluded(self):
        for host in ("news.google.com", "NEWS.GOOGLE.COM."):
            with self.subTest(host=host):
                item = self.news(1, url=f"https://{host}/rss/articles/ABC?oc=5")
                root = ET.fromstring(render_rss([item], self.now, self.site, "T", "D"))
                self.assertEqual(root.findall("./channel/item"), [])

    def test_merged_story_uses_the_linked_publishers_original_coverage(self):
        import fetch_noticias as news
        common = {"category": "nacional", "image": "", "summary": ""}
        first = dict(common, title="Gobierno anuncia nuevas medidas económicas para el país",
                     link="https://news.google.com/rss/articles/ABC", source="Medio A",
                     source_url="https://a.example", published=(self.now - timedelta(hours=3)).isoformat())
        second = dict(common, title="Gobierno anuncia nuevas medidas económicas en el país",
                      link="https://b.example/nota", source="Medio B",
                      source_url="https://b.example", published=(self.now - timedelta(hours=1)).isoformat())
        stories = []
        news.merge(stories, [first, second], self.now)
        self.assertEqual(len(stories), 1)
        before = deepcopy(stories)
        node = ET.fromstring(render_rss(stories, self.now, self.site, "T", "D")).find("./channel/item")
        self.assertEqual(node.findtext("link"), second["link"])
        self.assertEqual(node.findtext("title"), second["title"])
        self.assertEqual(node.findtext("source"), "Medio B")
        self.assertEqual(node.find("source").get("url"), "https://b.example")
        self.assertEqual(node.findtext("pubDate"), "Wed, 21 Oct 2026 11:00:00 GMT")
        self.assertEqual(stories, before)

    def test_missing_coverage_never_invents_a_publisher_for_a_merged_link(self):
        for declared in ("https://a.example", "https://b.example"):
            with self.subTest(declared=declared):
                item = self.news(1, url="https://b.example/nota")
                item.update(sources=["Medio A", "Medio B"], source_url=declared)
                root = ET.fromstring(render_rss([item], self.now, self.site, "T", "D"))
                self.assertEqual(root.findall("./channel/item"), [])

    def test_single_publisher_without_source_url_keeps_textual_attribution(self):
        item = self.news(1)
        item["source_url"] = ""
        node = ET.fromstring(render_rss([item], self.now, self.site, "T", "D")).find("./channel/item")
        self.assertEqual(node.findtext("source"), "Medio & Co.")
        self.assertEqual(node.find("source").get("url"), "https://medio.example")

    def test_single_publisher_with_conflicting_declared_host_is_omitted_without_matching_coverage(self):
        item = self.news(1, url="https://b.example/nota")
        item.update(sources=["Medio A"], source_url="https://a.example")
        item["coverages"] = [{"source": "Medio A", "title": "Otra nota",
                              "link": "https://a.example/otra-nota", "published": item["published"]}]
        root = ET.fromstring(render_rss([item], self.now, self.site, "T", "D"))
        self.assertEqual(root.findall("./channel/item"), [])

    def test_invalid_xml_characters_are_omitted_without_breaking_other_publications(self):
        for field in ("title", "sources", "link"):
            for invalid in ("\x00", "\x01", "\x0b", "\ud800", "\ufffe"):
                with self.subTest(field=field, invalid=repr(invalid)):
                    item = self.news(1)
                    if field == "sources":
                        item[field] = ["Medio" + invalid]
                    else:
                        item[field] += invalid
                    raw = render_rss([item, self.news(2)], self.now, self.site, "T", "D")
                    self.assertNotIn(invalid, raw)
                    rows = ET.fromstring(raw).findall("./channel/item")
                    self.assertEqual([node.findtext("link") for node in rows], [self.news(2)["link"]])

    def test_valid_xml_whitespace_and_unicode_titles_are_preserved(self):
        item = self.news(1)
        item["title"] = "Salud\t ciencia\n y tecnología 😀"
        node = ET.fromstring(render_rss([item], self.now, self.site, "T", "D")).find("./channel/item")
        self.assertEqual(node.findtext("title"), item["title"])

    def test_selected_coverage_date_controls_the_freshness_window(self):
        for hours in (25, -1):
            with self.subTest(hours=hours):
                item = self.news(1)
                item["coverages"] = [{"title": "Titular del medio", "source": "Medio",
                                      "link": item["link"],
                                      "published": (self.now - timedelta(hours=hours)).isoformat()}]
                root = ET.fromstring(render_rss([item], self.now, self.site, "T", "D"))
                self.assertEqual(root.findall("./channel/item"), [])

    def test_selected_coverage_without_its_own_valid_date_never_inherits_another_publishers_date(self):
        for date in (None, "", "not-a-date"):
            with self.subTest(date=date):
                item = self.news(1)
                item["sources"] = ["Medio A", "Medio B"]
                coverage = {"title": "Titular de B", "source": "Medio B", "link": item["link"]}
                if date is not None:
                    coverage["published"] = date
                item["coverages"] = [coverage]
                root = ET.fromstring(render_rss([item], self.now, self.site, "T", "D"))
                self.assertEqual(root.findall("./channel/item"), [])

    def test_coverage_date_orders_publications_before_both_feed_limits(self):
        for limit in (24, 50):
            with self.subTest(limit=limit):
                stories = [self.news(i, hours=2) for i in range(limit)]
                grouped = self.news(100, hours=10)
                grouped["sources"] = ["Medio A", "Medio B"]
                grouped["coverages"] = [{"title": "Última noticia original de B", "source": "Medio B",
                                         "link": grouped["link"],
                                         "published": (self.now - timedelta(minutes=1)).isoformat()}]
                stories.append(grouped)
                before = deepcopy(stories)
                with tempfile.TemporaryDirectory() as folder:
                    write_public_feeds(folder, stories, self.now, self.site, {"tecnologia": "Tecnología"})
                    path = Path(folder, "rss", "tecnologia.xml") if limit == 24 else Path(folder, "rss.xml")
                    rows = ET.parse(path).findall("./channel/item")
                    self.assertEqual(len(rows), limit)
                    self.assertEqual(rows[0].findtext("link"), grouped["link"])
                    self.assertEqual(rows[0].findtext("title"), "Última noticia original de B")
                self.assertEqual(stories, before)

    def test_writes_index_and_all_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_public_feeds(tmp, [self.news(1), self.news(2, cat="nacional")],
                                       self.now, self.site, {"tecnologia": "Tecnología", "nacional": "Nacional"})
            self.assertEqual(set(paths), {"rss.xml", "rss/tecnologia.xml", "rss/nacional.xml"})
            for file in paths:
                ET.parse(Path(tmp) / file)
            cat = ET.parse(Path(tmp) / "rss" / "nacional.xml")
            self.assertEqual(len(cat.findall("./channel/item")), 1)

    def test_limits_each_feed_and_keeps_the_original_health_and_climate_categories(self):
        categories = ("nacional", "tecnologia", "salud-ciencia", "medioambiente")
        stories = [self.news(index * 30 + i, cat=category)
                   for index, category in enumerate(categories) for i in range(30)]
        before = deepcopy(stories)
        with tempfile.TemporaryDirectory() as folder:
            write_public_feeds(folder, stories, self.now, self.site,
                               {c: c for c in ("nacional", "tecnologia", "salud-ciencia", "medioambiente")})
            self.assertEqual(len(ET.parse(Path(folder, "rss.xml")).findall("./channel/item")), 50)
            for category in ("nacional", "tecnologia", "salud-ciencia", "medioambiente"):
                rows = ET.parse(Path(folder, "rss", category + ".xml")).findall("./channel/item")
                self.assertEqual(len(rows), 24)
                allowed = {s["link"] for s in stories if s["category"] == category}
                self.assertTrue(all(node.findtext("link") in allowed for node in rows))
        self.assertEqual(stories, before)

    def test_build_site_publishes_original_category_rss_and_preserves_search(self):
        import fetch_noticias as news
        from html.parser import HTMLParser
        class FooterLinks(HTMLParser):
            def __init__(self):
                super().__init__(); self.footer = False; self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "footer": self.footer = True
                if tag == "a" and self.footer: self.links.append(attrs.get("href"))
            def handle_endtag(self, tag):
                if tag == "footer": self.footer = False
        stories = [self.news(i, cat=category) for i, category in
                   enumerate(("salud-ciencia", "salud-ciencia", "medioambiente", "medioambiente"))]
        stories[0]["metadata_only"] = True
        before = deepcopy(stories)
        with tempfile.TemporaryDirectory() as folder:
            news.build_site(stories, self.now, folder)
            for category in ("salud-ciencia", "medioambiente"):
                path = Path(folder, "rss", category + ".xml")
                self.assertTrue(path.is_file(), f"No se generó el RSS de {category}")
                root = ET.parse(path)
                self.assertEqual(len(root.findall("./channel/item")), 2)
            page = Path(folder, "index.html").read_text(encoding="utf-8")
            parser = FooterLinks(); parser.feed(page)
            self.assertIn("rss.xml", parser.links)
            self.assertIn('data-key="salud-ciencia"', page)
            self.assertIn('data-key="medioambiente"', page)
            self.assertIn('id="search-input"', page)
            rss = Path(folder, "rss.xml").read_text(encoding="utf-8")
            self.assertNotIn("foto.example", rss)
            self.assertNotIn("Texto que no se debe copiar", rss)
        self.assertEqual(stories, before)

    def test_template_exposes_rss_without_new_navigation_or_scripts(self):
        from pathlib import Path
        template = Path("template.html").read_text(encoding="utf-8")
        self.assertIn('type="application/rss+xml"', template)
        self.assertIn('href="rss.xml"', template)


if __name__ == "__main__":
    unittest.main()
