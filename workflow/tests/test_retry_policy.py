"""Offline tests of the patient bounded retry policy (ADR-018).
No API calls, generated issue changes or hidden acceptance tests.
"""
import json,os,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agent'))
import config,gemini

def ok_payload(text='{"action":"finish","result":{}}'):
 return {'candidates':[{'content':{'parts':[{'text':text}]},'finishReason':'STOP'}],
         'usageMetadata':{'promptTokenCount':3,'candidatesTokenCount':1,'totalTokenCount':4}}

class RetryPolicy(unittest.TestCase):
 def setUp(self):
  os.environ['GEMINI_API_KEY']='offline-fixture'
  self.saved=(config.API_RETRIES,list(config.API_BACKOFF_SECONDS))
  config.API_RETRIES=3
  config.API_BACKOFF_SECONDS=[30,60,120]
 def tearDown(self):
  config.API_RETRIES,config.API_BACKOFF_SECONDS=self.saved
 def test_defaults_are_patient_but_bounded(self):
  env={k:v for k,v in os.environ.items() if not k.startswith('API_')}
  out=subprocess.run([sys.executable,'-c',
   'import config;print(config.API_RETRIES, sum(config.API_BACKOFF_SECONDS), max(config.API_BACKOFF_SECONDS))'],
   cwd=str(Path(__file__).resolve().parents[1]/'agent'),env=env,capture_output=True,text=True)
  retries,total,longest=map(int,out.stdout.split())
  self.assertGreaterEqual(retries,3)
  self.assertGreaterEqual(total,180)   # tolerates short spikes, then falls back fast
  self.assertLessEqual(total,900)      # still bounded, not an infinite wait
  self.assertLessEqual(longest,300)
 def test_env_override(self):
  env=dict(os.environ,API_RETRIES='6',API_BACKOFF_SECONDS='5,10')
  out=subprocess.run([sys.executable,'-c',
   'import config;print(config.API_RETRIES, config.API_BACKOFF_SECONDS)'],
   cwd=str(Path(__file__).resolve().parents[1]/'agent'),env=env,capture_output=True,text=True)
  self.assertEqual(out.stdout.strip(),"6 [5, 10]")
 def test_spike_then_success_uses_config_without_fallback(self):
  calls=[]
  def fake_post(model,payload,key):
   calls.append(model)
   if len(calls)<3:raise gemini._Transient('503 spike')
   return ok_payload()
  with patch.object(gemini,'_post',side_effect=fake_post),patch.object(gemini.time,'sleep') as slp:
   text=gemini.generate('gemini-primary-x','system',[],gemini.Usage())
  self.assertIn('finish',text)
  self.assertEqual(calls,['gemini-primary-x']*3)
  self.assertEqual([c.args[0] for c in slp.call_args_list if c.args[0]>5],[30,60])
 def test_exhaustion_falls_back_once_then_raises(self):
  calls=[]
  def fake_post(model,payload,key):
   calls.append(model);raise gemini._Transient('still down')
  with patch.object(gemini,'_post',side_effect=fake_post),patch.object(gemini.time,'sleep'):
   with self.assertRaises(gemini.QuotaExhausted):
    gemini.generate('gemini-primary-x','system',[],gemini.Usage())
  self.assertEqual(calls,['gemini-primary-x']*4+[config.MODEL_FALLBACK]*4)

if __name__=='__main__':
 unittest.main()
