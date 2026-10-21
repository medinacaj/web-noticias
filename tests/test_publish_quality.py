"""Auditoría prepublicación: estadísticas, advertencias y puerta QA."""
import unittest
from pathlib import Path
from scripts.audit_news_health import inspect_news, alerts


class PublishQualityTests(unittest.TestCase):
    def test_coverage_diagnostics_are_not_fake_stories(self):
        news = [
            {"category": "salud-ciencia", "sources": ["Medio A"],
             "summary": "", "image": ""},
            {"category": "medioambiente", "sources": ["Medio A"],
             "summary": "Contenido", "image": "https://foto.example/nota"},
        ]
        report = inspect_news(news)
        self.assertEqual(report["noticias"], 2)
        self.assertEqual(report["categorias"]["salud-ciencia"], 1)
        self.assertEqual(report["porcentaje_fuente_principal"], 100)
        self.assertEqual(report["porcentaje_con_resumen"], 50)
        self.assertTrue(any("Medio A" in warning for warning in alerts(report)))
        self.assertEqual(len(news), 2)

    def test_empty_input_returns_safe_metrics(self):
        report = inspect_news([])
        self.assertEqual(report["noticias"], 0)
        self.assertEqual(report["porcentaje_con_resumen"], 0)
        self.assertTrue(alerts(report))

    def test_hourly_workflow_gates_deploy_before_upload(self):
        workflow = Path(".github/workflows/update-news.yml").read_text(encoding="utf-8")
        self.assertLess(workflow.index("Verificar contenido y calidad antes de publicar"),
                        workflow.index("Guardar historial de noticias"))
        self.assertLess(workflow.index("Verificar contenido y calidad antes de publicar"),
                        workflow.index("Subir sitio generado"))
        for expected in ("python3 scripts/validate_history.py",
                         "python3 scripts/audit_editorial_quality.py --strict",
                         "python3 scripts/audit_seo.py --site public",
                         "python3 scripts/audit_news_health.py"):
            self.assertIn(expected, workflow)

    def test_newsletter_variables_are_opt_in_not_credentials(self):
        workflow = Path(".github/workflows/update-news.yml").read_text(encoding="utf-8")
        for variable in ("NEWSLETTER_READY", "NEWSLETTER_SUBSCRIBE_URL",
                         "NEWSLETTER_PRIVACY_URL", "NEWSLETTER_UNSUBSCRIBE_URL"):
            self.assertIn(f"{variable}: ${{{{ vars.{variable} }}}}", workflow)
        self.assertNotIn("NEWSLETTER_READY: true", workflow)
        self.assertNotIn("NEWSLETTER_READY: 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
