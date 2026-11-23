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
