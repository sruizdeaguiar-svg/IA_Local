"""An external process must not inherit the frozen app's private library paths."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import process_runtime
class Runtime(unittest.TestCase):
 def test_external_child_uses_original_loader_environment(self):
  original={'PATH':os.environ.get('PATH',''),'LD_LIBRARY_PATH':'/private/app-libraries','LD_LIBRARY_PATH_ORIG':'/original/engine-libraries'};env={**os.environ,**original}
  with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS','/private/app-libraries',create=True),patch.object(process_runtime,'external_loader',__import__('contextlib').nullcontext):
   result=process_runtime.run([sys.executable,'-c','import os,json;print(json.dumps({"library":os.environ.get("LD_LIBRARY_PATH")}))'],env=env,capture_output=True,text=True,check=True)
  self.assertEqual(json.loads(result.stdout)['library'],'/original/engine-libraries');self.assertEqual(env['LD_LIBRARY_PATH'],'/private/app-libraries')
if __name__=='__main__':unittest.main()
