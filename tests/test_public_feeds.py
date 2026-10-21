"""RSS de Web Noticias: solo enlaces de origen, atribución y feed válido."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

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

    def test_writes_index_and_all_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_public_feeds(tmp, [self.news(1), self.news(2, cat="nacional")],
                                       self.now, self.site, {"tecnologia": "Tecnología", "nacional": "Nacional"})
            self.assertEqual(set(paths), {"rss.xml", "rss/tecnologia.xml", "rss/nacional.xml"})
            for file in paths:
                ET.parse(Path(tmp) / file)
            cat = ET.parse(Path(tmp) / "rss" / "nacional.xml")
            self.assertEqual(len(cat.findall("./channel/item")), 1)

    def test_template_exposes_rss_without_new_navigation_or_scripts(self):
        from pathlib import Path
        template = Path("template.html").read_text(encoding="utf-8")
        self.assertIn('type="application/rss+xml"', template)
        self.assertIn('href="rss.xml"', template)


if __name__ == "__main__":
    unittest.main()
