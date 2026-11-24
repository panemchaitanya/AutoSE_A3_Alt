import json,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import run_stage,agent,gemini,controller
class TesterResume(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.art=self.root/'.autose/artifacts';self.art.mkdir(parents=True)
  self.state=controller.init_state(4,'autose/issue-4');self.state['usage']={'calls':70,'total_tokens':696769}
  self.progress={'transcript':[{'role':'Tester','step':0,'reply':json.dumps({'action':'list_files','path':'.'})}], 'usage':{'calls':71,'total_tokens':709516,'prompt_tokens':679021,'completion_tokens':26460}}
  self.write('progress_tester.json',self.progress);(self.art/'diff.patch').write_text('old exact diff')
  self.write('transcript_implementation.json',[{'step':39,'reply':json.dumps({'action':'finish','result':{'files_changed':['tinydb/table.py']}})}])
  self.calls=[{'role':'Developer','status':'success','run_id':'r1','ts':'01'}, {'role':'Tester','status':'success','run_id':'r1','ts':'02','task_sha256':run_stage._sha(run_stage.tester_task('spec','old exact diff'))}];self.calls_write()
 def tearDown(self):self.t.cleanup()
 def write(self,name,data):(self.art/name).write_text(json.dumps(data))
 def calls_write(self):(self.art/'calls.jsonl').write_text('\n'.join(json.dumps(c) for c in self.calls))
 def recover(self):
  with patch.object(run_stage.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='source diff')),patch.object(run_stage.checks,'check_build',return_value=(True,'build OK')):
   return run_stage.tester_timeout_recovery(str(self.root),self.state,'spec')
 def test_actual_step_and_usage_retained_not_summed(self):
  p=self.recover();self.assertEqual(len(p['transcript']),1);self.assertEqual(self.state['usage']['calls'],71);self.assertEqual(self.state['stages']['implementation']['status'],'passed');self.assertNotEqual(self.state['stages']['testing']['status'],'passed')
 def test_wrong_task_refuses(self):
  self.calls[-1]['task_sha256']='wrong';self.calls_write()
  with self.assertRaisesRegex(ValueError,'binding'):self.recover()
 def test_no_same_run_transition_refuses(self):
  self.calls[-1]['run_id']='other';self.calls_write()
  with self.assertRaisesRegex(ValueError,'same run'):self.recover()
 def test_exhausted_tester_refuses(self):
  self.progress['transcript']=[{'role':'Tester','step':i,'reply':'{}'} for i in range(40)];self.write('progress_tester.json',self.progress)
  with self.assertRaisesRegex(ValueError,'exhausted'):self.recover()
 def test_missing_developer_finish_refuses(self):
  self.write('transcript_implementation.json',[{'reply':'{}'}])
  with self.assertRaisesRegex(ValueError,'finish'):self.recover()
 def test_tester_loop_continues_step_one_without_replay(self):
  usage=gemini.Usage(self.progress['usage'])
  with patch.object(agent.gemini,'generate',return_value=json.dumps({'action':'finish','result':{'all_pass':True}})) as gen,patch.object(agent,'_tool_list_files',side_effect=AssertionError('no replay')):
   result,transcript,error=agent.run_agent('Tester','model','system','task',str(self.root),usage,resume_progress=self.progress)
  self.assertIsNone(error);self.assertEqual([x['step'] for x in transcript],[0,1]);self.assertEqual(gen.call_count,1)
