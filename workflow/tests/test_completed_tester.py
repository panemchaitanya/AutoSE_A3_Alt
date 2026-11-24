import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import run_stage,controller
class CompletedTester(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.art=self.root/'.autose/artifacts';self.art.mkdir(parents=True);(self.root/'tests_autose').mkdir();(self.root/'tests_autose/test_feature.py').write_text('def test_feature():pass')
  self.state=controller.init_state(4,'autose/issue-4');self.state['fix_cycles']=1;self.state['usage']={'calls':88,'total_tokens':830906}
  (self.art/'test_report.md').write_text('Verdict: FAIL full suite failed: test_testing_coverage.py CalledProcessError')
  self.trans=[{'reply':json.dumps({'action':'finish','result':{'tests_written':['tests_autose/test_feature.py'],'all_pass':True}})}];self.write('transcript_testing.json',self.trans);self.write('progress_developer.json',{'transcript':[{'step':i} for i in range(5)]});(self.art/'diff.patch').write_text('diff')
  self.call={'role':'Tester','status':'success','branch_head':'head','task_sha256':run_stage._sha(run_stage.tester_task('spec','diff'))};self.calls()
 def tearDown(self):self.tmp.cleanup()
 def write(self,n,v):(self.art/n).write_text(json.dumps(v))
 def calls(self):(self.art/'calls.jsonl').write_text(json.dumps(self.call))
 def go(self,delta='',tests=True,baseline=True):
  with patch.object(run_stage.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=delta)),patch.object(run_stage.checks,'run_tests',return_value=(tests,'test result','output')),patch.object(run_stage.checks,'baseline_regression_check',return_value=(baseline,'baseline')),patch.object(run_stage.checks,'check_build',return_value=(True,'build')),patch.object(run_stage.agent,'run_agent',side_effect=AssertionError('no provider')):
   return run_stage.recheck_completed_tester(str(self.root),self.state,'spec')
 def test_rechecks_and_preserves_failed_report_usage_cycles(self):
  self.assertTrue(self.go());self.assertEqual(self.state['usage']['total_tokens'],830906);self.assertEqual(self.state['fix_cycles'],1);self.assertEqual(self.state['stages']['testing']['status'],'passed');self.assertEqual(len(list(self.art.glob('completed_tester_recheck_*.json'))),1)
 def test_changed_source_refuses(self):
  with self.assertRaisesRegex(ValueError,'source changed'):self.go(delta='changed source')
 def test_wrong_task_refuses(self):
  self.call['task_sha256']='wrong';self.calls()
  with self.assertRaisesRegex(ValueError,'binding'):self.go()
 def test_full_suite_failure_still_fails(self):self.assertFalse(self.go(tests=False));self.assertEqual(self.state['stages']['testing']['status'],'failed')
 def test_baseline_nonfailure_still_fails(self):self.assertFalse(self.go(baseline=False))
 def test_missing_finish_refuses(self):
  self.write('transcript_testing.json',[{'reply':'{}'}])
  with self.assertRaisesRegex(ValueError,'completed'):self.go()
