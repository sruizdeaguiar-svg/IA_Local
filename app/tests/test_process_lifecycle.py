"""Real parent/child lifecycle; managed descendants stop, unrelated processes survive."""
import os,sys,tempfile,time,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));_session=tempfile.TemporaryDirectory();os.environ['IA_LOCAL_HOME']=_session.name
import core,psutil
class ProcessLifecycle(unittest.TestCase):
 def test_managed_child_cleanup_preserves_other_process(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'logs').mkdir();pidfile=root/'child.pid';script=root/'fixture.py'
   script.write_text('import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(120)"])\nPath(sys.argv[1]).write_text(str(p.pid))\ntime.sleep(120)\n',encoding='utf-8')
   created=[];real_popen=subprocess.Popen
   def capture(*args,**kwargs):
    process=real_popen(*args,**kwargs);created.append(process);return process
   unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);child=None;parent=None
   try:
    with patch.object(core,'ROOT',root),patch.object(core,'port_open',return_value=False),patch.dict(core.PORTS,{'custom-child-qa':18771}),patch.object(core.subprocess,'Popen',side_effect=capture):
     with core.db() as c:c.execute('CREATE TABLE events (time REAL, kind TEXT, data TEXT)')
     parent=core.spawn('custom-child-qa',[sys.executable,str(script),str(pidfile)])
     until=time.monotonic()+10
     while not pidfile.exists() and time.monotonic()<until:time.sleep(.05)
     child=psutil.Process(int(pidfile.read_text(encoding='utf-8')));core.stop_process('custom-child-qa')
     self.assertFalse(core.same(parent));self.assertFalse(child.is_running() and child.status()!=psutil.STATUS_ZOMBIE);self.assertIsNone(unrelated.poll())
   finally:
    if parent is None:
     parent=core.read(root/'processes.json',{}).get('custom-child-qa')
     if pidfile.exists():
      try:child=psutil.Process(int(pidfile.read_text(encoding='utf-8')))
      except psutil.NoSuchProcess:pass
    unrelated.terminate();unrelated.wait(10)
    for p in [child,psutil.Process(parent['pid']) if parent and psutil.pid_exists(parent['pid']) else None]:
     if p:
      try:p.kill()
      except psutil.NoSuchProcess:pass
    for process in created:
     try:process.wait(10)
     except subprocess.TimeoutExpired:process.kill();process.wait(10)
if __name__=='__main__':unittest.main()
