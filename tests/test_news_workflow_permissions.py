"""Comprueba seguridad de permisos y continuidad del despliegue de noticias.

Inspección offline; no contacta medios externos ni necesita tokens.
"""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/update-news.yml"


class NewsWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = WORKFLOW.read_text(encoding="utf8")
        cls.header, jobs = src.split("\njobs:\n", 1)
        cls.generar, tail = jobs.split("\n  guardar_historial:\n", 1)
        cls.historial, cls.pages = tail.split("\n  publicar_pages:\n", 1)

    def test_triggers_and_concurrency_preserved(self):
        self.assertIn('cron: "7 * * * *"', self.header)
        self.assertIn("workflow_dispatch: {}", self.header)
        self.assertIn("branches: [main]", self.header)
        self.assertIn("group: noticias-del-momento", self.header)
        self.assertIn("cancel-in-progress: false", self.header)

    def test_generation_never_receives_write_token_or_pages_permission(self):
        self.assertIn("permissions:\n  contents: read", self.header)
        self.assertIn("    permissions:\n      contents: read", self.generar)
        self.assertNotIn("contents: write", self.generar)
        self.assertNotIn("pages: write", self.generar)
        self.assertNotIn("id-token: write", self.generar)
        self.assertNotIn("git push", self.generar)
        self.assertEqual(self.generar.count("persist-credentials: false"), 3)
        self.assertNotIn("persist-credentials: true", self.generar)
        self.assertIn("GNEWS_API_KEY: ${{ secrets.GNEWS_API_KEY }}", self.generar)
        self.assertNotIn("GNEWS_API_KEY", self.historial)
        self.assertNotIn("GNEWS_API_KEY", self.pages)

    def test_only_history_writer_has_git_write_permission(self):
        self.assertIn("needs: generar", self.historial)
        self.assertIn("contents: write", self.historial)
        self.assertIn("persist-credentials: true", self.historial)
        self.assertIn("ref: news-data", self.historial)
        self.assertNotIn("fetch_noticias.py", self.historial)
        self.assertNotIn("actions/deploy-pages", self.historial)
        self.assertIn("--data-repo .news-data", self.historial)
        self.assertIn("--state build-news-state/state.json", self.historial)
        self.assertIn("python3 scripts/validate_history.py", self.historial)

    def test_pages_waits_for_history_and_has_only_deploy_privileges(self):
        self.assertIn("needs: [generar, guardar_historial]", self.pages)
        self.assertIn("pages: write", self.pages)
        self.assertIn("id-token: write", self.pages)
        self.assertIn("contents: read", self.pages)
        self.assertNotIn("contents: write", self.pages)
        self.assertNotIn("actions/checkout", self.pages)
        self.assertNotIn("fetch_noticias.py", self.pages)
        self.assertIn("actions/deploy-pages@v4", self.pages)

    def test_history_data_artifact_and_pages_artifact_are_independent(self):
        self.assertIn("name: news-history-data", self.generar)
        self.assertIn("retention-days: 1", self.generar)
        self.assertIn("actions/upload-pages-artifact@v3", self.generar)
        self.assertIn("path: public", self.generar)
        self.assertIn("actions/download-artifact@v4", self.historial)
        self.assertIn("name: news-history-data", self.historial)

    def test_existing_quality_and_monetization_are_unchanged(self):
        for item in (
            "python3 -m unittest discover -s tests -v",
            "python3 scripts/validate_history.py",
            "python3 scripts/audit_editorial_quality.py --strict",
            "python3 scripts/audit_seo.py --site public",
            "python3 scripts/audit_news_health.py",
            "python3 fetch_noticias.py",
            "python3 scripts/news_data.py load",
            "ADSENSE_PUBLISHER_ID:",
            "NEWSLETTER_READY:",
            "SITE_URL:",
        ):
            self.assertIn(item, self.generar, item)

    def test_workflow_only_deploys_from_main(self):
        for section in (self.generar, self.historial, self.pages):
            self.assertIn("github.ref == 'refs/heads/main'", section)
        self.assertIn("ref: main", self.generar)
        self.assertIn("environment:\n      name: github-pages", self.generar)
        self.assertIn("environment:\n      name: github-pages", self.pages)


if __name__ == "__main__":
    unittest.main()
