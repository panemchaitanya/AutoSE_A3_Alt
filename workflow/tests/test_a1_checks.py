import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import a1_checks
class A1Checks(unittest.TestCase):
 def test_missing_bundle_fails(self):
  with tempfile.TemporaryDirectory() as d:
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertFalse(ok);self.assertEqual(len(errors),25)
 def test_presence_only_fails(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.autose/artifacts';root.mkdir(parents=True)
   for kind in ['SRS','REGISTER','VALIDATION']:(root/f'x_{kind}_v1.md').write_text('placeholder')
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertFalse(ok);self.assertTrue(any('C1' in e for e in errors))
 def test_explicit_check_status_required(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.autose/artifacts';root.mkdir(parents=True)
   (root/'x_VALIDATION_v1.md').write_text('C1 C2 C3 C4 all done. READY.\n'+'some prose '*30)
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertFalse(ok);self.assertTrue(any('C1' in e for e in errors))
 def test_conflicting_slugs_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.autose/artifacts';root.mkdir(parents=True)
   for slug in ['issue2','issue_2']:
    for kind in ['SRS','REGISTER','VALIDATION']:(root/f'{slug}_{kind}_v1.md').write_text('placeholder '*40)
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertFalse(ok);self.assertTrue(any('conflicting slugs' in e for e in errors));self.assertEqual(docs,{})
 def test_numeric_version_selection_v10_over_v9(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.autose/artifacts';root.mkdir(parents=True)
   for kind in ['SRS','REGISTER','VALIDATION']:
    (root/f'x_{kind}_v9.md').write_text('V9 CONTENT '+'placeholder '*40)
    (root/f'x_{kind}_v10.md').write_text('V10 CONTENT '+'placeholder '*40)
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertTrue(all(docs[k].startswith('V10 CONTENT') for k in ['SRS','REGISTER','VALIDATION']))
   self.assertFalse(any('missing for selected bundle' in e for e in errors))
 def test_missing_matching_components_rejected_never_mixed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'.autose/artifacts';root.mkdir(parents=True)
   for kind in ['SRS','REGISTER','VALIDATION']:(root/f'x_{kind}_v1.md').write_text('placeholder '*40)
   (root/'x_SRS_v2.md').write_text('placeholder '*40)
   ok,errors,docs=a1_checks.check_a1_bundle(d)
   self.assertFalse(ok)
   self.assertTrue(any('REGISTER missing for selected bundle x v2' in e for e in errors))
   self.assertTrue(any('VALIDATION missing for selected bundle x v2' in e for e in errors))
   self.assertEqual(docs,{})
 def test_a3_profile_excludes_mcp_only_not_integrity(self):
  import prompts
  profile=prompts.A3_REUSE_PROFILE
  self.assertIn('No MCP invocation is required',profile)
  self.assertIn('does not\nforce CLARIFY',profile)
  self.assertIn('source traceability',profile)
  self.assertIn('labelled assumptions linked to questions',profile)
  self.assertIn('fabricate a tool call',profile)
  self.assertIn('No MCP invocation is required for A3',prompts.SPEC_SYSTEM)
 def test_a3_profile_appended_without_mutating_original_skill(self):
  import prompts
  repo=Path(__file__).resolve().parents[2]
  original=(repo/'workflow/prompts/requirements-ledger-skill.md').read_text()
  effective=prompts.load_skill(str(repo))
  self.assertTrue(effective.startswith(original))
  self.assertTrue(effective.endswith(prompts.A3_REUSE_PROFILE))
  self.assertIn('call the MCP tool',original)
 def test_judge_uses_same_profile(self):
  src=(Path(__file__).resolve().parents[1]/'agent/run_stage.py').read_text()
  self.assertIn('prompts.A3_REUSE_PROFILE +',src)
  self.assertIn('Do not reject solely for absent MCP invocation',src)
