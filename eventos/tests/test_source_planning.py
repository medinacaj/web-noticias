"""Planificación sin falsas verificaciones y revalidación de URLs previamente publicadas."""
from datetime import date, datetime, timedelta, timezone
import unittest

import source_planning


NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def src(name, kind="venue", **extra):
    return {"name": name, "url": f"https://{name.lower()}.cl/",
            "enabled": True, "parser": "generic", "source_type": kind,
            "radar_only": False, **extra}


class SourcePlanningTests(unittest.TestCase):
    def test_default_cadence_and_limits(self):
        self.assertEqual(source_planning.refresh_hours(src("Teatro")), 12)
        self.assertEqual(source_planning.refresh_hours(src("Muni", kind="municipal")), 24)
        self.assertEqual(source_planning.refresh_hours(src("Radar", radar_only=True)), 48)
        self.assertEqual(source_planning.refresh_hours(src("A", refresh_interval_hours=6)), 6)
        self.assertEqual(source_planning.refresh_hours(src("A", refresh_interval_hours=240)), 12)
        self.assertEqual(source_planning.refresh_hours(src("A", refresh_interval_hours="INVALID")), 12)

    def test_due_respects_previous_check_and_manual_force(self):
        sources = [src("Teatro"), src("Municipio", kind="municipal"),
                   src("Radar", radar_only=True)]
        state = {
            "Teatro": {"last_checked_at": (NOW-timedelta(hours=6)).isoformat()},
            "Municipio": {"last_checked_at": (NOW-timedelta(hours=23)).isoformat()},
            "Radar": {"last_checked_at": (NOW-timedelta(hours=30)).isoformat()},
        }
        due, skipped = source_planning.due_sources(sources, state, NOW)
        self.assertEqual([s["name"] for s in due], ["Municipio"])
        self.assertEqual(skipped, ["Teatro", "Radar"])
        forced, skipped_force = source_planning.due_sources(sources, state, NOW, force=True)
        self.assertEqual(len(forced), 3)
        self.assertFalse(skipped_force)
        self.assertEqual(len(source_planning.due_sources(sources, {}, NOW)[0]), 3)

    def test_persistent_state_tracks_last_success_without_marking_skipped_checked(self):
        sources = [src("Teatro"), src("Municipio", kind="municipal")]
        first = source_planning.update_state({}, sources, [
            {"source_name": "Teatro", "finished_at": NOW.isoformat(), "ok": 1, "http_status": 200},
            {"source_name": "Municipio", "finished_at": NOW.isoformat(), "ok": 0, "http_status": 403},
        ])
        self.assertEqual(first["Teatro"]["last_success_at"], NOW.isoformat())
        self.assertEqual(first["Municipio"]["consecutive_failures"], 1)
        changed = source_planning.update_state(first, sources, [
            {"source_name": "Teatro", "finished_at": (NOW+timedelta(days=1)).isoformat(),
             "ok": 0, "http_status": 503}])
        self.assertEqual(changed["Teatro"]["last_success_at"], NOW.isoformat())
        self.assertEqual(changed["Teatro"]["consecutive_failures"], 1)
        self.assertEqual(changed["Municipio"], first["Municipio"])
        self.assertEqual(changed["Municipio"]["last_http_status"], 403)

    def test_only_previously_published_future_same_domain_urls_are_revisited(self):
        source = src("Teatro")
        snap = {"events": [
            {"date": "2026-11-06", "title": "Concierto", "source": "Teatro",
             "source_url": "https://teatro.cl/concierto-1/"},
            {"date": "2026-11-10", "title": "Evento externo", "source": "Teatro",
             "source_url": "https://evil.cl/concierto-2/"},
            {"date": "2026-10-01", "title": "Antiguo", "source": "Teatro",
             "source_url": "https://teatro.cl/old/"},
            {"date": "2026-11-03", "status": "Cancelado", "source": "Teatro",
             "source_url": "https://teatro.cl/cancelado/"},
            {"date": "2026-11-04", "title": "Duplicado", "source": "Teatro",
             "source_url": "https://teatro.cl/concierto-1/"},
            {"date": "2026-11-10", "title": "Pendiente", "source": "Otra",
             "source_url": "https://otra.cl/otro/"},
        ], "possible_events": [
            {"date": "2026-11-15", "source": "Teatro",
             "source_url": "https://teatro.cl/candidato-sin-validar/"}
        ]}
        result = source_planning.remembered_event_urls(snap, [source], date(2026, 11, 1))
        self.assertEqual(result["Teatro"], ["https://teatro.cl/concierto-1/"])

    def test_empty_previous_history_is_safe(self):
        self.assertEqual(source_planning.remembered_event_urls(None, [src("Teatro")], NOW.date()),
                         {"Teatro": []})


if __name__ == "__main__":
    unittest.main()
