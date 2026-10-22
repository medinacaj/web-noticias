"""Run the real inline application script against a small DOM in Node."""
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Node is required for browser-script behavior tests')
class SearchBehaviorTests(unittest.TestCase):
    def test_search_and_preferences(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', str(root / 'tests/search_behavior.cjs')],
                                cwd=root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
