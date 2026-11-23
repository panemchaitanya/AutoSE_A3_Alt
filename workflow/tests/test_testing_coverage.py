"""A green subset of tests cannot satisfy an explicitly untested criterion."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
import controller
import run_stage


class TestingCoverage(unittest.TestCase):
    def test_explicit_untested_criterion_blocks_testing_gate(self):
        with tempfile.TemporaryDirectory() as root:
            artifacts = Path(root) / '.autose/artifacts'
            artifacts.mkdir(parents=True)
            for name in ('spec.md', 'design.md', 'diff.patch'):
                (artifacts / name).write_text('offline fixture')
            generated = Path(root) / 'tests_autose'
            generated.mkdir()
            (generated / 'test_fixture.py').write_text('def test_fixture(): pass\n')
            state = controller.init_state(3, 'autose/issue-3')
            state['stages']['implementation']['status'] = 'passed'
            result = {'criteria_untestable': ['AC-2 needs a defined boundary'],
                      'tests_written': ['tests_autose/test_fixture.py'], 'all_pass': True}
            with patch.object(run_stage.agent, 'run_agent', return_value=(result, [], None)), \
                 patch.object(run_stage.checks, 'run_tests', return_value=(True, 'all tests pass', 'green subset')), \
                 patch.object(run_stage.checks, 'baseline_regression_check') as baseline:
                self.assertFalse(run_stage.stage_develop(root, state, {'number': 3}))
            self.assertEqual(state['stages']['testing']['status'], 'failed')
            self.assertEqual(state['stages']['release']['status'], 'pending')
            self.assertIn('AC-2', state['stages']['testing']['reason'])
            report = (artifacts / 'test_report.md').read_text()
            self.assertIn('AC-2', report)
            self.assertIn('Verdict: FAIL', report)
            baseline.assert_not_called()


if __name__ == '__main__':
    unittest.main()
