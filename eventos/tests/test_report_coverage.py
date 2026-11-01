import json
import tempfile
from datetime import date
import unittest
from pathlib import Path
from scripts.report_coverage import report

class CoverageReportTests(unittest.TestCase):
    def test_published_coverage_excludes_unverified_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"snapshot.json").write_text(json.dumps({
                "generated_at":"2026-10-18",
                "events":[{"commune":"Concepción", "date":"2026-10-20"}],
                "possible_events":[{"commune":"Florida","source":"Fuente externa"},{"commune":"Florida","source":"Fuente externa"}],
                "runs":[{"source_name":"Municipal", "ok":1, "http_status":200}]
            }),encoding="utf8")
            (p/"communes.json").write_text(json.dumps({
                "communes":[{"name":"Concepción"},{"name":"Florida"}]
            }),encoding="utf8")
            (p/"sources.json").write_text(json.dumps({
                "sources":[{"name":"Municipal","commune":"Concepción","enabled":True}]
            }),encoding="utf8")
            result=report(p/"snapshot.json",p/"communes.json",p/"sources.json", today=date(2026, 10, 18))
            self.assertIn("Cobertura vigente: 1/2 comunas",result)
            self.assertIn("| Florida | 0 | 0 | 0 | 2 |",result)
            self.assertIn("Diagnóstico del último rastreo por fuente", result)
            self.assertIn("No consultada", result)
            self.assertIn("Revalidación de fichas vigentes", result)


    def test_historical_and_cancelled_events_do_not_inflate_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "snapshot.json").write_text(json.dumps({
                "generated_at": "2026-11-01T12:00:00+00:00",
                "events": [
                    {"commune": "Concepción", "date": "2026-10-25"},
                    {"commune": "Florida", "date": "2026-11-04", "status": "Cancelado"},
                    {"commune": "Talcahuano", "date": "2026-10-26", "end_date": "2026-11-02"},
                    {"commune": "Talcahuano", "date": "fecha-invalida"},
                    {"commune": "Concepción", "date": "2026-11-03"},
                ],
            }), encoding="utf8")
            (p / "communes.json").write_text(json.dumps({"communes": [
                {"name": "Concepción"}, {"name": "Florida"}, {"name": "Talcahuano"},
            ]}), encoding="utf8")
            (p / "sources.json").write_text('{"sources":[]}', encoding="utf8")
            result = report(p / "snapshot.json", p / "communes.json",
                            p / "sources.json", today=date(2026, 11, 1))
            self.assertIn("Cobertura vigente: 2/3 comunas", result)
            self.assertIn("| Concepción | 0 | 0 | 1 | 0 |", result)
            self.assertIn("| Florida | 0 | 0 | 0 | 0 |", result)
            self.assertIn("| Talcahuano | 0 | 0 | 1 | 0 |", result)

    def test_report_separates_candidate_reasons_without_publishing_any(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "snapshot.json").write_text(json.dumps({
                "events": [],
                "possible_events": [
                    {"title": "No comprobado A", "reason": "Sin fecha"},
                    {"title": "No comprobado B", "reason": "Sin fecha"},
                    {"title": "No comprobado C", "reason": "Recinto|<sin comuna>"},
                    {"title": "No comprobado D", "reason": None},
                ],
            }), encoding="utf8")
            (p / "communes.json").write_text(
                '{"communes":[{"name":"Concepción"}]}', encoding="utf8")
            (p / "sources.json").write_text('{"sources":[]}', encoding="utf8")
            result = report(p / "snapshot.json", p / "communes.json",
                            p / "sources.json", today=date(2026, 11, 1))
            self.assertIn("Cobertura vigente: 0/1 comunas", result)
            self.assertIn("Candidatos pendientes por motivo de revisión", result)
            self.assertIn("| Sin fecha | 2 |", result)
            self.assertIn("| Recinto/&lt;sin comuna&gt; | 1 |", result)
            self.assertIn("| Sin motivo | 1 |", result)
            self.assertNotIn("<sin comuna>", result)
            self.assertNotIn("No comprobado A", result)

    def test_alerts_only_enabled_sources_with_three_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "snapshot.json").write_text(json.dumps({
                "events": [], "source_state": {
                    "Fallida|<script>": {
                        "consecutive_failures": 4, "last_http_status": 503,
                        "last_checked_at": "2026-11-01T12:00:00+00:00"},
                    "Desactivada": {"consecutive_failures": 9, "last_http_status": 403},
                    "Temporal": {"consecutive_failures": 2, "last_http_status": 429}
                }
            }), encoding="utf8")
            (p / "communes.json").write_text('{"communes":[]}', encoding="utf8")
            (p / "sources.json").write_text(json.dumps({"sources": [
                {"name": "Fallida|<script>", "enabled": True},
                {"name": "Desactivada", "enabled": False},
                {"name": "Temporal", "enabled": True}
            ]}), encoding="utf8")
            result = report(p / "snapshot.json", p / "communes.json",
                            p / "sources.json", today=date(2026, 11, 1))
            self.assertIn("Alertas de salud por fuente", result)
            self.assertIn("Fallida/&lt;script&gt; | 4 | 503 |", result)
            self.assertNotIn("| Desactivada |", result)
            self.assertNotIn("| Temporal |", result)
            self.assertNotIn("<script>", result)


if __name__=="__main__":
    unittest.main()
