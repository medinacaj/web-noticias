"""Archivo «Últimos 7 días»: una página por día, noindex, sin días vacíos (2026-10-25)."""
import os
import json
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fetch_noticias as news
from scripts.archive_pages import archive_days, render_archive
from scripts.presentation_groups import canonical_section

NOW = datetime(2026, 10, 25, 15, tzinfo=timezone.utc)  # 12:00 en Chile


def record(title, published, category="nacional", link=None):
    return {"title": title, "link": link or f"https://medio.example/{abs(hash(title))}",
            "category": category, "published": published, "sources": ["Medio A"]}


class ArchivePagesTests(unittest.TestCase):
    def test_seven_previous_chile_days_skip_today_and_empty_days(self):
        days = archive_days(NOW)
        self.assertEqual([d.isoformat() for d in (days[0], days[-1])], ["2026-10-24", "2026-10-18"])
        archive = [record("Ayer", "2026-10-24T15:00:00Z"),
                   # 01:00 UTC del 24 es todavía 23 de octubre en Chile.
                   record("Anteayer en Chile", "2026-10-24T01:00:00Z"),
                   record("Hoy en portada", "2026-10-25T13:00:00Z"),
                   record("Demasiado antiguo", "2026-10-10T12:00:00Z")]
        files = render_archive(archive, NOW, "https://sitio.example", news.CATEGORIES, canonical_section)
        self.assertEqual(sorted(files), ["archivo/2026-10-23.html", "archivo/2026-10-24.html", "archivo/index.html"])
        self.assertIn("Anteayer en Chile", files["archivo/2026-10-23.html"])
        self.assertNotIn("Hoy en portada", "".join(files.values()))

    def test_pages_are_noindex_with_one_h1_and_canonical(self):
        files = render_archive([record("Ayer", "2026-10-24T15:00:00Z")], NOW, "https://sitio.example",
                               news.CATEGORIES, canonical_section)
        for name, page in files.items():
            self.assertIn('<meta name="robots" content="noindex, follow">', page, name)
            self.assertEqual(page.count("<h1"), 1, name)
            self.assertIn('<link rel="canonical" href="https://sitio.example/archivo/', page)
            self.assertIn('href="https://sitio.example/favicon.svg"', page)
            self.assertIn('property="og:title"', page)
            self.assertIn('name="twitter:card"', page)
            structured = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page).group(1))
            self.assertEqual(structured['@type'], 'CollectionPage')
            self.assertTrue(structured['url'].startswith('https://sitio.example/archivo/'))

    def test_health_is_shown_inside_science_and_technology(self):
        archive = [record("Vacuna nueva", "2026-10-24T15:00:00Z", "salud-ciencia"),
                   record("Chip nuevo", "2026-10-24T16:00:00Z", "tecnologia")]
        page = render_archive(archive, NOW, "https://s.example", news.CATEGORIES, canonical_section)["archivo/2026-10-24.html"]
        self.assertEqual(page.count('data-section="tecnologia"'), 1)
        self.assertNotIn('data-section="salud-ciencia"', page)
        self.assertIn("Salud · Medio A", page)
        # Con una sola sección no se muestran filtros.
        self.assertNotIn("data-section-filter=", page)

    def test_headline_text_is_escaped(self):
        page = render_archive([record("<script>x</script>", "2026-10-24T15:00:00Z")], NOW, "https://s.example",
                              news.CATEGORIES, canonical_section)["archivo/2026-10-24.html"]
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)

    def test_build_writes_archive_clears_stale_days_and_keeps_it_out_of_sitemap(self):
        story = {"title": "Noticia de hoy", "category": "nacional", "sources": ["Medio"],
                 "published": NOW.isoformat(), "link": "https://medio.example/hoy", "image": "", "summary": ""}
        with tempfile.TemporaryDirectory() as folder:
            stale = Path(folder, "archivo", "2020-01-01.html")
            stale.parent.mkdir(parents=True)
            stale.write_text("vieja")
            news.build_site([story], NOW, folder, signals_archive=[record("Ayer", "2026-10-24T15:00:00Z")])
            self.assertFalse(stale.exists())
            self.assertTrue(Path(folder, "archivo", "2026-10-24.html").exists())
            self.assertNotIn("archivo", Path(folder, "sitemap.xml").read_text())
            self.assertIn('href="archivo/">Últimos 7 días</a>', Path(folder, "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
