"""Offline continuation handoff tests, never provider/hidden-test execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
import controller
import review_feedback
import run_stage


class ReviewFeedback(unittest.TestCase):
    def setUp(self):
        self.pr = {'number': 7, 'head': {'ref': 'autose/issue-3',
                   'sha': 'current-head', 'repo': {'full_name': 'owner/fork'}}}
        self.review = {'id': 11, 'user': {'login': 'github-actions[bot]', 'type': 'Bot'},
                       'commit_id': 'current-head', 'state': 'COMMENTED',
                       'body': '# Review of PR #7\n\nVerdict: **request_changes**\n\n'
                               '## Findings\n- `tinydb/table.py`: handle missing values\n',
                       'html_url': 'https://example.invalid/review/11'}

    def collect(self, reviews):
        with patch.object(review_feedback, 'json', wraps=json):
            def api(path):
                return reviews if '/reviews?' in path else [self.pr]
            return review_feedback.collect_review_feedback(api, 'owner/fork', 'autose/issue-3')

    def test_latest_matching_bot_review_is_recovered(self):
        stale = dict(self.review, id=99, commit_id='old-head')
        human = dict(self.review, id=100, user={'login': 'person', 'type': 'User'})
        later = dict(self.review, id=12)
        feedback = self.collect([self.review, stale, human, later])
        self.assertEqual(feedback['review_id'], 12)
        self.assertIn('handle missing values', feedback['body'])

    def test_stale_or_unbound_reviews_fail_closed(self):
        for review in (dict(self.review, commit_id='old-head'),
                       dict(self.review, user={'login': 'someone', 'type': 'User'}),
                       dict(self.review, body='unrelated comment')):
            with self.subTest(review=review), self.assertRaises(ValueError):
                self.collect([review])

    def test_later_approval_cannot_reactivate_an_older_change_request(self):
        approval = dict(self.review, id=12, body='# Review of PR #7\n\nVerdict: **approve**')
        with self.assertRaises(ValueError):
            self.collect([self.review, approval])

    def test_truncated_history_is_not_treated_as_latest(self):
        with self.assertRaises(ValueError):
            self.collect([self.review] * 100)

    def test_other_repository_cannot_supply_feedback(self):
        self.pr['head']['repo']['full_name'] = 'someone/else'
        with self.assertRaises(ValueError):
            self.collect([self.review])

    def test_feedback_reaches_designer_and_developer_tasks(self):
        with tempfile.TemporaryDirectory() as root:
            artifacts = Path(root) / '.autose/artifacts'
            artifacts.mkdir(parents=True)
            (artifacts / 'spec.md').write_text('fixture spec')
            (artifacts / 'design.md').write_text('fixture design')
            (Path(root) / 'ARCHITECTURE.md').write_text('fixture architecture')
            review_feedback.save_feedback(root, self.collect([self.review]))
            issue = {'number': 3, 'title': 'fixture', 'body': ''}
            for stage in ('design', 'develop'):
                with self.subTest(stage=stage):
                    state = controller.init_state(3, 'autose/issue-3')
                    with patch.object(run_stage.agent, 'run_agent',
                                      return_value=(None, [], 'offline stop')) as model:
                        method = run_stage.stage_design if stage == 'design' else run_stage.stage_develop
                        self.assertFalse(method(root, state, issue))
                    self.assertIn('handle missing values', model.call_args.args[3])
                    self.assertIn('https://example.invalid/review/11', model.call_args.args[3])

    def test_no_feedback_is_valid_for_fresh_run(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(review_feedback.task_feedback(root), '')


if __name__ == '__main__':
    unittest.main()
