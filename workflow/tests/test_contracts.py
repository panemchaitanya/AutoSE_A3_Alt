"""Offline regression checks for the agent response contract."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'agent'
sys.path.insert(0, str(ROOT))
import agent
import gemini
import prompts


class Contracts(unittest.TestCase):
    def test_action_specific_required_fields(self):
        branches = gemini.response_schema(prompts.DESIGN_SYSTEM)['anyOf']
        fields = {b['properties']['action']['enum'][0]: b['required']
                  for b in branches}
        self.assertEqual(fields['write_file'], ['action', 'path', 'content'])
        self.assertEqual(fields['run_shell'], ['action', 'command'])
        self.assertEqual(fields['finish'], ['action', 'result'])

    def test_judge_schema_is_not_action_schema(self):
        schema = gemini.response_schema(prompts.JUDGE_SYSTEM)
        self.assertEqual(schema['required'], ['pass', 'reasons'])

    def test_missing_write_content_cannot_truncate_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'spec.md'
            path.write_text('existing contents')
            replies = [json.dumps({'action': 'write_file', 'path': 'spec.md'}),
                       json.dumps({'action': 'finish', 'result': {}})]
            with patch.object(gemini, 'generate', side_effect=replies):
                result, transcript, error = agent.run_agent(
                    'SpecWriter', 'stub', '', '', root, gemini.Usage())
            self.assertIsNone(error)
            self.assertEqual(path.read_text(), 'existing contents')

    def test_protected_direct_write(self):
        with tempfile.TemporaryDirectory() as root:
            out = agent._tool_write_file(root, 'workflow/agent.py', 'bad')
            self.assertIn('ERROR', out)
            self.assertFalse((Path(root) / 'workflow/agent.py').exists())

    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(agent._safe_path(root, '../outside'))


if __name__ == '__main__':
    unittest.main()
