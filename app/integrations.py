"""Reviewed, user-owned local HTTP integrations; discovery never starts software."""
from core import *
import shutil,copy,ipaddress,string

REGISTRY=ROOT/'integrations.json'
KNOWN=[('ollama','server',['/opt/homebrew/bin/ollama','/Applications/Ollama.app/Contents/Resources/ollama']),('lmstudio','server',[str(HOME/'.lmstudio/bin/lms')]),('llama','server',[str(LLAMA)]),('strata-llama','server',[str(STRATA/'engines/llama-b11707/llama-server')]),('vllm','server',['/opt/homebrew/bin/vllm']),('omlx','server',[str(HOME/'.omlx/bin/omlx')]),('mlx','server',[str(OLD/'metrics_server.py')]),('mirai','server',['/usr/local/bin/mirai']),('exo','server',['/Applications/EXO.app/Contents/MacOS/EXO']),('fm','server',['/usr/bin/fm']),('opencode','agent',[str(HOME/'.opencode/bin/opencode')]),('hermes','agent',[str(HOME/'.local/bin/hermes')]),('aider','agent',['/opt/homebrew/bin/aider',str(HOME/'.local/bin/aider')]),('goose','agent',['/opt/homebrew/bin/goose',str(HOME/'.local/bin/goose')]),('crush','agent',['/opt/homebrew/bin/crush']),('openhands','agent',[str(HOME/'.local/bin/openhands'),'/opt/homebrew/bin/openhands']),('codex','agent',['/opt/homebrew/bin/codex','/Applications/Codex.app/Contents/MacOS/Codex'])]

if sys.platform!='darwin':KNOWN=[(name,kind,[]) for name,kind in [('ollama','server'),('llama-server','server'),('vllm','server'),('lms','server'),('opencode','agent'),('hermes','agent'),('aider','agent'),('goose','agent')]]

def definitions():return read(REGISTRY,{'items':[]}).get('items',[])
def definition(s):return next((d for d in definitions() if d.get('id')==s),None)
def validate(value):
    if not isinstance(value,dict):raise ValueError('La propuesta debe ser un objeto JSON.')
    d=copy.deepcopy(value);sid=d.get('id','')
    if not re.fullmatch(r'custom-[a-z][a-z0-9-]{1,40}',sid):raise ValueError('El identificador debe empezar por custom- y usar letras minúsculas, números o guiones.')
    if d.get('kind') not in ('server','agent'):raise ValueError('Tipo: server o agent.')
    name=d.get('name','').strip()
    if not 1<=len(name)<=80:raise ValueError('Nombre no válido.')
    exe=Path(d.get('executable','')).expanduser()
    if not exe.is_absolute() or not exe.is_file() or not os.access(exe,os.X_OK):raise ValueError('El ejecutable debe existir, ser ejecutable y tener ruta absoluta.')
    banned={'sh','bash','dash','ash','ksh','csh','tcsh','zsh','fish','busybox','cmd','powershell','pwsh','wscript','cscript','sudo','osascript','launchctl','curl','wget','rm'}
    if exe.suffix.lower() in ('.cmd','.bat','.ps1','.vbs','.js') or exe.stem.lower() in banned or exe.resolve().stem.lower() in banned:raise ValueError('El asistente no admite shells, elevación ni comandos de instalación.')
    port=d.get('port')
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Puerto entre 1024 y 65535.')
    validate_ports({**{s:p for s,p in PORTS.items() if s!=sid},sid:port})
    args=d.get('args')
    if not isinstance(args,list) or len(args)>80 or any(not isinstance(a,str) or len(a)>4096 or '\x00' in a for a in args):raise ValueError('Argumentos: una lista de cadenas, sin shell.')
    if any(re.search(r'api.?key|password|secret|bearer|sk-[A-Za-z0-9]{12}',a,re.I) for a in args):raise ValueError('No incluyas credenciales en los argumentos. Configúralas con el mecanismo propio del servicio.')
    allowed={'host','port','model','model_id','context'}
    for a in args+[d.get('public_model','{model_id}')]:
        try:
            fields=[(field,spec,conversion) for _,field,spec,conversion in string.Formatter().parse(a) if field is not None]
        except (ValueError,TypeError):raise ValueError('Plantilla mal formada.') from None
        if any(field not in allowed or spec or conversion for field,spec,conversion in fields):raise ValueError('Plantilla no admitida.')
        if set(re.findall(r'\{([^{}]+)\}',a))-allowed:raise ValueError('Plantilla no admitida. Usa {host}, {port}, {model}, {model_id} o {context}.')
    bind=d.get('bind','args')
    if bind not in ('args','ollama'):raise ValueError('Enlace: args u ollama.')
    if bind=='args' and (not any('{host}' in a for a in args) or not any('{port}' in a for a in args)):raise ValueError('La orden debe usar {host} y {port} para limitarla a loopback y al puerto reservado.')
    if bind=='ollama' and (exe.stem.lower()!='ollama' or args!=['serve']):raise ValueError('El modo Ollama admite exclusivamente ollama serve.')
    mode=d.get('start_mode','idle')
    if mode not in ('idle','model'):raise ValueError('Arranque: idle o model.')
    if d['kind']=='agent' and mode!='idle':raise ValueError('Un agente HTTP debe poder arrancar sin pesos.')
    path=d.get('health_path','/v1/models')
    if not isinstance(path,str) or not re.fullmatch(r'/[A-Za-z0-9_./?=&-]{0,180}',path) or '..' in path:raise ValueError('Ruta de salud local no válida.')
    formats=d.get('formats',[]);architectures=d.get('architectures',[])
    if not isinstance(formats,list) or set(formats)-{'GGUF','MLX','Safetensors','System','Sistema','Apple FM'}:raise ValueError('Formato no admitido.')
    if not isinstance(architectures,list) or any(not isinstance(a,str) or len(a)>80 for a in architectures):raise ValueError('Arquitecturas no válidas.')
    public=d.get('public_model','{model_id}')
    if not isinstance(public,str) or len(public)>250 or set(re.findall(r'\{([^{}]+)\}',public))-allowed:raise ValueError('Nombre público del modelo no válido.')
    notes=d.get('notes','')
    if not isinstance(notes,str) or len(notes)>6000:raise ValueError('Notas demasiado extensas.')
    return {'id':sid,'name':name,'kind':d['kind'],'executable':str(exe),'args':args,'port':port,'bind':bind,'start_mode':mode,'health_path':path,'formats':formats if d['kind']=='server' else [],'architectures':architectures,'public_model':public,'notes':notes,'compatibility':'Declarada por el usuario; pendiente de prueba funcional'}

def install_registry():
    for d in definitions():
        sid=d.get('id','')
        if re.fullmatch(r'custom-[a-z][a-z0-9-]{1,40}',sid) and type(d.get('port')) is int:
            proposed={**PORTS,sid:d['port']}
            try:validate_ports(proposed)
            except RuntimeError:continue
            PORTS[sid]=d['port'];NAMES[sid]=d.get('name',sid)

def register(value):
    d=validate(value);sid=d['id']
    if same(ledger().get(sid)) or sid in PORTS and port_open(PORTS[sid]):raise RuntimeError('Detén esta integración antes de modificarla.')
    if port_open(d['port']):raise RuntimeError('El puerto está ocupado. Elige otro; se conserva el proceso existente.')
    items=[x for x in definitions() if x['id']!=sid];items.append(d)
    backup=ROOT/'backups'/('integrations-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3));backup.mkdir()
    if REGISTRY.exists():shutil.copy2(REGISTRY,backup/REGISTRY.name)
    write(REGISTRY,{'items':items,'time':time.time()});install_registry();event('integration-registered',{'id':sid,'port':d['port'],'kind':d['kind']})
    return {'message':d['name']+' guardado. No se ha arrancado ni instalado software. Prueba Arrancar y la respuesta antes de usar modelos reales.','definition':d}

def unregister(sid):
    if not definition(sid):raise ValueError('Integración no encontrada.')
    if same(ledger().get(sid)) or port_open(PORTS[sid]):raise RuntimeError('Detén primero la integración; no se elimina ningún proceso por su puerto.')
    write(REGISTRY,{'items':[d for d in definitions() if d['id']!=sid],'time':time.time()});PORTS.pop(sid,None);NAMES.pop(sid,None);event('integration-unregistered',{'id':sid});return {'message':'Integración retirada del panel. Sus archivos y modelos se conservan.'}

def attach_models(rows):
    custom=[d for d in definitions() if d.get('kind')=='server' and d.get('id') in PORTS]
    result=copy.deepcopy(rows)
    for m in result:
        m['engines']=[e for e in m['engines'] if not e.startswith('custom-')]
        for d in custom:
            if m['format'] in d['formats'] and (not d['architectures'] or m.get('architecture') in d['architectures']):m['engines'].append(d['id'])
    return result

def probe_custom(s):
    d=definition(s)
    if not d:return None
    try:
        result=http('http://127.0.0.1:'+str(d['port']),d['health_path'],text=d['kind']=='agent')
        return result if isinstance(result,dict) else {'ready':True,'data':[]}
    except (OSError,ValueError):return None

def stop_custom(s):
    d=ledger().get(s)
    if hasattr(os,'getpgid') and same(d) and d.get('managed') and os.getpgid(d['pid'])==d['pid']:os.killpg(d['pid'],signal.SIGTERM)
    stop_process(s)
    if not same(d):set_process(s,None)

def verify_loopback(s):
    d=ledger().get(s)
    if not same(d):raise RuntimeError('No se conserva la identidad del proceso arrancado.')
    try:
        p=psutil.Process(d['pid']);listeners=[c for child in [p]+p.children(recursive=True) for c in child.net_connections('tcp') if c.status=='LISTEN']
        if not listeners:raise RuntimeError('No se pudo verificar el enlace del proceso.')
        if any(not ipaddress.ip_address(c.laddr.ip).is_loopback for c in listeners):raise RuntimeError('El proceso abrió una interfaz ajena a loopback; se ha detenido.')
        if not any(c.laddr.port==PORTS[s] for c in listeners):raise RuntimeError('El proceso no abrió su puerto reservado.')
    except (psutil.Error,RuntimeError) as e:
        stop_custom(s);raise RuntimeError('No se confirma el aislamiento de red: '+str(e)) from None

def launch(s,model=None):
    d=definition(s)
    if not d:raise ValueError('Integración desconocida.')
    if d['start_mode']=='model' and model is None:
        cfg=read(ROOT/'settings.json',{});cfg.setdefault('waiting',[])
        if s not in cfg['waiting']:cfg['waiting'].append(s)
        write(ROOT/'settings.json',cfg);return
    if same(ledger().get(s)) and probe_custom(s):return
    values={'host':'127.0.0.1','port':str(d['port']),'model':(model or {}).get('path',''),'model_id':(model or {}).get('id',''),'context':str((model or {}).get('context',4096))}
    args=[a.format(**values) for a in d['args']];env={'OLLAMA_HOST':'127.0.0.1:'+str(d['port'])} if d['bind']=='ollama' else {}
    spawn(s,[d['executable'],*args],env)
    until=time.monotonic()+120
    while time.monotonic()<until:
        if probe_custom(s):verify_loopback(s);return
        if not same(ledger().get(s)):raise RuntimeError('El proceso terminó antes de confirmar salud.')
        time.sleep(.3)
    stop_custom(s);raise RuntimeError('No confirmó salud en 120 segundos. Revisa argumentos y registros.')

def public_model(s,m):
    d=definition(s);return d['public_model'].format(host='127.0.0.1',port=d['port'],model=m.get('path',''),model_id=m['id'],context=m['context'])

def scan():
    rows=[];known_paths=set()
    for name,kind,paths in KNOWN:
        path=next((Path(p) for p in paths if Path(p).is_file()),None)
        if path is None:
            found=shutil.which(name,path=os.pathsep.join([str(HOME/'.local/bin'),str(HOME/'.opencode/bin'),os.environ.get('PATH',''),'/opt/homebrew/bin','/usr/local/bin','/usr/bin']))
            if found:path=Path(found)
        if path:
            known_paths.add(str(path.resolve()));rows.append({'name':name,'kind':kind,'executable':str(path),'adapter':'Integrado' if name in PORTS else 'Necesita asistente/adaptador','registered':name in available_services(),'builtin':name if name in available_services(include_unlinked=True) else None})
    for item in definitions():rows.append({'name':item['name'],'kind':item['kind'],'executable':item['executable'],'adapter':'Integración revisada','registered':True,'id':item['id']});known_paths.add(str(Path(item['executable']).resolve()))
    # Discover other user-owned listeners without copying argv or credentials.
    for p in psutil.process_iter(['name','exe']):
        try:
            if not own_process(p):continue
            exe=p.info['exe'] or '';name=p.info['name'] or ''
            if not exe or exe in known_paths or not re.search(r'ollama|llama|vllm|mlx|hermes|opencode|aider|goose|crush|openhands|kobold|tabby|litellm|lmstudio',name,re.I):continue
            ports=sorted({c.laddr.port for c in p.net_connections('tcp') if c.status=='LISTEN' and ipaddress.ip_address(c.laddr.ip).is_loopback})
            if ports:rows.append({'name':name,'kind':'agent' if re.search('hermes|opencode|aider|goose|crush',name,re.I) else 'server','executable':exe,'ports':ports,'adapter':'Proceso detectado; no gestionado','registered':False});known_paths.add(exe)
        except (psutil.Error,OSError):pass
    result={'time':time.time(),'items':rows,'message':str(len(rows))+' instalaciones o procesos encontrados. Detectado no significa compatible, arrancado ni modelo cargado.'};write(ROOT/'integration-discovery.json',result);return result

def view():return {'registered':definitions(),'discovery':read(ROOT/'integration-discovery.json',{}),'proposal':read(ROOT/'integration-proposal.json',{})}
