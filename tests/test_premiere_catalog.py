"""Fechas verificadas y noticias directas, conservando las guías semanales."""
from datetime import datetime, timezone
import importlib
import unittest

from scripts.premiere_catalog import current_premieres, load_catalog
from scripts.culture_content import add_culture_content, content_kind, card_label
import fetch_noticias as news

NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


def sample(**changes):
    return {"title": "Película demostración", "format": "Cine", "platform": "",
            "region": "CL", "verified": True, "release_date": "2026-10-29",
            "source": "Medio", "source_url": "https://ejemplo.cl",
            "link": "https://ejemplo.cl/noticias/pelicula-demostracion",
            "verification_url": "https://cine.cl/cartelera/pelicula", **changes}


class PremiereCatalogTests(unittest.TestCase):
    def collect(self, *items):
        return current_premieres(items, NOW, restrictions=[])

    def test_verified_release_with_direct_article(self):
        found = self.collect(sample())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["title"], "Película demostración")
        self.assertEqual(found[0]["release_date"], "2026-10-29")
        self.assertEqual(found[0]["link"], sample()["link"])
        self.assertIsNone(found[0]["published"])
        self.assertEqual(found[0]["content_kind"], "premiere")
        self.assertEqual(found[0]["image"], "")

    def test_reject_invalid_unverified_or_not_chilean(self):
        for entry in (
            sample(verified=False), sample(region="MX"), sample(release_date="2026-11-02"),
            sample(release_date="2026-10-20"), sample(release_date="2026-10-99"),
            sample(link="javascript:alert(1)"),
            sample(source_url="https://ejemplo.cl.evil.test"),
            sample(link="https://ejemplo.cl.evil.test/otro"),
            sample(verification_url="http://cine.cl/pelicula"),
            sample(verification_url="https://127.0.0.1/internal"),
            sample(format="Streaming", platform=""),
        ):
            with self.subTest(entry=entry):
                self.assertEqual(self.collect(entry), [])

    def test_week_rollover_and_deduplication(self):
        item = sample(release_date="2026-11-01")
        self.assertEqual(len(self.collect(item, dict(item))), 1)
        self.assertEqual(current_premieres([item], datetime(2026, 11, 2, 12, tzinfo=timezone.utc), restrictions=[]), [])

    def test_premiere_and_guides_coexist_without_false_article_dates(self):
        by_cat = add_culture_content({}, NOW, premiere_items=[sample()], release_guides=[])
        items = by_cat["cine-streaming"]
        self.assertEqual(len(items), 1)
        self.assertEqual(content_kind(items[0]), "premiere")
        self.assertIn("cines", card_label(items[0]))
        rendered = news.render_sections(by_cat, NOW)
        self.assertIn("Película demostración", rendered)
        self.assertIn("Estreno en Chile", rendered)
        self.assertNotIn("Guía publicada", rendered)
        self.assertIn(sample()["link"], rendered)
        self.assertNotIn('target="_blank"', rendered)

    def test_catalog_has_no_out_of_week_releases(self):
        entries = load_catalog()
        self.assertGreaterEqual(len(entries), 2)
        self.assertTrue(all(x.get("verified") is True for x in entries))
        self.assertEqual(len(current_premieres(entries, NOW, restrictions=[])), len(entries))


if __name__ == "__main__":
    unittest.main()
