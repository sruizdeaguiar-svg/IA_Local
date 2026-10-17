"""Read macOS GPU driver counters without root; absent counters stay unknown."""
import subprocess,plistlib,time,threading,sys,shutil
_cache={};_guard=threading.Lock()
def read():
    with _guard:
        if time.monotonic()-_cache.get('_at',-99)<2:return {k:v for k,v in _cache.items() if k!='_at'}
        result={}
        try:
            if sys.platform!='darwin':
                tool=shutil.which('nvidia-smi')
                if tool:
                    rows=subprocess.check_output([tool,'--query-gpu=utilization.gpu,memory.used','--format=csv,noheader,nounits'],text=True,timeout=4).splitlines()
                    values=[[float(v.strip()) for v in line.split(',')] for line in rows]
                    result={'util':max(v[0] for v in values),'mem_used':sum(v[1] for v in values)*2**20,'source':'nvidia-smi; max utilization across GPUs'}
                _cache.clear();_cache.update(result,_at=time.monotonic());return result
            raw=subprocess.check_output(['/usr/sbin/ioreg','-a','-r','-c','IOAccelerator'],timeout=4);nodes=plistlib.loads(raw)
            def stats(items):
                for item in items:
                    if isinstance(item.get('PerformanceStatistics'),dict):yield item['PerformanceStatistics']
                    yield from stats(item.get('IORegistryEntryChildren',[]))
            values=next(stats(nodes),{})
            load=values.get('Device Utilization %')
            if load is None:load=max((values[k] for k in ('Renderer Utilization %','Tiler Utilization %') if isinstance(values.get(k),(int,float))),default=None)
            result={'util':load,'mem_used':values.get('In use system memory') or 0}
        except (OSError,ValueError,subprocess.SubprocessError):pass
        _cache.clear();_cache.update(result,_at=time.monotonic());return result
