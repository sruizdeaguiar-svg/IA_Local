"""CI smoke test of the actual frozen executable, not merely Python sources."""
import sys
from packaged_session import PackagedSession
with PackagedSession(sys.argv[1]) as app:
 state=app.state
 assert not state['services'] and not state['models'] and not state['lan']['enabled'] and not state['lan']['users']
 assert state['ram_total']>0 and not state['platform']['gpu_limit_supported']
 # Test late imports/assets after the initial launcher has exited and cleaned up.
 result=app.request('/action',{'action':'scan'})
 import time
 until=time.monotonic()+30
 while True:
  time.sleep(.2);state=app.request('/status');job=next((j for j in state.get('jobs',[]) if j['id']==result['job']),None)
  if job and job['state']!='running':assert job['state']=='done',job;break
  assert time.monotonic()<until,'Late GGUF import/catalogue scan timeout'
 print('Frozen clean profile, health, late GGUF import and platform controls: passed')
