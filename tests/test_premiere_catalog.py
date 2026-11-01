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

    def test_catalog_current_and_next_week_have_no_cross_leak(self):
        entries = load_catalog()
        self.assertGreaterEqual(len(entries), 6)
        self.assertTrue(all(x.get("verified") is True for x in entries))
        current = current_premieres(entries, NOW, restrictions=[])
        next_week_now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
        next_week = current_premieres(entries, next_week_now, restrictions=[])
        self.assertEqual(len(current), 4)
        self.assertEqual(len(next_week), 2)
        self.assertEqual(len(current) + len(next_week), len(entries))
        self.assertEqual({x["title"] for x in next_week},
                         {"Caballo Salvaje Nueve", "Todo Vale (temporada 2)"})
        # La puerta real de permisos por fuente sigue activa, no sólo la prueba
        # con restricciones vacías.
        self.assertEqual(current_premieres(entries, next_week_now), next_week)


if __name__ == "__main__":
    unittest.main()
