"""CI smoke test of the actual frozen executable, not merely Python sources."""
from pathlib import Path
import json,os,socket,subprocess,sys,tempfile,time,urllib.request
import psutil
folder=Path(sys.argv[1]).absolute();exe=folder/('IA-Local.exe' if os.name=='nt' else 'IA-Local')
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)/'data'
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 child=None
 try:
  subprocess.run([str(exe),'--data',str(root),'--port',str(port),'--no-browser'],check=True,timeout=90)
  child=next(p for p in psutil.process_iter(['cmdline']) if p.info['cmdline'] and '--serve' in p.info['cmdline'] and str(root) in p.info['cmdline'])
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));token=(root/'token').read_text()
  req=urllib.request.Request(f'http://127.0.0.1:{port}/status',headers={'Authorization':'Bearer '+token})
  until=time.monotonic()+30
  while True:
   with opener.open(req,timeout=5) as response:state=json.load(response)
   if not state.get('starting'):break
   if time.monotonic()>until:raise RuntimeError('Frozen supervisor state unavailable')
   time.sleep(.2)
  assert not state['services'] and not state['models'] and not state['lan']['enabled'] and not state['lan']['users']
  assert state['ram_total']>0 and not state['platform']['gpu_limit_supported']
  print('Frozen clean installation, health, state and unsupported Mac controls: passed')
 finally:
  if child:
   child.terminate()
   try:child.wait(10)
   except psutil.TimeoutExpired:child.kill();child.wait(10)
