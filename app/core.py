'Core lifecycle and inventory. Models stay in their original locations. Process identities, unique ports and a profile-scoped lock protect lifecycle operations; individual engine branches implement only verified native APIs.'
from pathlib import Path
import contextlib, datetime, hashlib, json, os, plistlib, re, secrets, signal, socket, sqlite3, subprocess, sys, threading, time, urllib.request, urllib.error
import psutil,platform,shutil
try:import fcntl
except ImportError:fcntl=None

HOME=Path.home()
DEFAULT_ROOT=HOME/'Library/Application Support/IA-Local' if sys.platform=='darwin' else Path(os.environ.get('LOCALAPPDATA',HOME/'AppData/Local'))/'IA-Local' if os.name=='nt' else Path(os.environ.get('XDG_DATA_HOME',HOME/'.local/share'))/'IA-Local'
ROOT=Path(os.environ.get('IA_LOCAL_HOME',DEFAULT_ROOT))
STRATA=HOME/'Library/Application Support/Strata-Mac'
LROOT=Path('/Volumes/Seguridad/Llama')
LLAMA=LROOT/'optimizacion-m4-pro/bin/llama-server'
OLD=HOME/'.local/share/mlx-server'
PYTHON=Path(os.environ.get('IA_LOCAL_PYTHON',sys.executable))
CONTROL_PORT=int(os.environ.get('IA_LOCAL_PORT','8040'))
DOMAIN='gui/'+str(getattr(os,'getuid',lambda:0)())
PORTS={'strata':8080,'llama':8082,'mirai':8000,'fm':8767,'omlx':8010,'lmstudio':1234,'mlx':8083,'unsloth':8084,'exo':52415,'vllm':8042,'strata-llama':8085,'opencode':8041,'hermes':8643,'freellmapi':8043}
AUX_PORTS={'mirai-backend':8001,'supervisor':CONTROL_PORT,'hermes-gateway':8642,**{'https-'+str(p):p for p in range(8440,8448)}}
NAMES={'strata':'Strata Metal','llama':'Llama M4 Pro','mirai':'Mirai Uzu','fm':'Apple Foundation Models','omlx':'oMLX','lmstudio':'LM Studio','mlx':'MLX-LM','unsloth':'Unsloth Studio','exo':'EXO','vllm':'vLLM Metal','strata-llama':'Strata · llama Metal','opencode':'OpenCode','hermes':'Hermes','freellmapi':'FreeLLMAPI · nube'}

try:
    _saved=json.loads((ROOT/'settings.json').read_text(encoding='utf-8')).get('opencode_port')
    if isinstance(_saved,int) and 1024<=_saved<=65535:PORTS['opencode']=_saved
except (OSError,ValueError):pass

def own_process(p):
    return p.uids().real==os.getuid() if hasattr(os,'getuid') else p.username().casefold()==psutil.Process().username().casefold()

def executable_path(name):
    known=HOME/('.opencode/bin/opencode' if name=='opencode' else '.local/bin/hermes')
    return known if known.exists() else Path(shutil.which(name) or known)

def validate_ports(ports=None):
    assigned={}
    for service,port in {**AUX_PORTS,**(PORTS if ports is None else ports)}.items():
        if isinstance(port,bool) or not isinstance(port,int) or not 1024<=port<=65535:raise RuntimeError('Puerto no válido para '+service+'.')
        if port in assigned:raise RuntimeError('Puerto '+str(port)+' duplicado entre '+assigned[port]+' y '+service+'. Se cancela el arranque.')
        assigned[port]=service
    return assigned

def listener_pids(port):
    if sys.platform!='darwin':
        try:return {c.pid for c in psutil.net_connections('tcp') if c.status=='LISTEN' and c.laddr.port==port and c.pid}
        except psutil.Error:raise RuntimeError('No se pudo identificar el oyente del puerto '+str(port)+'.') from None
    p=subprocess.run(['/usr/sbin/lsof','-nP','-iTCP:'+str(port),'-sTCP:LISTEN','-Fp'],capture_output=True,text=True,timeout=5)
    if p.returncode not in (0,1):raise RuntimeError('No se pudo identificar el oyente del puerto '+str(port)+'.')
    return {int(line[1:]) for line in p.stdout.splitlines() if line.startswith('p') and line[1:].isdigit()}

def expected_listener(service,pid):
    known=find(service)
    if known and known['pid']==pid:return True
    try:
        p=psutil.Process(pid)
        if not own_process(p):return False
        args=p.cmdline();exe=p.exe()
        if service=='mirai':return str(HOME/'.local/share/mirai-local/mirai_router.py') in args
        if service=='mirai-backend':return Path(exe).resolve()==Path('/usr/local/bin/mirai').resolve() and 'server' in args
        if service=='lmstudio':return (exe.startswith(str(HOME/'.lmstudio')+os.sep) and Path(exe).name=='llmster') or exe=='/Applications/LM Studio.app/Contents/MacOS/LM Studio'
        if service=='strata':return exe.startswith(str(STRATA/'.venv')+os.sep) and 'serve.server' in args
    except (psutil.Error,OSError):pass
    return False

def check_service_ports(service):
    validate_ports()
    for key,port in [(service,PORTS[service])]+([('mirai-backend',AUX_PORTS['mirai-backend'])] if service=='mirai' else []):
        if port_open(port):
            pids=listener_pids(port)
            if not pids or not all(expected_listener(key,pid) for pid in pids):
                raise RuntimeError('El puerto '+str(port)+' de '+NAMES.get(service,service)+' está ocupado por otro proceso. Se conserva; no se arranca ni se reutiliza ese oyente.')
        else:
            with socket.socket() as sock:
                sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                try:sock.bind(('127.0.0.1',port))
                except OSError as e:raise RuntimeError('El puerto '+str(port)+' no está disponible para '+NAMES.get(service,service)+'.') from e

def init():
    ROOT.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':
        from portable_security import secure_directory
        secure_directory(ROOT)
    else:os.chmod(ROOT,0o700)
    for x in ('logs','results','backups','updates','omlx-models','router-models','model-links'): (ROOT/x).mkdir(exist_ok=True)
    if not (ROOT/'token').exists():
        fd=os.open(ROOT/'token',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(40))
    if read(ROOT/'installation.json',{}).get('clean') and not (ROOT/'catalog.json').exists():write(ROOT/'catalog.json',{'time':time.time(),'models':[],'errors':[]})
    import integrations,remote_servers,external_providers
    integrations.install_registry();remote_servers.install_registry();external_providers.install_registry()
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS events (time REAL, kind TEXT, data TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, time REAL, model TEXT, status TEXT, data TEXT)')

@contextlib.contextmanager
def db():
    c=sqlite3.connect(ROOT/'history.sqlite',timeout=10);c.execute('PRAGMA journal_mode=WAL')
    try:
        with c:yield c
    finally:c.close()
def event(kind,data):
    with db() as c:c.execute('INSERT INTO events VALUES(?,?,?)',(time.time(),kind,json.dumps(data,ensure_ascii=False)))
def read(p,default=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
def write(p,d):
    p=Path(p);temp=p.with_name(p.name+'.'+secrets.token_hex(4)+'.tmp');temp.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8');os.chmod(temp,0o600);temp.replace(p)
def run(args,timeout=60,env=None):
    if env is None:env={**os.environ,'PATH':os.pathsep.join([str(HOME/'.opencode/bin'),str(HOME/'.local/bin'),'/opt/homebrew/bin','/usr/local/bin',os.environ.get('PATH','/usr/bin:/bin:/usr/sbin:/sbin')])}
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout,env=env)
    if p.returncode:raise RuntimeError('El comando de '+Path(str(args[0])).name+' no terminó correctamente (código '+str(p.returncode)+').')
    return p.stdout.strip()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
def http(base,path,body=None,timeout=2,headers=None,text=False):
    h={'Content-Type':'application/json',**(headers or {})}
    req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=h)
    with OPENER.open(req,timeout=timeout) as r:
        b=r.read().decode();return b if text else json.loads(b)
def probe(s,path='/v1/models'):
    if s.startswith('cloud-'):
        import external_providers
        d=external_providers.definition(s)
        return {'data':[{'id':m} for m in d['models']]} if s in external_providers.SERVERS and d else None
    if s.startswith('custom-'):
        import integrations
        return integrations.probe_custom(s)
    if s.startswith('remote-'):
        import remote_servers
        try:return remote_servers.request(s,'/models') if remote_servers.connected(s) else None
        except Exception:return None
    if s=='opencode':
        try:
            d=json.loads(run([HOME/'.opencode/bin/opencode','api','server.info'],5));return {'ready':True,'version':d.get('version'),'data':[]}
        except Exception:return None
    try:return http('http://127.0.0.1:'+str(PORTS[s]),path)
    except (OSError,ValueError):return None
def port_open(port):
    with socket.socket() as s:s.settimeout(.15);return s.connect_ex(('127.0.0.1',port))==0
def registered(label):return sys.platform=='darwin' and subprocess.run(['launchctl','print',DOMAIN+'/'+label],capture_output=True).returncode==0
def identity(pid):
    try:
        p=psutil.Process(pid)
        if not own_process(p):return None
        return {'pid':pid,'exe':p.exe(),'birth':p.create_time(),'argv_hash':hashlib.sha256(json.dumps(p.cmdline()).encode()).hexdigest()}
    except (psutil.Error,OSError):return None
def same(d):return bool(d) and identity(d['pid'])=={k:d[k] for k in ('pid','exe','birth','argv_hash')}
def ledger():return read(ROOT/'processes.json',{})
def set_process(key,d):
    with lock('ledger'):
        a=ledger()
        if d:a[key]=d
        else:a.pop(key,None)
        write(ROOT/'processes.json',a)
_file_guards={};_file_guard=threading.Lock()
@contextlib.contextmanager
def lock(name='lifecycle'):
    with _file_guard:guard=_file_guards.setdefault(name,threading.RLock())
    with guard,(ROOT/(name+'.lock')).open('a+b') as f:
        if fcntl:fcntl.flock(f,fcntl.LOCK_EX)
        else:
            import msvcrt
            if f.tell()==0:f.write(b'0');f.flush()
            began=time.monotonic()
            while True:
                try:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:
                    if time.monotonic()-began>300:raise RuntimeError('Coordinación ocupada; espera a que termine la consulta actual.')
                    time.sleep(.1)
        try:yield
        finally:
            if fcntl:fcntl.flock(f,fcntl.LOCK_UN)
            else:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def find(s):
    known=ledger().get(s)
    if same(known):return known
    if known and known.get('managed'):
        now=identity(known['pid'])
        if now and now['birth']==known['birth']:
            # Shell entry points exec into their installed Python runtime, preserving PID/birth.
            permitted=(s=='omlx' and now['exe'].startswith('/Applications/oMLX.app/')) or (s=='hermes' and now['exe'].startswith(str(HOME/'.hermes/'))) or (s=='vllm' and now['exe'].startswith('/opt/homebrew/')) or (s=='unsloth' and now['exe'].startswith(str(HOME/'.unsloth/')))
            if permitted:
                now['managed']=True;set_process(s,now);return now
    exact={'llama':str(LLAMA),'fm':'/usr/bin/fm'}
    for p in psutil.process_iter(['exe','cmdline']):
        try:
            a=p.info['cmdline'] or [];exe=p.info['exe'] or ''
            ok=(s in exact and exe==exact[s] and (s!='fm' or 'serve' in a))
            if s=='opencode':ok=exe==str(HOME/'.opencode/bin/opencode') and ('serve' in a or 'service' in a)
            if s=='omlx':ok=exe=='/Applications/oMLX.app/Contents/Resources/Python/cpython-3.11/bin/python3.11' and a and a[0]=='omlx-server'
            if s=='hermes':ok='hermes_cli.main' in ' '.join(a) and any(x in a for x in ('serve','dashboard')) and exe.startswith(str(HOME/'.hermes'))
            if ok:
                if not own_process(p):continue
                listeners=[c for child in [p]+p.children(recursive=True) for c in child.net_connections('tcp') if c.status=='LISTEN']
                if any(c.laddr.port==PORTS.get(s) for c in listeners):return identity(p.pid)
        except psutil.Error:pass
    return None
def spawn(s,args,env=None):
    validate_ports()
    if port_open(PORTS[s]):raise RuntimeError('El puerto '+str(PORTS[s])+' está ocupado; no se toma control de un proceso desconocido.')
    e={**os.environ,'PATH':os.pathsep.join([str(HOME/'.opencode/bin'),str(HOME/'.local/bin'),'/opt/homebrew/bin','/usr/local/bin',os.environ.get('PATH','/usr/bin:/bin:/usr/sbin:/sbin')]),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','NO_PROXY':'127.0.0.1,localhost','TOKENIZERS_PARALLELISM':'false',**(env or {})}
    with (ROOT/'logs'/(s+'.log')).open('ab') as f:
        p=subprocess.Popen([str(x) for x in args],stdout=f,stderr=f,stdin=subprocess.DEVNULL,cwd=ROOT,env=e,start_new_session=os.name!='nt',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
    d=identity(p.pid)
    if not d:raise RuntimeError('El proceso no pudo arrancar.')
    d['managed']=True;set_process(s,d);event('start',{'service':s,'pid':p.pid});return d
def stop_process(s):
    d=find(s)
    if not d:
        if port_open(PORTS[s]):raise RuntimeError('El oyente no se ha identificado; se conserva.')
        return
    # Capture full identities before terminating the parent. Windows has no
    # POSIX process group; terminate only descendants of this managed identity.
    children=[]
    if d.get('managed') and same(d):
        try:children=[row for child in psutil.Process(d['pid']).children(recursive=True) if (row:=identity(child.pid))]
        except psutil.Error:pass
    targets=list(reversed(children))+[d]
    for row in targets:
        if same(row):
            try:psutil.Process(row['pid']).terminate()
            except psutil.NoSuchProcess:pass
    until=time.monotonic()+20
    while any(same(row) for row in targets) and time.monotonic()<until:time.sleep(.1)
    if d.get('managed'):
        for row in targets:
            if same(row):
                try:psutil.Process(row['pid']).kill();event('forced-owned-stop',{'service':s,'pid':row['pid']})
                except psutil.NoSuchProcess:pass
        until=time.monotonic()+5
        while any(same(row) for row in targets) and time.monotonic()<until:time.sleep(.1)
    if any(same(row) for row in targets):raise RuntimeError('Un proceso identificado sigue terminando; se conserva su registro.')
    set_process(s,None)
def wait(s,path='/v1/models',timeout=60):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if probe(s,path) is not None:return
        d=ledger().get(s)
        if d and identity(d['pid']) is None and not port_open(PORTS[s]):raise RuntimeError(NAMES[s]+' terminó durante el arranque. Consulta su registro.')
        time.sleep(.3)
    raise RuntimeError(NAMES[s]+' no confirmó disponibilidad. Consulta su registro.')

def discover():
    sys.path.insert(0,str(STRATA/'third_party/llama.cpp/gguf-py'))
    from gguf import GGUFReader
    cfg=read(ROOT/'settings.json',{});roots=[Path(p) for p in cfg['model_dirs']] if 'model_dirs' in cfg else ([] if read(ROOT/'installation.json',{}).get('clean') else [Path('/Volumes/Seguridad/models'),LROOT,STRATA/'Strata-data/models',HOME/'.lmstudio/models'])
    out={};inodes=set();errors=[]
    skip={'llama.cpp','src','bin','build','build-metal','build-release','node_modules','.git','.venv','evidencia','evidence'}
    for root in roots:
        if not root.exists():continue
        for parent,dirs,files in os.walk(root):
            dirs[:]=[x for x in dirs if x not in skip and not x.startswith('.')]
            for name in files:
                if not name.endswith('.gguf') or name.startswith(('._','mmproj','mtp-','dflash')):continue
                p=Path(parent)/name;st=p.stat();inode=(st.st_dev,st.st_ino)
                if inode in inodes:continue
                split=re.match(r'(.+)-(\d{5})-of-(\d{5})\.gguf$',name)
                parts=[p]
                if split:
                    pre,num,total=split.groups()
                    if num!='00001':continue
                    parts=[p.with_name(f'{pre}-{i:05d}-of-{int(total):05d}.gguf') for i in range(1,int(total)+1)]
                    if not all(x.is_file() for x in parts):errors.append({'path':str(p),'error':'Faltan partes GGUF'});continue
                try:
                    size=sum(x.stat().st_size for x in parts)
                    if size>30*2**30:continue
                    r=GGUFReader(str(p));arch=r.fields['general.architecture'].contents();label=r.fields.get('general.name');label=label.contents() if label else p.stem
                    native_context=r.fields.get(str(arch)+'.context_length');native_context=int(native_context.contents()) if native_context else 8192
                    size=sum(x.stat().st_size for x in parts);mid='gguf-'+hashlib.sha256(str(p.resolve()).encode()).hexdigest()[:12]
                    if size>30*2**30:continue # Flash-Next is managed by its dedicated streaming engine.
                    inodes.add(inode);out[mid]={'id':mid,'label':name.removesuffix('.gguf'),'name':label,'format':'GGUF','path':str(p),'bytes':size,'architecture':arch,'max_context':native_context,'context':4096 if '27B' in name else 8192,'engines':['llama','strata-llama','unsloth'],'load_keys':{'unsloth':str(p)},'status':'Completo; carga por verificar'}
                except Exception:errors.append({'path':str(p),'error':'Cabecera GGUF no válida'})
    sys.path.insert(0,str(HOME/'.local/share/mirai-local'))
    try:
        import mirai_router
        mirai_catalog=mirai_router.catalog()
    except ImportError:mirai_catalog={}
    for mid,m in mirai_catalog.items():out['mirai/'+mid]={'id':'mirai/'+mid,'native_id':mid,'label':m['name'],'name':m['name'],'path':m['path'],'format':'Mirai','bytes':m['weights_bytes'],'context':min(65536,m.get('context_length') or 65536),'engines':['mirai'],'status':'Completo'}
    sys.path.insert(0,str(OLD))
    try:
        from local_providers import ProviderManager
        pm=ProviderManager(state_dir=ROOT/'provider-state')
    except ImportError:pm=None
    for provider in ('mlx','omlx','lmstudio','unsloth'):
        try:
            for m in pm.discover(provider) if pm else []:
                p=Path(m.get('path',''))
                if p.name.startswith(('mmproj','mtp-','dflash')) or 'mmproj' in p.name.lower():continue
                if p.is_dir() and (p/'adapter_config.json').exists() and not (p/'model.safetensors').exists() and not list(p.glob('model-*.safetensors')):continue
                cfg=read(p/'config.json',{}) if p.is_dir() else {}
                fmt='GGUF' if p.suffix=='.gguf' else 'MLX' if cfg.get('quantization') or cfg.get('quantization_config',{}).get('quant_method')=='mlx' else 'Safetensors'
                mid='local-'+hashlib.sha256(str(p.resolve()).encode()).hexdigest()[:12]
                # Merge backend load keys into an existing physical model entry.
                found=next((x for x in out.values() if x.get('path') and Path(x['path']).resolve()==p.resolve()),None)
                if found is None and fmt=='GGUF':continue
                if found is None:
                    size=sum(x.stat().st_size for x in p.glob('*.safetensors')) if p.is_dir() else p.stat().st_size
                    found={'id':mid,'label':m.get('label',p.name),'path':str(p.resolve()),'format':fmt,'bytes':size,'context':4096,'engines':[],'status':'Completo; carga por verificar'};out[mid]=found
                if provider not in found['engines']:found['engines'].append(provider)
                found.setdefault('load_keys',{})[provider]=m['id']
                native_context=cfg.get('max_position_embeddings') or cfg.get('text_config',{}).get('max_position_embeddings')
                if native_context:found['max_context']=int(native_context)
        except Exception:errors.append({'engine':provider,'error':'No se pudo completar el inventario de este motor'})
    # Complete local HF/MLX directories shared directly, without copying weights.
    for base in roots if read(ROOT/'installation.json',{}).get('clean') else (Path('/Volumes/Seguridad/models'),HOME/'.cache/huggingface/hub'):
        if not base.exists():continue
        for parent,dirs,files in os.walk(base):
            dirs[:]=[d for d in dirs if d not in skip and d not in ('blobs','.locks')]
            if 'config.json' not in files or 'adapter_config.json' in files:continue
            path=Path(parent);cfg=read(path/'config.json',{});weights=[p for p in path.glob('*.safetensors') if not p.name.startswith('._')]
            index=read(path/'model.safetensors.index.json',{})
            if not weights or not (path/'tokenizer.json').exists() or (index and not all((path/x).is_file() for x in set(index.get('weight_map',{}).values()))):continue
            modeltype=cfg.get('model_type','');mid='local-'+hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12]
            row=next((x for x in out.values() if x.get('path')==str(path.resolve())),None)
            if row is None:
                row={'id':mid,'label':path.parent.parent.name.removeprefix('models--').replace('--','/') if path.parent.name=='snapshots' else path.name,'format':'MLX' if cfg.get('quantization') else 'Safetensors','path':str(path.resolve()),'bytes':sum(x.stat().st_size for x in weights),'context':4096,'engines':[],'status':'Completo; carga por verificar'};out[mid]=row
            row['architecture']=modeltype;row['max_context']=int(cfg.get('max_position_embeddings') or cfg.get('text_config',{}).get('max_position_embeddings') or 4096)
            if modeltype in ('qwen2','qwen3','qwen3_moe','qwen3_5','qwen3_5_moe','qwen3_8','llama','mistral','gemma3','gemma4','qwen3_next') and Path('/opt/homebrew/bin/vllm').exists() and 'vllm' not in row['engines']:row['engines'].append('vllm')
    # VLM loaders cannot reconstruct a missing vision configuration from text-only metadata.
    for row in out.values():
        path=Path(row.get('path','/nonexistent'));cfg=read(path/'config.json',{}) if path.is_dir() else {}
        if any('ConditionalGeneration' in a for a in cfg.get('architectures',[])) and not cfg.get('vision_config'):
            row['engines']=[e for e in row['engines'] if e not in ('vllm','unsloth')]
            row['compatibility_note']='vLLM/Unsloth: falta vision_config para este loader. MLX/omlx pueden usar el texto.'
    if (ROOT/'exo-runtime/bin/python').exists():
        for row in out.values():
            path=Path(row.get('path','/nonexistent'));cfg=read(path/'config.json',{}) if path.is_dir() else {}
            if cfg.get('model_type') in ('qwen2','qwen3','qwen3_moe') and row.get('format') in ('MLX','Safetensors') and 'exo' not in row['engines']:row['engines'].append('exo')
    import integrations
    out={m['id']:m for m in integrations.attach_models(list(out.values())) if m['engines']}
    out['fm/system']={'id':'fm/system','native_id':'system','label':'Apple Foundation Models','format':'Sistema','bytes':0,'context':4096,'engines':['fm'],'status':'Sistema'}
    out['strata/flash-next']={'id':'strata/flash-next','label':'Flash-Next 125B Q2_0','format':'Strata','bytes':66423878624,'context':8192,'engines':['strata'],'status':'Expertos desde SSD'}
    contexts=read(ROOT/'contexts.json',{})
    for row in out.values():
        override=contexts.get(row['id'])
        if override and override<=row.get('max_context',row['context']):row['context']=override
    out={m['id']:m for m in integrations.attach_models(list(out.values()))}
    if read(ROOT/'installation.json',{}).get('clean'):
        allowed=available_services()
        for m in out.values():m['engines']=[e for e in m['engines'] if e in allowed]
        out={k:m for k,m in out.items() if m['engines']}
    rows=sorted(out.values(),key=lambda x:(x['format'],x['label']))
    write(ROOT/'catalog.json',{'time':time.time(),'models':rows,'errors':errors})
    save_presets(rows)
    return {'count':len(rows),'errors':errors}

def fingerprint(m):
    p=Path(m.get('path','/nonexistent'))
    paths=[p] if p.is_file() else sorted(p.glob('*.safetensors'))+sorted(p.glob('config.json'))
    return hashlib.sha256(json.dumps([(str(x),x.stat().st_size,x.stat().st_mtime_ns) for x in paths]).encode()).hexdigest()

def engine_signature(engine):
    paths={'llama':LLAMA,'strata-llama':STRATA/'engines/llama-b11707/llama-server','vllm':Path('/opt/homebrew/bin/vllm'),'mirai':Path('/usr/local/bin/mirai')}
    p=paths.get(engine)
    if not p or not p.exists():return None
    st=p.resolve().stat();return hashlib.sha256((str(p.resolve())+str(st.st_size)+str(st.st_mtime_ns)).encode()).hexdigest()

def profile_for(m,engine):
    p=read(ROOT/'profiles.json',{}).get(engine+'/'+m['id'],{})
    return p if p.get('fingerprint')==fingerprint(m) and p.get('context')==m['context'] and p.get('engine_signature')==engine_signature(engine) else {}

def save_presets(rows=None,engine='llama'):
    rows=models() if rows is None else rows
    profiles=read(ROOT/'profiles.json',{})
    presets=['version = 1','[*]','n-gpu-layers = 99','threads = 4','threads-batch = 4','batch-size = 512','ubatch-size = 128','parallel = 1','flash-attn = on','cache-ram = 256','reasoning = off','reasoning-budget = 0','offline = true','load-on-startup = false','']
    for m in rows:
        if 'llama' in m['engines']:
            profile=profile_for(m,engine)
            presets += ['['+m['id']+']','model = '+m['path'],'c = '+str(m['context']),'threads = '+str(profile.get('threads',4)),'threads-batch = '+str(profile.get('threads',4)),'batch-size = '+str(profile.get('batch',512)),'ubatch-size = '+str(profile.get('ubatch',128)),'load-on-startup = false','']
    (ROOT/('models-strata.ini' if engine=='strata-llama' else 'models.ini')).write_text('\n'.join(presets),encoding='utf-8')
def gguf_link(m):
    target=ROOT/'model-links'/(m['id']+'.gguf');target.parent.mkdir(exist_ok=True)
    if target.is_symlink():
        if target.resolve()!=Path(m['path']).resolve():target.unlink()
    elif target.exists():raise RuntimeError('Existe un archivo ajeno en el enlace del modelo.')
    if not target.exists():target.symlink_to(Path(m['path']).resolve())
    return str(target)

def models():
    import integrations,remote_servers,external_providers
    return integrations.attach_models(read(ROOT/'catalog.json',{}).get('models',[]))+remote_servers.models_remote()+external_providers.models_cloud()

def api_base(engine):
    if engine.startswith('remote-'):
        import remote_servers
        return remote_servers.api_base(engine).removesuffix('/v1')
    return 'http://127.0.0.1:'+str(PORTS[engine])
def get_model(mid):
    m=next((x for x in models() if x['id']==mid),None)
    if not m:raise ValueError('Modelo no encontrado en el catálogo.')
    if m.get('path') and not Path(m['path']).exists():raise ValueError('El disco del modelo no está disponible.')
    return m

def start(s):
    if s.startswith('cloud-'):
        import external_providers
        return external_providers.connect(s)
    if s.startswith('remote-'):
        import remote_servers
        return remote_servers.connect(s)
    if s not in PORTS:raise ValueError('Servicio desconocido.')
    check_service_ports(s)
    if s.startswith('custom-'):
        import integrations
        return integrations.launch(s)
    if s=='freellmapi':
        if same(ledger().get(s)) and port_open(PORTS[s]):return
        secret=ROOT/'freellmapi-env.json'
        if not secret.exists():write(secret,{'ENCRYPTION_KEY':secrets.token_hex(32)})
        env={**read(secret,{}),'HOST':'127.0.0.1','PORT':str(PORTS[s]),'FREEAPI_DESKTOP':'1','NODE_ENV':'production','FREEAPI_DB_PATH':str(ROOT/'freellmapi-data.sqlite'),'CLIENT_DIST':str(ROOT/'freellmapi/client/dist'),'FREEAPI_ENV_PATH':str(ROOT/'nonexistent.env')}
        spawn(s,[ROOT/'runtime/bin/node',ROOT/'freellmapi/server/dist/index.js'],env)
        wait(s,'/api/auth/status',90);return
    if s in ('strata','strata-llama','vllm'):
        cfg=read(ROOT/'settings.json',{});cfg.setdefault('waiting',[])
        if s not in cfg['waiting']:cfg['waiting'].append(s)
        write(ROOT/'settings.json',cfg);return
    if s=='strata-original-unused':
        if not registered('local.strata.metal'):
            run([PYTHON,STRATA/'manager-control.py','start','strata'],120)
        return
    if s=='mirai':
        if not registered('com.local.mirai-api'):run(['launchctl','bootstrap',DOMAIN,HOME/'Library/LaunchAgents/com.local.mirai-api.plist'])
        wait(s);return
    if s=='llama':
        save_presets();signature=hashlib.sha256((ROOT/'models.ini').read_bytes()).hexdigest();loaded=read(ROOT/'router-configs.json',{})
        if find(s) and probe(s) and loaded.get(s)==signature:return
        if find(s):stop_process(s)
        spawn(s,[LLAMA,'--models-dir',ROOT/'router-models','--models-preset',ROOT/'models.ini','--models-max','1','--host','127.0.0.1','--port',str(PORTS[s]),'--metrics','--slots','--offline'],{'GGML_METAL_NO_RESIDENCY':'1'})
        wait(s);loaded[s]=signature;write(ROOT/'router-configs.json',loaded);return
    elif s=='fm':
        if find(s) and probe(s):return
        spawn(s,['/usr/bin/fm','serve','--host','127.0.0.1','--port',str(PORTS[s])])
    elif s=='omlx':
        if find(s) and port_open(PORTS[s]):return
        for m in models():
            if 'omlx' in m['engines']:
                target=ROOT/'omlx-models'/m['id']
                if not target.exists():target.symlink_to(m['path'],target_is_directory=True)
        spawn(s,[HOME/'.omlx/bin/omlx','serve','--host','127.0.0.1','--port',str(PORTS[s]),'--model-dir',ROOT/'omlx-models','--base-path',ROOT/'omlx-data','--no-hf-cache','--initial-cache-blocks','32','--memory-guard','safe','--max-concurrent-requests','1','--log-level','warning'])
    elif s=='lmstudio':
        run([HOME/'.lmstudio/bin/lms','server','start','--bind','127.0.0.1','--port',str(PORTS[s])],90)
    elif s=='opencode':
        if same(ledger().get(s)) and not port_open(PORTS[s]):stop_process(s)
        run([HOME/'.opencode/bin/opencode','service','start'],90)
        url=run([HOME/'.opencode/bin/opencode','service','status'],30).strip()
        from urllib.parse import urlsplit
        u=urlsplit(url)
        if u.hostname not in ('127.0.0.1','localhost') or not u.port:raise RuntimeError('OpenCode no confirmó una dirección local.')
        validate_ports({**PORTS,s:u.port})
        PORTS[s]=u.port;cfg=read(ROOT/'settings.json',{});cfg['opencode_port']=u.port;write(ROOT/'settings.json',cfg)
        wait(s,'/api/info',60);return
    elif s=='hermes':
        if probe(s,'/api/health'):return
        if find(s):stop_process(s)
        spawn(s,[HOME/'.local/bin/hermes','dashboard','--no-open','--host','127.0.0.1','--port',str(PORTS[s]),'--skip-build'])
        until=time.monotonic()+90
        while time.monotonic()<until:
            if probe(s,'/api/health'):return
            record=ledger().get(s);current=identity(record['pid']) if record else None
            # The installed launcher may exec through a shell before its Python
            # command line settles. A live original birth is not an exited child.
            # This permits waiting, never adoption or termination of a changed PID.
            if not current or current['birth']!=record['birth']:raise RuntimeError('Hermes terminó antes de estar disponible. Revisa sus registros.')
            time.sleep(.5)
        raise RuntimeError('Hermes no confirmó la salud de su interfaz local en 90 segundos.')
        return
    elif s in ('mlx','unsloth'):
        # These backends require a concrete model at startup. Persist queue state, not fictitious health.
        cfg=read(ROOT/'settings.json',{});cfg.setdefault('waiting',[])
        if s not in cfg['waiting']:cfg['waiting'].append(s)
        write(ROOT/'settings.json',cfg);return
    elif s=='exo':
        if find(s) and probe(s,'/state'):return
        spawn(s,[ROOT/'exo-runtime/bin/python',ROOT/'exo_local.py','--api-port',str(PORTS[s]),'--offline','--force-master','--no-batch'])
        wait(s,'/state',90);return
    if s not in ('strata','mirai'):wait(s)

def stop(s):
    if s.startswith('cloud-'):
        import external_providers
        return external_providers.disconnect(s)
    if s.startswith('remote-'):
        import remote_servers
        return remote_servers.disconnect(s)
    if s.startswith('custom-'):
        import integrations
        integrations.stop_custom(s)
    elif s=='strata':
        if registered('local.strata.small-model') or registered('local.strata.metal'):run([PYTHON,STRATA/'manager-control.py','stop'],90)
    elif s=='strata-llama':stop_process(s)
    elif s=='omlx' and find(s) and not same(ledger().get(s)):
        run([HOME/'.omlx/bin/omlx','stop'],90)
        until=time.monotonic()+20
        while port_open(PORTS[s]) and time.monotonic()<until:time.sleep(.2)
        if port_open(PORTS[s]):raise RuntimeError('oMLX aún está cerrándose.')
    elif s=='mirai':
        if registered('com.local.mirai-api'):run(['launchctl','bootout',DOMAIN+'/com.local.mirai-api'])
    elif s=='lmstudio':
        # Explicit UI stop covers this user's Studio service; CLI owns runtime teardown.
        loaded=json.loads(run([HOME/'.lmstudio/bin/lms','ps','--json'],20)) if (HOME/'.lmstudio/bin/lms').exists() else []
        if any(r.get('status') not in ('idle','ready','loaded',None) or r.get('queued',0) for r in loaded):raise RuntimeError('LM Studio está generando. Espera a que termine antes de detenerlo.')
        if loaded:run([HOME/'.lmstudio/bin/lms','unload','--all'],90)
        if port_open(PORTS[s]):run([HOME/'.lmstudio/bin/lms','server','stop'])
    elif s=='opencode':
        if same(ledger().get(s)):stop_process(s)
        run([HOME/'.opencode/bin/opencode','service','stop'],60)
    elif s=='unsloth':
        state=read(ROOT/'unsloth-state.json')
        if state:
            sys.path.insert(0,str(OLD));import unsloth_provider
            if state.get('launch_handle') in unsloth_provider._PROCESSES:unsloth_provider.stop(state)
            elif same(ledger().get(s)):
                d=ledger()[s]
                if os.getpgid(d['pid'])==d['pid']:os.killpg(d['pid'],signal.SIGTERM)
                else:os.kill(d['pid'],signal.SIGTERM)
                until=time.monotonic()+20
                while port_open(PORTS[s]) and time.monotonic()<until:time.sleep(.2)
                if port_open(PORTS[s]):raise RuntimeError('Studio aún está terminando; se conserva su identidad.')
            elif port_open(PORTS[s]):raise RuntimeError('No se ha podido identificar este proceso Studio.')
            set_process(s,None);(ROOT/'unsloth-state.json').unlink(missing_ok=True)
    elif s=='exo':
        d=ledger().get(s)
        if same(d):stop_process(s)
    else:stop_process(s)
    cfg=read(ROOT/'settings.json',{});cfg['waiting']=[x for x in cfg.get('waiting',[]) if x!=s];write(ROOT/'settings.json',cfg)
    active=read(ROOT/'active.json',{})
    if active.get('engine')==s:write(ROOT/'active.json',{})
    event('stop',{'service':s})

def available_services(include_unlinked=False):
    profile=read(ROOT/'installation.json',{})
    if not profile.get('clean') and not profile.get('detached') and sys.platform=='darwin':return list(NAMES)
    paths={'llama':LLAMA,'strata-llama':STRATA/'engines/llama-b11707/llama-server','strata':STRATA/'serve/server.py','opencode':HOME/'.opencode/bin/opencode','hermes':HOME/'.local/bin/hermes','fm':Path('/usr/bin/fm'),'mirai':Path('/usr/local/bin/mirai'),'vllm':Path('/opt/homebrew/bin/vllm'),'omlx':HOME/'.omlx/bin/omlx','lmstudio':Path('/Applications/LM Studio.app'),'mlx':OLD/'metrics_server.py','unsloth':HOME/'.unsloth/studio','exo':ROOT/'exo-runtime/bin/python','freellmapi':ROOT/'freellmapi/server/dist/index.js'}
    if sys.platform!='darwin':paths={}
    return [s for s in NAMES if s.startswith(('custom-','remote-','cloud-')) or s in paths and paths[s].exists() and (include_unlinked or not profile.get('detached') or s in profile.get('linked_services',[]))]

def unload_all(except_engine=None):
    active=read(ROOT/'active.json',{})
    if active.get('engine') and active['engine']!=except_engine:stop(active['engine'])
    # Reconcile exact known standalone engines left outside the manager.
    import integrations
    for s in ['strata','strata-llama','llama','fm','omlx','mlx','unsloth','vllm','exo']+[d['id'] for d in integrations.definitions() if d['kind']=='server']:
        if s==except_engine:continue
        if s=='strata' and (registered('local.strata.small-model') or registered('local.strata.metal')):stop(s)
        elif s in ('llama','fm','omlx') and find(s):stop(s)
        elif same(ledger().get(s)):stop(s)
    if except_engine!='mirai' and port_open(8001):stop('mirai')
    if except_engine!='lmstudio' and (HOME/'.lmstudio/bin/lms').exists():
        # The Studio API can be stopped while llmster still holds weights.
        # Inspect the official runtime inventory, never infer this from port 1234.
        loaded=json.loads(run([HOME/'.lmstudio/bin/lms','ps','--json'],20)) if (HOME/'.lmstudio/bin/lms').exists() else []
        if any(r.get('status') not in ('idle','ready','loaded',None) or r.get('queued',0) for r in loaded):raise RuntimeError('LM Studio está generando o tiene consultas en cola. Espera antes de cambiar de motor.')
        if loaded:run([HOME/'.lmstudio/bin/lms','unload','--all'],90)

def load(mid,engine):
    m=get_model(mid)
    if engine not in m['engines']:raise ValueError('El modelo no es compatible con este motor.')
    if not engine.startswith(('remote-','cloud-')):check_service_ports(engine)
    active=read(ROOT/'active.json',{})
    if active.get('id')==mid and active.get('engine')==engine and probe(engine):return active
    if not engine.startswith(('remote-','cloud-')):unload_all(except_engine=engine)
    if engine.startswith('custom-') and same(ledger().get(engine)):stop(engine)
    if engine in ('mlx','unsloth','vllm','strata-llama') and find(engine):stop(engine)
    if engine=='omlx' and find(engine):stop(engine)
    if engine=='lmstudio' and probe(engine):run([HOME/'.lmstudio/bin/lms','unload','--all'],90)
    start(engine)
    public=m.get('native_id',mid)
    if engine.startswith('custom-'):
        import integrations
        integrations.launch(engine,m);public=integrations.public_model(engine,m)
    elif engine=='llama':
        # A pre-existing single-model server must become the generated local router.
        listed=probe(engine) or {}
        if mid not in [x.get('id') for x in listed.get('data',[])]:stop(engine);start(engine)
        listing=probe(engine) or {};row=next((x for x in listing.get('data',[]) if x.get('id')==mid),{})
        if row.get('status',{}).get('value')!='loaded':http('http://127.0.0.1:'+str(PORTS[engine]),'/models/load',{'model':mid},timeout=240)
        public=mid
    elif engine=='mirai':public=m['native_id']
    elif engine=='strata':
        run([PYTHON,STRATA/'manager-control.py','start','strata'],240);public='strata'
    elif engine=='strata-llama':
        save_presets(engine='strata-llama')
        spawn(engine,[STRATA/'engines/llama-b11707/llama-server','--models-dir',ROOT/'router-models','--models-preset',ROOT/'models-strata.ini','--models-max','1','--host','127.0.0.1','--port',str(PORTS[engine]),'--offline','--metrics'],{'GGML_METAL_NO_RESIDENCY':'1'});wait(engine,timeout=120)
        http('http://127.0.0.1:'+str(PORTS[engine]),'/models/load',{'model':mid},timeout=240);public=mid
    elif engine=='vllm':
        profile=profile_for(m,engine)
        context=profile.get('context',m['context'])
        config=read(Path(m['path'])/'config.json',{});kind=config.get('model_type','')
        parser='qwen3_xml' if kind in ('qwen3_5','qwen3_5_moe') else 'hermes' if kind=='qwen3' else None
        tool_args=['--enable-auto-tool-choice','--tool-call-parser',parser] if parser else []
        spawn(engine,['/opt/homebrew/bin/vllm','serve',m['path'],'--host','127.0.0.1','--port',str(PORTS[engine]),'--served-model-name',mid,'--max-model-len',str(context),'--max-num-seqs','1','--max-num-batched-tokens',str(profile.get('batch',512)),'--gpu-memory-utilization','0.65','--kv-cache-memory-bytes','2147483648','--enforce-eager','--language-model-only',*tool_args],{'VLLM_MLX_DEVICE':'gpu'})
        wait(engine,timeout=300);public=mid
    elif engine=='fm':public='system'
    elif engine=='omlx':
        public=mid;http('http://127.0.0.1:'+str(PORTS[engine]),'/v1/models/'+mid+'/load',{},timeout=240)
    elif engine=='lmstudio':
        public='ia-local-'+mid
        load_path=gguf_link(m) if m['format']=='GGUF' else m['path']
        sys.path.insert(0,str(OLD));from local_providers import ProviderManager
        roots=ProviderManager(state_dir=ROOT/'provider-state').model_roots()
        def find_key():
            rows=json.loads(run([HOME/'.lmstudio/bin/lms','ls','--json'],30))
            for row in rows:
                for root in roots:
                    if (root/row.get('path','')).resolve()==Path(m['path']).resolve():return row['modelKey']
            return None
        cli_key=find_key()
        if not cli_key and m['format']=='GGUF':
            # Official symbolic import: no copy, move, or overwrite of the weights.
            run([HOME/'.lmstudio/bin/lms','import',load_path,'--symbolic-link','--user-repo','ia-local/'+mid,'--yes'],60)
            # The official indexer is asynchronous after import; a listed file is not yet a loadable key.
            until=time.monotonic()+30
            while time.monotonic()<until:
                cli_key=find_key()
                if cli_key:break
                time.sleep(1)
        if not cli_key:raise RuntimeError('LM Studio no confirmó una clave vigente para este modelo.')
        run([HOME/'.lmstudio/bin/lms','load',cli_key,'--identifier',public,'--context-length',str(m['context']),'--parallel','1','--no-speculative-draft-mtp','--yes'],240)
    elif engine=='exo':
        public='IA-Local/'+mid
        http('http://127.0.0.1:'+str(PORTS[engine]),'/place_instance',{'model_id':public,'min_nodes':1},timeout=30)
        until=time.monotonic()+240
        while time.monotonic()<until:
            current=probe(engine,'/state') or {}
            if not current and not find(engine):raise RuntimeError('El proceso EXO terminó antes de cargar el modelo.')
            runners=list(current.get('runners',{}).values())
            if any('RunnerFailed' in r for r in runners):raise RuntimeError('EXO no pudo cargar este modelo. Consulta sus registros.')
            if any('RunnerReady' in r for r in runners):break
            time.sleep(.5)
        else:raise RuntimeError('EXO no confirmó un runner preparado en 240 segundos.')
    elif engine=='mlx':
        spawn(engine,[OLD/'.venv/bin/python',OLD/'metrics_server.py','--model',m['path'],'--host','127.0.0.1','--port',str(PORTS[engine]),'--log-level','WARNING']);wait(engine,timeout=240);public=m['path']
    elif engine=='unsloth':
        sys.path.insert(0,str(OLD));import unsloth_provider
        selected=next((x for x in unsloth_provider.discover() if x['id']==m['load_keys']['unsloth']),None)
        if selected is None and m['format']=='GGUF':selected={'id':m['path'],'path':gguf_link(m),'format':'gguf','label':m['label']}
        if selected is None:raise RuntimeError('Unsloth no reconoce este checkpoint completo.')
        if not hasattr(unsloth_provider,'_ia_original_command'):unsloth_provider._ia_original_command=unsloth_provider.command
        def configured_command(home,port,model):
            args=unsloth_provider._ia_original_command(home,port,model);index=args.index('--max-seq-length');args[index+1]=str(m['context']);return args
        unsloth_provider.command=configured_command
        state=unsloth_provider.start(PORTS[engine],selected,ROOT/'unsloth-private');write(ROOT/'unsloth-state.json',state)
        d=identity(state['pid']);d['managed']=True;set_process('unsloth',d)
        public=unsloth_provider.load_selected(state,selected,time.monotonic()+300)
    # Readiness means a real model response, not just a catalog entry.
    proof=http(api_base(engine),'/v1/chat/completions',{'model':public,'messages':[{'role':'user','content':'Responde OK.'}],'max_tokens':1,'stream':False,'temperature':0},timeout=300,headers=model_headers(engine))
    if not proof.get('choices'):raise RuntimeError('El modelo no confirmó inferencia.')
    if engine in ('llama','strata-llama'):
        props=http('http://127.0.0.1:'+str(PORTS[engine]),'/props?model='+public,timeout=5)
        real_context=props.get('default_generation_settings',{}).get('n_ctx')
        if real_context!=m['context']:raise RuntimeError('Contexto real '+str(real_context)+' distinto del perfil '+str(m['context'])+'. Recarga el router.')
    state={'id':mid,'engine':engine,'public_model':public,'label':m['label'],'context':m['context'],'time':time.time()};write(ROOT/'active.json',state);event('load',state);return state

def model_headers(engine):
    if engine.startswith('cloud-'):return {'Authorization':'Bearer '+(ROOT/'token').read_text(encoding='utf-8')}
    if engine.startswith('remote-'):
        import remote_servers
        return remote_servers.headers(engine)
    if engine=='unsloth':
        sys.path.insert(0,str(OLD));import unsloth_provider
        return {'Authorization':'Bearer '+unsloth_provider.credentials(read(ROOT/'unsloth-state.json',{}))}
    return {}

def state():
    import lan, privileged,integrations,remote_servers,external_providers
    cfg=read(ROOT/'settings.json',{});rows=[]
    active=read(ROOT/'active.json',{})
    if active and (not remote_servers.connected(active['engine']) if active['engine'].startswith('remote-') else active['engine'] not in PORTS or not port_open(PORTS[active['engine']])):active={}
    if active.get('engine')=='mirai':
        health=probe('mirai','/health') or {}
        if health.get('loaded_model')!=next((m for m in models() if m['id']==active['id']),{}).get('native_id'):active={}
    studio_residents=[]
    try:
        running_studio=any('llmster' in (p.info['name'] or '').lower() for p in psutil.process_iter(['name']))
        if running_studio:studio_residents=json.loads(run([HOME/'.lmstudio/bin/lms','ps','--json'],5))
    except Exception:pass
    for s,name in list(NAMES.items()):
        if s.startswith(('remote-','cloud-')) or s not in available_services():continue
        data=probe(s) if s not in ('hermes','opencode','unsloth','exo','freellmapi') else None
        open_=port_open(PORTS[s]);p=find(s);status='Disponible' if data else 'Escuchando; verificación pendiente' if open_ else 'En espera de modelo' if s in cfg.get('waiting',[]) else 'Detenido'
        if s=='opencode' and open_:status='Servidor disponible' if probe(s,'/api/info') else 'Escuchando; verificación pendiente'
        if s=='hermes' and open_:status='Interfaz disponible' if probe(s,'/api/health') else 'Escuchando; verificación pendiente'
        if s=='freellmapi' and probe(s,'/api/auth/status'):status='Panel disponible · nube'
        if active.get('engine')==s and data:status='Modelo cargado'
        if s=='lmstudio' and studio_residents:status='Modelo residente'+(' · API disponible' if open_ else ' · API detenida')
        if s=='exo' and probe(s,'/state'):status='Disponible · solo este Mac'
        if p and not open_ and not data:status='Proceso sin salud confirmada'
        can_stop=bool(p) or s=='strata' and (registered('local.strata.small-model') or registered('local.strata.metal')) or s=='mirai' and registered('com.local.mirai-api')
        if s=='lmstudio' and open_:
            pids=listener_pids(PORTS[s]);can_stop=bool(pids) and all(expected_listener(s,pid) for pid in pids)
        if open_ and not can_stop and not data and s not in ('hermes','opencode'):status='Puerto ocupado; proceso sin identificar'
        rows.append({'id':s,'name':name,'can_stop':bool(can_stop),'kind':(integrations.definition(s) or {}).get('kind','agent' if s in ('opencode','hermes') else 'server'),'custom':s.startswith('custom-'),'port':PORTS[s],'state':status,'ready':bool(data or status in ('Servidor disponible','Interfaz disponible','Panel disponible · nube','Disponible · solo este Mac')),'running':bool(p or data or open_ or s=='lmstudio' and studio_residents),'managed':bool(p and p.get('managed')),'models':[x['id'] for x in (data or {}).get('data',[])],'url':'http://127.0.0.1:'+str(PORTS[s])})
    rows.extend(remote_servers.rows());rows.extend(external_providers.rows())
    mem=psutil.virtual_memory();gpu={}
    try:
        sys.path.insert(0,str(STRATA));from serve.telemetry import gpu_reader
        g=gpu_reader();gpu=g.read() if g.ok() else {}
    except Exception:pass
    if not gpu:
        import gpu_telemetry
        gpu=gpu_telemetry.read()
    try:wired=int(run(['/usr/sbin/sysctl','-n','iogpu.wired_limit_mb']))
    except Exception:wired=None
    with db() as c:
        events=[{'time':t,'kind':k,'data':json.loads(d)} for t,k,d in c.execute('SELECT time,kind,data FROM events ORDER BY time DESC LIMIT 30')]
        results=[{'id':i,'time':t,'model':m,'status':s,'data':json.loads(d)} for i,t,m,s,d in c.execute('SELECT * FROM results ORDER BY time DESC LIMIT 30')]
    import comparison, inference_stats, memory_status
    with db() as connection:inference=inference_stats.summary(connection)
    catalog=models();optimizations=read(ROOT/'optimizations.json',[])
    import updater
    from operations import agent_profiles
    updates=updater.rows_with_current_versions(read(ROOT/'updates.json',[]))
    comparisons=comparison.build(catalog,results,optimizations)
    gateway={'running':registered('ai.hermes.gateway'),'state':'Gestionado por launchd' if registered('ai.hermes.gateway') else 'Detenido'}
    import reset_state
    return {'platform':{'system':platform.system(),'architecture':platform.machine(),'gpu_limit_supported':sys.platform=='darwin','control_port':CONTROL_PORT},'reset_state':reset_state.status(),'gateway':gateway,'external_providers':external_providers.view(),'integrations':integrations.view(),'remote_servers':[{**d,'has_key':bool(remote_servers.headers(d['id']))} for d in remote_servers.definitions()],'helper':privileged.status(),'ui_stamp':str((ROOT/'index.html').stat().st_mtime_ns),'lan':lan.status(),'services':rows,'studio_residents':[{'label':r.get('displayName',r.get('modelKey')),'state':r.get('status'),'context':r.get('contextLength')} for r in studio_residents],'models':catalog,'comparisons':comparisons,'inference':inference,'active':active,'cpu':psutil.cpu_percent(interval=.1),'gpu':gpu.get('util'),'gpu_memory':gpu.get('mem_used',0)/2**30,'memory_breakdown':memory_status.read(),'ram_used':(mem.total-mem.available)/2**30,'ram_active':getattr(mem,'active',0)/2**30 if hasattr(mem,'active') else None,'ram_inactive':getattr(mem,'inactive',0)/2**30 if hasattr(mem,'inactive') else None,'ram_wired':getattr(mem,'wired',0)/2**30 if hasattr(mem,'wired') else None,'ram_available':mem.available/2**30,'ram_total':mem.total/2**30,'swap_used':psutil.swap_memory().used/2**30,'wired':wired,'wired_previous':read(ROOT/'gpu-previous.json'),'events':events,'results':results,'benchmark_series':read(ROOT/'benchmark-series.json',{}),'optimization_series':read(ROOT/'optimization-series.json',{}),'agent_checks':read(ROOT/'agent-checks.json',{}),'agent_profiles':agent_profiles(),'optimizations':read(ROOT/'optimizations.json',[]),'updates':updates,'settings':cfg,'time':time.time()}
