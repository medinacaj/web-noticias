"""Exercise news-data isolation using real local Git repositories.

Catches wrong push destinations, stale writes, accidental code execution and
committing unrelated working-tree files. No network or GitHub credentials.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/news_data.py"


class NewsDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.seed = self.root / "seed"
        self.data = self.root / "checkout"
        self.history = self.root / "runtime/data/historial.json"
        self.state = self.root / "state.json"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "main", str(self.seed))
        self.git(self.seed, "config", "user.name", "Tests")
        self.git(self.seed, "config", "user.email", "tests@example.invalid")
        (self.seed / "code.py").write_text("raise RuntimeError('not trusted')\n")
        self.write_history(self.seed / "data/historial.json", "initial")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "seed")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "HEAD:refs/heads/main", "HEAD:refs/heads/news-data")
        self.main_before = self.git(self.remote, "rev-parse", "main").stdout
        self.git(self.root, "clone", "--branch", "news-data", str(self.remote), str(self.data))
        # Reject *all* destinations other than news-data: this is a real push gate.
        hook = self.remote / "hooks/pre-receive"
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n  test "$ref" = refs/heads/news-data || exit 1\ndone\n')
        hook.chmod(0o755)

    def git(self, cwd, *args, check=True):
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
        return subprocess.run(["git", "-C", str(cwd), *args], text=True,
                              capture_output=True, check=check, env=env)

    def write_history(self, path, title):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"noticias": [{"title": title}]}))

    def run_helper(self, operation):
        return subprocess.run([sys.executable, str(SCRIPT), operation,
                               "--data-repo", str(self.data), "--history", str(self.history),
                               "--state", str(self.state)], text=True, capture_output=True)

    def load(self):
        result = self.run_helper("load")
        self.assertEqual(result.returncode, 0, result.stderr)

    def persist(self):
        result = self.run_helper("persist")
        self.assertEqual(result.returncode, 0, result.stderr)

    def advance_remote(self, title=None):
        if title:
            self.write_history(self.seed / "data/historial.json", title)
        else:
            (self.seed / "unrelated.txt").write_text("concurrent metadata\n")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "concurrent")
        self.git(self.seed, "push", "origin", "HEAD:refs/heads/news-data")

    def test_load_reads_git_blob_without_executing_checkout_code_or_hooks(self):
        marker = self.root / "executed"
        (self.data / "sitecustomize.py").write_text(f"open({str(marker)!r}, 'w').write('bad')")
        (self.data / ".git/hooks/post-checkout").write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        (self.data / ".git/hooks/post-checkout").chmod(0o755)
        self.write_history(self.data / "data/historial.json", "uncommitted tampering")
        self.load()
        self.assertEqual(json.loads(self.history.read_text())["noticias"][0]["title"], "initial")
        self.assertFalse(marker.exists())

    def test_persist_pushes_only_history_to_news_data_and_never_main(self):
        self.load()
        self.write_history(self.history, "updated")
        marker = self.root / "pre-push-executed"
        hook = self.data / ".git/hooks/pre-push"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n")
        hook.chmod(0o755)
        (self.data / "code.py").write_text("unrelated dirty code")
        self.git(self.data, "add", "code.py")
        before = self.git(self.remote, "rev-parse", "news-data").stdout.strip()
        self.persist()
        self.assertEqual(self.git(self.remote, "diff", "--name-only", before, "news-data").stdout,
                         "data/historial.json\n")
        self.assertFalse(marker.exists())
        self.assertIn('"updated"', self.git(self.remote, "show", "news-data:data/historial.json").stdout)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, self.main_before)

    def test_unchanged_history_does_not_create_a_commit(self):
        self.load()
        before = self.git(self.remote, "rev-parse", "news-data").stdout
        self.persist()
        self.assertEqual(self.git(self.remote, "rev-parse", "news-data").stdout, before)

    def test_concurrent_history_change_fails_without_overwriting_either_branch(self):
        self.load()
        self.write_history(self.history, "stale generation")
        self.advance_remote("newer generation")
        before = self.git(self.remote, "rev-parse", "news-data").stdout
        result = self.run_helper("persist")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("concurrent", result.stderr.lower())
        self.assertEqual(self.git(self.remote, "rev-parse", "news-data").stdout, before)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, self.main_before)

    def test_concurrent_other_file_is_preserved_by_fast_forward_commit(self):
        self.load()
        self.write_history(self.history, "updated")
        self.advance_remote()
        before = self.git(self.remote, "rev-parse", "news-data").stdout.strip()
        self.persist()
        self.assertEqual(self.git(self.remote, "rev-parse", "news-data^").stdout.strip(), before)
        self.assertEqual(self.git(self.remote, "show", "news-data:unrelated.txt").stdout,
                         "concurrent metadata\n")

    def test_symlink_blob_is_rejected_before_runtime_write(self):
        self.git(self.seed, "rm", "data/historial.json")
        (self.seed / "data").mkdir(exist_ok=True)
        (self.seed / "data/historial.json").symlink_to("../../outside")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "symlink")
        self.git(self.seed, "push", "origin", "HEAD:refs/heads/news-data")
        self.git(self.data, "fetch", "origin", "news-data")
        self.git(self.data, "reset", "--hard", "FETCH_HEAD")
        result = self.run_helper("load")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.history.exists())

    def test_two_simultaneous_writers_cannot_overwrite_each_other(self):
        self.load()
        second = self.root / "second"
        second_state = self.root / "second-state.json"
        second_history = self.root / "second-history.json"
        self.git(self.root, "clone", "--branch", "news-data", str(self.remote), str(second))
        arguments = [sys.executable, str(SCRIPT), "load", "--data-repo", str(second),
                     "--history", str(second_history), "--state", str(second_state)]
        subprocess.run(arguments, capture_output=True, check=True)
        self.write_history(self.history, "writer one")
        self.write_history(second_history, "writer two")
        # Synchronize both real receive-pack processes after their fetch. Git's
        # atomic ref update must reject one; removing non-force semantics loses it.
        barrier = self.remote / "writers"
        barrier.mkdir()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text(
            "#!/usr/bin/env python3\nimport pathlib, sys, time\n"
            f"barrier = pathlib.Path({str(barrier)!r})\n"
            "for line in sys.stdin:\n"
            "    old, new, ref = line.split()\n"
            "    if ref != 'refs/heads/news-data': sys.exit(1)\n"
            "    (barrier / new).touch()\n"
            "deadline = time.monotonic() + 5\n"
            "while len(list(barrier.iterdir())) < 2:\n"
            "    if time.monotonic() > deadline: sys.exit(1)\n"
            "    time.sleep(0.01)\n"
        )
        commands = [
            [sys.executable, str(SCRIPT), "persist", "--data-repo", str(self.data),
             "--history", str(self.history), "--state", str(self.state)],
            [sys.executable, str(SCRIPT), "persist", "--data-repo", str(second),
             "--history", str(second_history), "--state", str(second_state)],
        ]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for command in commands]
        for process in processes:
            process.communicate(timeout=15)
        self.assertEqual(sum(process.returncode == 0 for process in processes), 1)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, self.main_before)
        actual = json.loads(self.git(self.remote, "show", "news-data:data/historial.json").stdout)
        self.assertIn(actual["noticias"][0]["title"], {"writer one", "writer two"})
        self.assertEqual(len(list(barrier.iterdir())), 2)

    def test_rejected_remote_push_fails_closed(self):
        self.load()
        self.write_history(self.history, "updated")
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        before = self.git(self.remote, "rev-parse", "news-data").stdout
        result = self.run_helper("persist")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git(self.remote, "rev-parse", "news-data").stdout, before)

    def test_invalid_json_is_rejected_before_persist(self):
        self.load()
        self.history.write_text('{"noticias": "not a list"}')
        before = self.git(self.remote, "rev-parse", "news-data").stdout
        result = self.run_helper("persist")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git(self.remote, "rev-parse", "news-data").stdout, before)


if __name__ == "__main__":
    unittest.main()
