import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import agent,run_stage,gemini,config

def fixture(root,task='original'):
 a=Path(root)/'.autose/artifacts';a.mkdir(parents=True)
 rows=[{'role':'Developer','step':x,'reply':'{"action":"read_file","path":"tinydb/table.py"}'} for x in range(20)]
 p={'transcript':rows,'usage':{'calls':50,'total_tokens':517599}}
 (a/'progress_developer.json').write_text(json.dumps(p))
 (a/'calls.jsonl').write_text(json.dumps({'role':'Developer','task_sha256':run_stage._sha(task)})+'\n')
 return p

def test_preserves_usage_and_steps_without_replay():
 with tempfile.TemporaryDirectory() as d:
  fixture(d);state={'usage':{'calls':30,'total_tokens':378840},'history':[]}
  p=run_stage.developer_progress_resume(d,'original',state)
  assert state['usage']['total_tokens']==517599
  usage=gemini.Usage(state['usage'])
  with patch.object(agent.gemini,'generate',return_value='{"action":"finish","result":{"blocked":true}}') as call,patch.object(agent,'_tool_run_shell') as shell:
   result,transcript,error=agent.run_agent('Developer','m','system','original',d,usage,resume_progress=p)
  assert result['blocked'] and error is None
  assert transcript[-1]['step']==20
  shell.assert_not_called()
  assert any('Remaining steps: 20' in x['parts'][0]['text'] for x in call.call_args[0][2])

def test_mismatch_refuses_before_usage_change():
 with tempfile.TemporaryDirectory() as d:
  fixture(d);state={'usage':{'total_tokens':1},'history':[]}
  try:run_stage.developer_progress_resume(d,'changed',state);assert False
  except ValueError:pass
  assert state['usage']['total_tokens']==1

def test_exhausted_prefix_never_gets_new_budget():
 with tempfile.TemporaryDirectory() as d:
  p=fixture(d);p['transcript']*=2
  for i,row in enumerate(p['transcript']):p['transcript'][i]={'role':'Developer','step':i,'reply':'x'}
  (Path(d)/'.autose/artifacts/progress_developer.json').write_text(json.dumps(p))
  try:run_stage.developer_progress_resume(d,'original',{'usage':{},'history':[]});assert False
  except ValueError as e:assert 'exhausted' in str(e)
