"""Verify the workflow's isolated reviewer can load its trusted module closure.

These tests never invoke a provider or inspect generated/hidden issue tests.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ReviewerBootstrap(unittest.TestCase):
    def test_review_workflow_mirror_matches_live_definition(self):
        self.assertEqual(
            (ROOT / '.github/workflows/autose-review.yml').read_text(),
            (ROOT / 'workflow/autose-review.yml').read_text(),
        )

    def test_isolated_trusted_harness_imports_without_repo_pythonpath(self):
        workflow = (ROOT / '.github/workflows/autose-review.yml').read_text()
        match = re.search(r'for FILE in ([^;\n]+); do', workflow)
        self.assertIsNotNone(match, 'trusted reviewer module list is missing')
        modules = match.group(1).split()
        with tempfile.TemporaryDirectory() as clean:
            for module in modules:
                self.assertRegex(module, r'^[a-z0-9_]+\.py$')
                shutil.copy2(ROOT / 'workflow/agent' / module, Path(clean) / module)
            # Isolated interpreter prevents a module in the original checkout,
            # PYTHONPATH, or a user installation from masking a missing import.
            proc = subprocess.run(
                [sys.executable, '-I', str(Path(clean) / 'run_stage.py'), '--help'],
                cwd=clean, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('--stage', proc.stdout)


if __name__ == '__main__':
    unittest.main()
