"""Aislamiento de la rama events-data con repositorios Git locales reales (sin red).

Detecta destinos de push equivocados, escrituras obsoletas, archivos no
permitidos y datos que no son snapshots válidos.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/events_data.py"
SNAP = "eventos/crawled_events.json"


class EventsDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.seed = self.root / "seed"
        self.data = self.root / "checkout"
        self.work = self.root / "work"
        self.state = self.root / "state.json"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "events-data", str(self.seed))
        self.git(self.seed, "config", "user.name", "Tests")
        self.git(self.seed, "config", "user.email", "tests@example.invalid")
        self.write_snapshot(self.seed / SNAP, "inicial")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "seed")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "HEAD:refs/heads/main", "HEAD:refs/heads/events-data")
        self.git(self.root, "clone", "--branch", "events-data", str(self.remote), str(self.data))
        hook = self.remote / "hooks/pre-receive"
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n  test "$ref" = refs/heads/events-data || exit 1\ndone\n')
        hook.chmod(0o755)

    def git(self, cwd, *args, check=True):
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
        return subprocess.run(["git", "-C", str(cwd), *args], text=True,
                              capture_output=True, check=check, env=env)

    def write_snapshot(self, path, title):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"events": [{"title": title}]}))

    def run_helper(self, operation):
        return subprocess.run([sys.executable, str(SCRIPT), operation, "--data-repo", str(self.data),
                               "--workdir", str(self.work), "--state", str(self.state)],
                              text=True, capture_output=True)

    def remote_file(self, path):
        return self.git(self.remote, "show", f"events-data:{path}", check=False)

    def test_load_and_persist_only_allowed_paths(self):
        self.assertEqual(self.run_helper("load").returncode, 0)
        self.assertEqual(json.loads((self.work / SNAP).read_text())["events"][0]["title"], "inicial")
        self.write_snapshot(self.work / SNAP, "nuevo")
        (self.work / "eventos/coverage.md").write_text("# Cobertura\n")
        (self.work / "eventos/otro.py").write_text("print('no')\n")
        result = self.run_helper("persist")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nuevo", self.remote_file(SNAP).stdout)
        self.assertEqual(self.remote_file("eventos/coverage.md").stdout, "# Cobertura\n")
        self.assertNotEqual(self.remote_file("eventos/otro.py").returncode, 0)
        self.assertEqual(self.git(self.remote, "log", "--format=%s", "-1", "main").stdout.strip(), "seed")

    def test_invalid_snapshot_is_rejected(self):
        self.run_helper("load")
        (self.work / SNAP).write_text(json.dumps({"eventos": []}))
        result = self.run_helper("persist")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inicial", self.remote_file(SNAP).stdout)

    def test_concurrent_update_fails_closed(self):
        self.run_helper("load")
        self.write_snapshot(self.seed / SNAP, "otra corrida")
        self.git(self.seed, "commit", "-am", "concurrent")
        self.git(self.seed, "push", "origin", "HEAD:refs/heads/events-data")
        self.write_snapshot(self.work / SNAP, "obsoleto")
        result = self.run_helper("persist")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Concurrent", result.stderr)
        self.assertIn("otra corrida", self.remote_file(SNAP).stdout)


if __name__ == "__main__":
    unittest.main()
