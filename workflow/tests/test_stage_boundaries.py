"""Offline tests of corrected requirements gate and reviewer context.
No API calls, generated issue changes or hidden acceptance tests.
"""
import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import run_stage,controller,config,gemini

class StageBoundaries(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'.autose/artifacts').mkdir(parents=True)
  self.state=controller.init_state(91,'autose/issue-91')
  self.issue={'number':91,'title':'offline fixture','body':'fixture'}
 def tearDown(self):self.temp.cleanup()
 def test_old_pass_does_not_bypass_corrected_requirements(self):
  for st in self.state['stages'].values():st['status']='passed'
  with patch.object(run_stage.prompts,'load_skill',return_value='fixture'),patch.object(run_stage.agent,'run_agent',return_value=(None,[],'provider unavailable')) as model:
   ok=run_stage.stage_requirements(str(self.root),self.state,self.issue)
  self.assertFalse(ok);self.assertEqual(model.call_count,1)
  for name in ['design','implementation','testing','release','review']:self.assertEqual(self.state['stages'][name]['status'],'pending')
 def test_verified_marker_skips_without_model_call(self):
  self.state['stages']['requirements']['status']='passed';self.state['a1_bundle_verified']=True
  with patch.object(run_stage.agent,'run_agent') as model:
   self.assertTrue(run_stage.stage_requirements(str(self.root),self.state,self.issue))
  model.assert_not_called()
 def test_presence_failure_cannot_be_overruled_by_testability_judge(self):
  (self.root/'.autose/artifacts/spec.md').write_text('# Spec\n## Acceptance criteria\n- Given an input, when called, then return1.\n')
  with patch.object(run_stage.prompts,'load_skill',return_value='fixture'),patch.object(run_stage.agent,'run_agent',return_value=({},[],None)),patch.object(run_stage,'judge',return_value=(True,'testability pass')):
   ok=run_stage.stage_requirements(str(self.root),self.state,self.issue)
  self.assertFalse(ok);self.assertFalse(self.state.get('a1_bundle_verified',False))
 def test_semantic_audit_veto_cannot_be_overruled(self):
  (self.root/'.autose/artifacts/spec.md').write_text('# Spec\n## Acceptance criteria\n- Given input, when called, then returns1.\n')
  with patch.object(run_stage.prompts,'load_skill',return_value='fixture'),patch.object(run_stage.agent,'run_agent',return_value=({},[],None)),patch.object(run_stage.a1_checks,'check_a1_bundle',return_value=(True,[],{'SRS':'fixture'})),patch.object(run_stage,'judge',side_effect=[(False,'unsupported readiness'),(True,'testable')]*2):
   ok=run_stage.stage_requirements(str(self.root),self.state,self.issue)
  self.assertFalse(ok);self.assertFalse(self.state.get('a1_bundle_verified',False))
 def test_reviewer_cannot_read_assignment_readme_or_pipeline_artifacts(self):
  (self.root/'README.md').write_text('pipeline reasoning')
  (self.root/'README.rst').write_text('upstream docs')
  (self.root/'tinydb').mkdir();(self.root/'tinydb/table.py').write_text('x=1')
  for d in ['workflow','results','experiment','architecture','.github']:
   (self.root/d).mkdir();(self.root/d/'notes.txt').write_text('excluded')
  def reviewer(*args,**kwargs):
   clean=Path(args[4]);self.assertFalse((clean/'README.md').exists());self.assertTrue((clean/'README.rst').exists());self.assertTrue((clean/'tinydb/table.py').exists())
   for d in ['.autose','workflow','results','experiment','architecture','.github']:self.assertFalse((clean/d).exists())
   self.assertTrue(kwargs['read_only'])
   return {'verdict':'approve','findings':[],'classification':None,'summary':'offline stub'},[],None
  with patch.object(run_stage.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='fixture diff')),patch.object(run_stage.agent,'run_agent',side_effect=reviewer):
   self.assertTrue(run_stage.stage_review(str(self.root),self.state,self.issue,91))

if __name__=='__main__':unittest.main()
