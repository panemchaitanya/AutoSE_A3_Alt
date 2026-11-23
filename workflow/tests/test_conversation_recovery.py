"""Preparation-role recovery preserves real replies, never a stage pass."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import agent,gemini

class ConversationRecovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  (self.root/'tinydb').mkdir();(self.root/'tinydb/a.py').write_text('value=1')
 def tearDown(self):self.tmp.cleanup()
 def run_role(self,task='fixed task',role='SpecWriter',read_only=False):
  return agent.run_agent(role,'fixed-model','fixed system',task,str(self.root),gemini.Usage(),read_only=read_only)
 def test_resume_keeps_prior_observation_without_repeating_action(self):
  with patch.object(agent.gemini,'generate',side_effect=[json.dumps({'action':'read_file','path':'tinydb/a.py'}),gemini.QuotaExhausted('503')]):
   result,transcript,error=self.run_role()
  self.assertIsNone(result);self.assertIn('503',error)
  saved=self.root/'.autose/artifacts/conversation_specwriter.json'
  self.assertEqual(json.loads(saved.read_text())['next_step'],1)
  def recovered(model,system,contents,usage,**_kw):
   self.assertTrue(any('value=1' in p.get('text','') for c in contents for p in c['parts']))
   return json.dumps({'action':'finish','result':{'summary':'resumed'}})
  with patch.object(agent.gemini,'generate',side_effect=recovered),patch.object(agent,'_tool_read_file',side_effect=AssertionError('must not repeat')):
   result,transcript,error=self.run_role()
  self.assertIsNone(error);self.assertEqual(result['summary'],'resumed');self.assertEqual(len(transcript),2);self.assertFalse(saved.exists())
 def test_changed_task_invalidates_saved_conversation(self):
  with patch.object(agent.gemini,'generate',side_effect=[json.dumps({'action':'read_file','path':'tinydb/a.py'}),gemini.QuotaExhausted('503')]):self.run_role()
  def changed(model,system,contents,usage,**_kw):
   self.assertEqual(contents,[{'role':'user','parts':[{'text':'new task'}]}])
   return json.dumps({'action':'finish','result':{}})
  with patch.object(agent.gemini,'generate',side_effect=changed):self.run_role(task='new task')
 def test_reviewer_never_loads_or_creates_conversation(self):
  with patch.object(agent.gemini,'generate',return_value=json.dumps({'action':'finish','result':{}})):self.run_role(role='Reviewer',read_only=True)
  self.assertFalse((self.root/'.autose/artifacts/conversation_reviewer.json').exists())
 def test_step_cap_survives_restarts(self):
  with patch.object(agent.config,'MAX_AGENT_STEPS',2),patch.object(agent.gemini,'generate',side_effect=[json.dumps({'action':'list_files','path':'tinydb'}),gemini.QuotaExhausted('503')]):self.run_role()
  with patch.object(agent.config,'MAX_AGENT_STEPS',2),patch.object(agent.gemini,'generate',return_value=json.dumps({'action':'list_files','path':'tinydb'})) as model:
   result,transcript,error=self.run_role()
  self.assertIn('step cap',error);self.assertEqual(model.call_count,1)

if __name__=='__main__':unittest.main()
