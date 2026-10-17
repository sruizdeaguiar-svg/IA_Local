"""macOS memory breakdown; cache categories overlap and are not summed."""
import re,subprocess,time,threading
_cache={};_guard=threading.Lock()
def read():
 with _guard:
  if time.monotonic()-_cache.get('_at',-999)<10:return {k:v for k,v in _cache.items() if k!='_at'}
  result={}
  try:
   text=subprocess.check_output(['/usr/bin/vm_stat'],text=True,timeout=3);page=int(re.search(r'page size of (\d+) bytes',text)[1]);values={name.strip():int(n) for name,n in re.findall(r'^([^:\n]+):\s+(\d+)\.',text,re.M)}
   for label,key in [('file_backed_gib','File-backed pages'),('compressed_gib','Pages occupied by compressor'),('purgeable_gib','Pages purgeable')]:result[label]=values.get(key,0)*page/2**30
   p=subprocess.run(['/usr/sbin/sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,timeout=3)
   result['pressure']={1:'Normal',2:'Aviso',4:'Crítica'}.get(int(p.stdout),'Desconocida') if p.returncode==0 else 'No disponible'
  except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):result['pressure']='No disponible'
  _cache.clear();_cache.update(result,_at=time.monotonic());return result
