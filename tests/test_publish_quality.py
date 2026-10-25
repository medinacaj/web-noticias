"""Auditoría prepublicación: estadísticas, advertencias y puerta QA."""
import unittest
from pathlib import Path
from datetime import datetime, timezone
from scripts.audit_news_health import inspect_news, alerts


class PublishQualityTests(unittest.TestCase):
    def test_publisher_aliases_count_together_and_keep_first_visible_name(self):
        for links in (False, True):
            with self.subTest(editorial_links=links):
                names = ("BBC Mundo", "BBC", "BBC News Mundo", "BBC Mundo")
                news = [{"sources": [name], **(
                    {"link": f"https://www.bbc.com/mundo/{i}"} if links else {})}
                    for i, name in enumerate(names)]
                report = inspect_news(news)
                self.assertEqual(report["porcentaje_fuente_principal"], 100)
                self.assertEqual(report["fuente_mas_frecuente"], "BBC Mundo")
                self.assertTrue(any("Alta concentración: BBC Mundo (100.0%)" in warning
                                    for warning in alerts(report)))

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

    def test_warns_if_news_is_stale_without_blocking(self):
        news = [{"category": "nacional", "sources": ["A"],
                 "published": "2026-10-20T10:00:00Z"}]
        report = inspect_news(news, now=datetime(2026, 10, 20, 15, tzinfo=timezone.utc))
        self.assertEqual(report["horas_desde_noticia_mas_reciente"], 5)
        self.assertTrue(any("Última noticia" in x for x in alerts(report)))

    def test_hourly_workflow_gates_deploy_before_upload(self):
        workflow = Path(".github/workflows/update-news.yml").read_text(encoding="utf-8")
        quality = workflow.index("Verificar contenido y calidad antes de publicar")
        history_artifact = workflow.index("Transferir exclusivamente el historial")
        pages_artifact = workflow.index("Preparar artefacto GitHub Pages")
        persist_job = workflow.index("\n  guardar_historial:")
        deploy_job = workflow.index("\n  publicar_pages:")
        self.assertLess(quality, history_artifact)
        self.assertLess(quality, pages_artifact)
        self.assertLess(history_artifact, persist_job)
        self.assertLess(pages_artifact, deploy_job)
        self.assertLess(persist_job, deploy_job)
        # Desplegar depende del job de escritura: un historial fallido bloquea Pages.
        self.assertIn("needs: [generar, guardar_historial]", workflow)
        for expected in ("python3 scripts/validate_history.py",
                         "python3 scripts/audit_editorial_quality.py --strict",
                         "python3 scripts/audit_seo.py --site public",
                         "python3 scripts/audit_news_health.py"):
            self.assertIn(expected, workflow)

    def test_newsletter_variables_are_opt_in_not_credentials(self):
        workflow = Path(".github/workflows/update-news.yml").read_text(encoding="utf-8")
        for variable in ("NEWSLETTER_READY", "NEWSLETTER_PROVIDER", "NEWSLETTER_SUBSCRIBE_URL",
                         "NEWSLETTER_PRIVACY_URL", "NEWSLETTER_UNSUBSCRIBE_URL",
                         "ADSENSE_PUBLISHER_ID", "ADSENSE_READY", "ADSENSE_PRIVACY_URL",
                         "ADSENSE_ROOT_CONTROLLED"):
            self.assertIn(f"{variable}: ${{{{ vars.{variable} }}}}", workflow)
        self.assertNotIn("NEWSLETTER_READY: true", workflow)
        self.assertNotIn("NEWSLETTER_READY: 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
