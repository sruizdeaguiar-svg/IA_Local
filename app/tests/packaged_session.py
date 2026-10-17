"""CI-only isolated frozen supervisor fixture. Never points at user data."""
from pathlib import Path
import json,os,socket,subprocess,tempfile,time,urllib.request
import psutil
class PackagedSession:
 def __init__(self,folder):self.folder=Path(folder).absolute();self.temp=None
 def __enter__(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'data';self.exe=self.folder/('IA-Local.exe' if os.name=='nt' else 'IA-Local')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
  self.base=f'http://127.0.0.1:{self.port}';self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  try:
   subprocess.run([str(self.exe),'--data',str(self.root),'--port',str(self.port),'--no-browser'],check=True,timeout=90)
   self.token=(self.root/'token').read_text(encoding='utf-8');until=time.monotonic()+30
   while True:
    self.state=self.request('/status')
    if not self.state.get('starting'):break
    if time.monotonic()>until:raise RuntimeError('Frozen state unavailable')
    time.sleep(.2)
   return self
  except Exception:self.__exit__(*__import__('sys').exc_info());raise
 def request(self,path,body=None):
  q=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
  with self.opener.open(q,timeout=30) as response:return json.load(response)
 def __exit__(self,kind,error,tb):
  if error:
   for log in (self.root/'logs').glob('*.log'):print(log.name+': '+log.read_text(encoding='utf-8',errors='replace')[-15000:])
  owned=[]
  for p in psutil.process_iter(['cmdline']):
   try:
    a=p.info['cmdline'] or []
    if '--serve' in a and str(self.root) in a:owned.append(p)
   except psutil.Error:pass
  targets={p.pid:p for parent in owned for p in [parent]+parent.children(recursive=True)}
  for p in reversed(list(targets.values())):
   try:p.terminate()
   except psutil.NoSuchProcess:pass
  _,alive=psutil.wait_procs(list(targets.values()),timeout=10)
  for p in alive:
   try:p.kill();p.wait(10)
   except psutil.NoSuchProcess:pass
  if self.temp:self.temp.cleanup()
