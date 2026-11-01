"""actualizar.py con fetcher falso y archivos temporales (sin red)."""
import json
import os
import shutil
import tempfile
import unittest

from tests.helpers import COMMUNES, ROOT, db, memory_db
import actualizar
from tests.test_scrapers import EVENT_PAGE, HOME, fake_fetcher

PAGES = {"https://teatro.demo.cl/": HOME, "https://teatro.demo.cl/obra-negra-ester/": EVENT_PAGE}
SOURCES = {"_notes": "", "sources": [
    {"name": "Teatro Demo", "url": "https://teatro.demo.cl/", "enabled": True, "source_type": "venue",
     "source_priority": 1, "official": True, "deep_crawl": True, "max_pages": 5, "max_depth": 1, "timeout": 5,
     "radar_only": False, "commune": "Concepción", "province": "Concepción", "parser": "generic",
     "verified_live": False, "notes": "No verificada en vivo: algo; el scraper NUNCA se ejecutó contra esta URL. Nota propia."},
    {"name": "Caída", "url": "https://caida.cl/", "enabled": True, "source_type": "municipal",
     "source_priority": 1, "official": True, "deep_crawl": False, "max_pages": 1, "max_depth": 0, "timeout": 5,
     "radar_only": False, "commune": "Lota", "province": "Concepción", "parser": "generic",
     "verified_live": True, "notes": "Nota de Lota."},
    {"name": "Apagada", "url": "https://x.cl/", "enabled": False, "source_type": "media", "source_priority": 3,
     "official": False, "deep_crawl": False, "max_pages": 1, "max_depth": 0, "timeout": 5, "radar_only": True,
     "commune": None, "province": None, "parser": "generic", "verified_live": False, "notes": "Off."}]}


class ActualizarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.crawled = os.path.join(self.tmp, "crawled.json")
        self.sources = os.path.join(self.tmp, "sources.json")
        with open(self.sources, "w", encoding="utf-8") as f:
            json.dump(SOURCES, f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_once(self):
        return actualizar.main([], fetcher=fake_fetcher(PAGES), crawled_path=self.crawled,
                               sources_path=self.sources)

    def test_snapshot_and_sources_updated_from_real_responses(self):
        self.assertEqual(self.run_once(), 0)
        with open(self.crawled, encoding="utf-8") as f:
            snap = json.load(f)
        self.assertEqual([e["title"] for e in snap["events"]], ["La Negra Ester"])
        self.assertEqual({r["source_name"]: r["ok"] for r in snap["runs"]}, {"Teatro Demo": 1, "Caída": 0})
        with open(self.sources, encoding="utf-8") as f:
            src = {s["name"]: s for s in json.load(f)["sources"]}
        self.assertTrue(src["Teatro Demo"]["verified_live"])
        self.assertTrue(src["Teatro Demo"]["notes"].startswith("Verificada en vivo el "))
        self.assertTrue(src["Teatro Demo"]["notes"].endswith("Nota propia."))
        self.assertNotIn("NUNCA", src["Teatro Demo"]["notes"])
        self.assertFalse(src["Caída"]["verified_live"])  # antes true: ahora refleja la falla real
        self.assertIn("falló", src["Caída"]["notes"])
        self.assertEqual(src["Apagada"]["notes"], "Off.")
        self.assertNotIn("last_live_check", src["Apagada"])

    def test_snapshot_and_status_paths_leave_config_untouched(self):
        # Así corre el workflow de web-noticias: config/ es código revisado; el estado va a events-data.
        snap = os.path.join(self.tmp, "datos", "crawled.json")
        status = os.path.join(self.tmp, "datos", "sources_status.json")
        with open(self.sources, encoding="utf-8") as f:
            before = f.read()
        code = actualizar.main(["--snapshot", snap, "--estado-fuentes", status],
                               fetcher=fake_fetcher(PAGES), sources_path=self.sources)
        self.assertEqual(code, 0)
        with open(self.sources, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)
        with open(status, encoding="utf-8") as f:
            self.assertTrue({s["name"]: s for s in json.load(f)["sources"]}["Teatro Demo"]["verified_live"])
        with open(snap, encoding="utf-8") as f:
            self.assertEqual([e["title"] for e in json.load(f)["events"]], ["La Negra Ester"])

    def test_second_run_no_duplicates_and_notes_not_stacked(self):
        self.run_once()
        self.run_once()
        with open(self.crawled, encoding="utf-8") as f:
            snap = json.load(f)
        self.assertEqual(len(snap["events"]), 1)
        self.assertEqual(snap["summary"]["events_inserted"], 0)
        with open(self.sources, encoding="utf-8") as f:
            src = {s["name"]: s for s in json.load(f)["sources"]}
        self.assertEqual(src["Teatro Demo"]["notes"].count("Verificada en vivo"), 1)
        self.assertEqual(src["Caída"]["notes"].count("falló"), 1)

    def test_rapid_second_run_keeps_event_and_fresh_http_evidence(self):
        self.assertEqual(self.run_once(), 0)
        with open(self.crawled, encoding="utf-8") as f:
            previous = json.load(f)
        self.assertIn("source_state", previous)
        self.assertIn("Teatro Demo", previous["source_state"])
        self.assertEqual(previous["source_state"]["Teatro Demo"]["last_http_status"], 200)
        self.assertEqual(self.run_once(), 0)
        with open(self.crawled, encoding="utf-8") as f:
            after = json.load(f)
        self.assertEqual([e["title"] for e in after["events"]], ["La Negra Ester"])
        self.assertEqual(after["summary"]["sources_attempted"], len(after["runs"]))
        self.assertGreater(after["summary"]["sources_attempted"], 0)
        self.assertTrue(any(r["ok"] for r in after["runs"]))
        self.assertEqual(after["source_state"]["Teatro Demo"]["last_http_status"], 200)

    def test_skipped_source_status_reports_cached_http_as_previous(self):
        self.assertEqual(self.run_once(), 0)
        with open(self.crawled, encoding="utf-8") as file:
            state = json.load(file)["source_state"]
        actualizar.update_sources_file(
            self.sources, [], source_state=state, skipped=["Teatro Demo", "Caída"])
        with open(self.sources, encoding="utf-8") as file:
            statuses = {source["name"]: source for source in json.load(file)["sources"]}
        self.assertIn("Omitida por cadencia", statuses["Teatro Demo"]["notes"])
        self.assertTrue(statuses["Teatro Demo"]["verified_live"])
        self.assertEqual(statuses["Teatro Demo"]["last_live_check"]["http_status"], 200)
        self.assertEqual(statuses["Teatro Demo"]["last_live_check"]["at"],
                         state["Teatro Demo"]["last_checked_at"])
        self.assertFalse(statuses["Caída"]["verified_live"])
        self.assertEqual(statuses["Caída"]["last_live_check"]["http_status"], 404)

    def test_app_loads_snapshot_idempotently(self):
        self.run_once()
        conn = memory_db()
        r1 = db.load_crawled(conn, self.crawled, COMMUNES)
        r2 = db.load_crawled(conn, self.crawled, COMMUNES)
        self.assertEqual((r1["inserted"], r2["inserted"]), (1, 0))
        self.assertEqual(r2["runs"], 0)
        st = db.compute_status(conn, [], COMMUNES)
        self.assertEqual((st["events_crawled"], st["sources_with_successful_run"]), (1, 1))

    def test_missing_snapshot_is_fine(self):
        r = db.load_crawled(memory_db(), os.path.join(self.tmp, "no.json"), COMMUNES)
        self.assertEqual(r["inserted"], 0)

    def test_repo_snapshot_valid_if_present(self):
        path = os.path.join(ROOT, "data", "crawled_events.json")
        if os.path.exists(path):
            db.load_crawled(memory_db(), path, COMMUNES)


if __name__ == "__main__":
    unittest.main()


class PageEventsAreRevalidatedTests(unittest.TestCase):
    def test_page_events_from_previous_snapshot_are_not_reloaded(self):
        from scrapers import event_page
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "snap.json")
            base = {"title": "Concierto", "date": "2030-05-10", "commune": "Concepción",
                    "source": "Teatro Demo", "source_url": "https://t.cl/1", "category": "Cultura"}
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"events": [dict(base, tags=[event_page.PAGE_TAG]),
                                      dict(base, title="Ópera", source_url="https://t.cl/2", tags=[])]}, f)
            conn = memory_db()
            counts = db.load_crawled(conn, path, COMMUNES, skip_tags=(event_page.PAGE_TAG,))
            self.assertEqual(counts["inserted"], 1)
            titles = [r["title"] for r in conn.execute("SELECT title FROM events")]
            self.assertEqual(titles, ["Ópera"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class FailedSourceKeepsPageEventsTests(unittest.TestCase):
    def test_page_events_survive_only_when_their_source_failed(self):
        from scrapers import event_page
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "snap.json")
            tag = [event_page.PAGE_TAG]
            evs = [{"title": "Taller", "date": "2030-11-03", "commune": "Concepción", "source": "FTB",
                    "source_url": "https://ftb.cl/taller/", "tags": tag},
                   {"title": "Obra", "date": "2030-11-04", "commune": "Concepción", "source": "Teatro",
                    "source_url": "https://t.cl/obra/", "tags": tag},
                   {"title": "Pasado", "date": "2001-01-01", "commune": "Concepción", "source": "FTB",
                    "source_url": "https://ftb.cl/pasado/", "tags": tag}]
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"events": evs}, f)
            conn = memory_db()
            n = db.restore_tagged_events(conn, path, COMMUNES, event_page.PAGE_TAG, skip_sources={"Teatro"})
            self.assertEqual(n, 1)
            self.assertEqual([r["title"] for r in conn.execute("SELECT title FROM events")], ["Taller"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
