"""Pruebas sin red del monitor de GitHub Pages."""
import unittest
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.check_news_site import assess, DEFAULT_SITE, MAX_AGE_HOURS


class PublicHealthTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("jq"), "jq is required by the Actions runner")
    def test_issue_management_runs_real_shell_block_with_paginated_results(self):
        workflow = Path(".github/workflows/monitor.yml").read_text(encoding="utf-8")
        step = workflow.split("      - name: Gestionar incidencia única y cierre por recuperación", 1)[1]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        syntax = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        title = "Web Noticias: alerta automática de publicación"
        newest = [{"number": n, "title": "Otra incidencia"} for n in range(300, 200, -1)]
        old = {"number": 2, "title": title}
        newer = {"number": 101, "title": title}
        pull_request = {"number": 1, "title": title, "pull_request": {}}
        cases = [
            ([newest, [newer, old, pull_request]], "failure", 1, [("edit", "2")]),
            ([newest, [old, pull_request]], "success", 0, [("comment", "2"), ("close", "2")]),
            ([newest, [pull_request]], "failure", 1, [("create", "--repo")]),
        ]
        for pages, check_result, expected_exit, expected_actions in cases:
            with self.subTest(check_result=check_result, expected_actions=expected_actions), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                (folder / "pages.json").write_text(json.dumps(pages), encoding="utf-8")
                (folder / "health-report.txt").write_text("Public health fixture\n", encoding="utf-8")
                executable = folder / "gh"
                executable.write_text(textwrap.dedent('''\
                    #!/usr/bin/env python3
                    import json, os, pathlib, sys
                    args = sys.argv[1:]
                    if "--slurp" in args:
                        sys.stderr.write("unknown flag: --slurp (gh 2.46)\\n")
                        sys.exit(1)
                    if args[0] == "api":
                        assert "--paginate" in args
                        for page in json.loads(pathlib.Path(os.environ["PAGES_FIXTURE"]).read_text()):
                            print(json.dumps(page))
                    elif args[0] == "issue":
                        with open(os.environ["GH_CALLS"], "a") as handle:
                            handle.write(json.dumps(args[1:]) + "\\n")
                    else:
                        sys.exit(2)
                    '''), encoding="utf-8")
                executable.chmod(0o755)
                env = {**os.environ, "PATH": tmp + os.pathsep + os.environ.get("PATH", ""),
                       "GH_REPO": "fixture/repository", "CHECK_RESULT": check_result,
                       "GITHUB_STEP_SUMMARY": str(folder / "summary.txt"),
                       "PAGES_FIXTURE": str(folder / "pages.json"), "GH_CALLS": str(folder / "calls.jsonl")}
                result = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                                        cwd=tmp, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                calls_file = folder / "calls.jsonl"
                calls = [json.loads(line) for line in calls_file.read_text().splitlines()] if calls_file.exists() else []
                self.assertEqual([(call[0], call[1]) for call in calls], expected_actions, result.stderr)

    def setUp(self):
        self.now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        self.sitemap = (
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{DEFAULT_SITE}</loc></url></urlset>'
        )

    def page(self, hours=1):
        timestamp = (self.now - timedelta(hours=hours)).isoformat()
        return ('<!doctype html><html><head><title>Noticias del Momento</title></head>'
                '<body><time id="updated-at" datetime="' + timestamp
                + '">Actualizado</time></body></html>')

    def test_healthy(self):
        self.assertEqual(assess(self.page(), self.sitemap, self.now), [])

    def test_stale_publication(self):
        warnings = assess(self.page(MAX_AGE_HOURS + 1), self.sitemap, self.now)
        self.assertTrue(any("desactualizada" in x for x in warnings))

    def test_missing_timestamp_and_title(self):
        warnings = assess("<html><body>Fuera de servicio</body></html>", self.sitemap, self.now)
        self.assertEqual(len(warnings), 2)

    def test_bad_sitemap_or_failed_deployment(self):
        warnings = assess(self.page(), "<wrong/>", self.now, deployment="failure")
        self.assertTrue(any("despliegue" in x for x in warnings))
        self.assertTrue(any("sitemap" in x for x in warnings))

    def test_monitor_is_separate_and_least_privileged(self):
        workflow = Path(".github/workflows/monitor.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("issues: write", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("Vigilar Web Noticias publicado", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("secrets.GNEWS_API_KEY", workflow)


if __name__ == "__main__":
    unittest.main()

