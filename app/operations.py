'Controlled evaluations, model-specific tuning, version checks and agent profiles. Synthetic benchmarks are distinct from passively observed requests; trial failure/cancellation is persisted rather than reported as valid speed.'
import concurrent.futures, configparser, math, shutil, statistics, tarfile, urllib.parse
from core import *

SOURCES={
 'hermes':('NousResearch/hermes-agent',str(HOME/'.local/bin/hermes'),'https://github.com/NousResearch/hermes-agent/releases'),
 'opencode':('anomalyco/opencode',str(HOME/'.opencode/bin/opencode'),'https://opencode.ai/download'),
 'llama':('ggml-org/llama.cpp',str(LLAMA),'https://github.com/ggml-org/llama.cpp/releases'),
 'strata-llama':('ggml-org/llama.cpp',str(STRATA/'engines/llama-b11707/llama-server'),'https://github.com/ggml-org/llama.cpp/releases'),
 'strata':('Niko1221/Strata',None,'https://github.com/Niko1221/Strata/releases'),
 'omlx':('jundot/omlx',str(HOME/'.omlx/bin/omlx'),'https://github.com/jundot/omlx/releases'),
 'exo':('exo-explore/exo',None,'https://github.com/exo-explore/exo/releases'),
 'lmstudio':(None,None,'https://lmstudio.ai/download'),
 'mirai':(None,'/usr/local/bin/mirai','https://github.com/trymirai/uzu'),
 'unsloth':('unslothai/unsloth',None,'https://github.com/unslothai/unsloth/releases'),
 'mlx':('ml-explore/mlx-lm',None,'https://github.com/ml-explore/mlx-lm/releases'),
 'vllm':('vllm-project/vllm-metal',None,'https://github.com/vllm-project/vllm-metal/releases'),
 'freellmapi':('tashfeenahmed/freellmapi',None,'https://github.com/tashfeenahmed/freellmapi/releases'),
 'fm':(None,None,'https://support.apple.com/guide/mac-help/get-macos-updates-mchlpx1065/mac')}

def installed(s,exe):
    if exe and s not in ('llama','strata-llama'):
        try:return run([exe,'--version'],20).splitlines()[0]
        except Exception:return 'No comprobada'
    if s in ('llama','strata-llama'):
        try:
            p=subprocess.run([exe or str(LLAMA),'--version'],capture_output=True,text=True,timeout=20);text=p.stdout+' '+p.stderr;m=re.search(r'(?:version:\s*)?([^\n]*\b(?:build|commit)\b[^\n]*)',text);return m[1].strip() if m else text.strip().splitlines()[0] if text.strip() else 'No comprobada'
        except Exception:return 'No comprobada'
    if s=='freellmapi':return 'Fuente 369c471 (paquete 0.2.1)'
    if s=='vllm':
        try:
            from email.parser import Parser
            p=next(Path('/opt/homebrew/opt/vllm-metal/libexec').glob('lib/python*/site-packages/vllm_metal-*.dist-info/METADATA'));return Parser().parsestr(p.read_text(encoding='utf-8'))['Version']+' (Metal)'
        except Exception:return 'No comprobada'
    if s=='strata':return '0.1.45 + parches Metal locales'
    apps={'exo':'EXO','lmstudio':'LM Studio'}
    if s in apps:
        try:return plistlib.loads((Path('/Applications')/(apps[s]+'.app')/'Contents/Info.plist').read_bytes())['CFBundleShortVersionString']
        except Exception:return 'No comprobada'
    if s=='fm':return run(['/usr/bin/sw_vers','-productVersion'])+' (macOS)'
    paths={'unsloth':HOME/'.unsloth/studio/unsloth_studio/lib/python3.13/site-packages','mlx':OLD/'.venv/lib/python3.12/site-packages'}
    name='unsloth' if s=='unsloth' else 'mlx_lm'
    try:
        from email.parser import Parser
        p=next(paths[s].glob(name+'-*.dist-info/METADATA'));return Parser().parsestr(p.read_text(encoding='utf-8'))['Version']
    except Exception:return 'No comprobada'
def check_updates():
    def check(item):
        s,(repo,exe,url)=item;row={'id':s,'name':NAMES[s],'installed':installed(s,exe),'source':url,'time':time.time(),'status':'Comprobación manual','latest':None}
        if repo:
            try:
                req=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers={'User-Agent':'IA-Local/1.0','Accept':'application/vnd.github+json'})
                with urllib.request.urlopen(req,timeout=15) as r:v=json.load(r)
                row.update(latest=v['tag_name'],source=v['html_url'],release_name=v.get('name'),published=v.get('published_at'))
                a=re.search(r'\d+\.\d+\.\d+',row['installed']);b=re.search(r'\d+\.\d+\.\d+',row['latest'])
                if a and b:row['status']='Actualización disponible' if tuple(map(int,a[0].split('.')))<tuple(map(int,b[0].split('.'))) else 'Sin versión estable posterior'
                else:row['status']='Comparar build y cambios locales'
                if s in ('strata','freellmapi'):row['status']='Compilación local: revisar commit y cambios'
                if s in ('llama','strata-llama'):row['status']='Comparar build y commit del motor local'
                if s=='unsloth':row['status']='Versión de paquete y release con numeración distinta'
                if re.search(r'(rc|alpha|beta|dev)',row['latest'],re.I):row['status']='Publicación preliminar: revisar canal'
                if s=='opencode' and a and b and a[0].split('.')[0]!=b[0].split('.')[0]:row['status']='Canal instalado y release con versión principal distinta'
            except Exception:row['status']='No comprobado: sin respuesta de la fuente'
        from updater import policy
        row.update(policy(s))
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,[(s,v) for s,v in SOURCES.items() if s in available_services()]))
    write(ROOT/'updates.json',rows);return rows

def update_agents(s):
    if s not in ('hermes','opencode'):raise RuntimeError('Este componente se actualiza mediante su instalador oficial. Se conserva la compilación y los ajustes locales.')
    if s=='opencode':
        row=next((r for r in read(ROOT/'updates.json',[]) if r['id']==s),{})
        current=installed(s,str(HOME/'.opencode/bin/opencode'));a=re.search(r'\d+\.\d+\.\d+',current);b=re.search(r'\d+\.\d+\.\d+',row.get('latest') or '')
        if not a or not b:raise RuntimeError('Comprueba primero el canal oficial de OpenCode; no hay una versión disponible verificada.')
        if a[0].split('.')[0]!=b[0].split('.')[0]:raise RuntimeError('La publicación consultada pertenece a otra versión principal. Se conserva el canal instalado de OpenCode.')
        if tuple(map(int,b[0].split('.')))<=tuple(map(int,a[0].split('.'))):return {'message':'OpenCode ya está en esa versión o en una posterior.','changed':False}
    if port_open(PORTS[s]):raise RuntimeError('Detén '+NAMES[s]+' antes de actualizar. No se interrumpe una sesión activa.')
    if s=='hermes' and registered('ai.hermes.gateway'):raise RuntimeError('Detén también el gateway de Hermes antes de actualizar el código.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');target=ROOT/'backups'/stamp;target.mkdir()
    if s=='hermes':
        repo=HOME/'.hermes/hermes-agent'
        if run(['git','-C',repo,'status','--porcelain']):raise RuntimeError('Hermes tiene cambios locales. Revisa el instalador oficial antes de actualizar; no se sobrescriben tus cambios.')
        commit=run(['git','-C',repo,'rev-parse','HEAD']);write(target/'restore.json',{'service':s,'repo':str(repo),'commit':commit})
        shutil.copyfile(HOME/'.hermes/config.yaml',target/'config.yaml')
        run([HOME/'.local/bin/hermes','update'],900)
    else:
        exe=HOME/'.opencode/bin/opencode';shutil.copy2(exe,target/'opencode');shutil.copy2(HOME/'.config/opencode/opencode.json',target/'opencode.json')
        write(target/'restore.json',{'service':s,'executable':str(exe)})
        try:run([exe,'upgrade'],600);run([exe,'--version'])
        except Exception:shutil.copy2(target/'opencode',exe);raise
    event('update',{'service':s,'backup':str(target)});return {'message':'Actualización ejecutada; copia de recuperación en '+str(target)}

def configure_agents(mid,select=True,engine=None,targets=None):
    import yaml
    m=get_model(mid)
    targets=['opencode','hermes'] if targets is None else list(dict.fromkeys(targets))
    if not targets or any(a not in ('opencode','hermes') for a in targets):raise ValueError('Agente de destino no válido.')
    if select and 'hermes' in targets and m['context']<64000:raise RuntimeError('Hermes requiere 64000 tokens. Usa un modelo cargado con ese contexto; OpenCode admite perfiles menores.')
    engine=engine or m['engines'][0]
    if engine not in m['engines']:raise RuntimeError('El motor no es compatible con este perfil.')
    alias=engine+'/'+mid
    base='http://127.0.0.1:'+str(CONTROL_PORT)+'/v1';token=(ROOT/'token').read_text(encoding='utf-8')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=ROOT/'backups'/('agents-'+stamp+'-'+secrets.token_hex(3));backup.mkdir()
    oc=HOME/'.config/opencode/opencode.json';hc=HOME/'.hermes/config.yaml'
    shutil.copy2(oc,backup/'opencode.json');shutil.copy2(hc,backup/'config.yaml')
    catalog={e+'/'+r['id']:{'name':NAMES[e]+' · '+r['label'],'limit':{'context':r['context'],'output':min(4096,r['context']//4)}} for r in models() for e in r['engines']}
    c=json.loads(oc.read_text(encoding='utf-8'));provider={'name':'IA Local','package':'@opencode/ai/providers/openai-compatible','settings':{'baseURL':base,'apiKey':token},'models':catalog}
    c.setdefault('providers',{})['ia-local']=provider
    if isinstance(c.get('enabled_providers'),list) and 'ia-local' not in c['enabled_providers']:c['enabled_providers'].append('ia-local')
    if select:c['model']='ia-local/'+alias
    d=yaml.safe_load(hc.read_text(encoding='utf-8'));d.setdefault('providers',{})['ia-local']={'base_url':base,'api_key':token,'transport':'chat_completions','discover_models':True,'context_length':m['context'],'models':{k:{'context_length':v['limit']['context']} for k,v in catalog.items()}}
    if select:d.setdefault('model',{}).update(provider='ia-local',default=alias,base_url=base,context_length=m['context'],api_mode='chat_completions')
    # Validate both documents before replacing either; preserve complete originals.
    text=yaml.safe_dump(d,allow_unicode=True,sort_keys=False);yaml.safe_load(text)
    try:
        if 'opencode' in targets:write(oc,c)
        if 'hermes' in targets:
            temp=hc.with_suffix('.yaml.ia-local.tmp');temp.write_text(text,encoding='utf-8');os.chmod(temp,0o600);temp.replace(hc)
    except Exception:
        if 'opencode' in targets:shutil.copy2(backup/'opencode.json',oc)
        if 'hermes' in targets:shutil.copy2(backup/'config.yaml',hc)
        raise RuntimeError('No se pudo guardar el perfil; se restauraron las configuraciones anteriores.') from None
    write(backup/'selection.json',{'targets':targets,'model':mid,'engine':engine,'context':m['context']})
    warnings=[]
    if select and 'opencode' in targets and probe('opencode'):
        try:run([HOME/'.opencode/bin/opencode','reload'],30)
        except Exception:warnings.append('OpenCode guardado; usa su opción Reload antes de abrir una sesión nueva.')
    event('agents-configured',{'model':mid,'engine':engine,'targets':targets,'backup':str(backup),'routes':len(catalog)})
    return {'message':'Perfil '+NAMES[engine]+' · '+m['label']+' · '+str(m['context'])+' tokens aplicado a '+', '.join(NAMES[a] for a in targets)+'. Abre una sesión nueva para usarlo.','backup':str(backup),'targets':targets,'warnings':warnings}


def configure_active_agents(target):
    targets=['opencode','hermes'] if target=='both' else [target]
    if any(t not in ('opencode','hermes') for t in targets):raise ValueError('Agente de destino no válido.')
    active=read(ROOT/'active.json',{})
    if not active.get('id'):raise RuntimeError('Carga primero un modelo desde Control. No basta con arrancar el servidor vacío.')
    m=get_model(active['id']);engine=active['engine']
    if engine not in m['engines'] or active.get('context')!=m['context']:raise RuntimeError('El perfil ha cambiado; vuelve a cargar el modelo antes de enviarlo a los agentes.')
    if 'hermes' in targets and m['context']<64000:raise RuntimeError('Hermes requiere 64000 tokens. Puedes usar este modelo solo en OpenCode o cargarlo con más contexto.')
    if not engine.startswith('remote-'):check_service_ports(engine)
    if not probe(engine):raise RuntimeError('El servidor del modelo activo no responde. No se cambian los agentes.')
    body={'model':active['public_model'],'messages':[{'role':'user','content':'Responde OK.'}],'max_tokens':1,'temperature':0,'stream':False}
    if engine=='exo':body['enable_thinking']=False
    else:body['chat_template_kwargs']={'enable_thinking':False}
    response=http(api_base(engine),'/v1/chat/completions',body,timeout=90,headers=model_headers(engine))
    if not response.get('choices'):raise RuntimeError('El modelo activo no confirmó disponibilidad. No se cambian los agentes.')
    return configure_agents(m['id'],engine=engine,targets=targets)


def agent_profiles():
    import yaml
    result={}
    try:
        c=read(HOME/'.config/opencode/opencode.json',{});selection=c.get('model','');result['opencode']={'selection':selection if isinstance(selection,str) else 'Sin selección'}
    except Exception:result['opencode']={'selection':'No disponible'}
    try:
        c=yaml.safe_load((HOME/'.hermes/config.yaml').read_text(encoding='utf-8')) or {};m=c.get('model',{});result['hermes']={'selection':((m.get('provider','')+'/'+m.get('default','')) if isinstance(m,dict) else str(m)),'context':m.get('context_length') if isinstance(m,dict) else None}
    except Exception:result['hermes']={'selection':'No disponible'}
    return result

def restore_agents():
    backups=sorted((ROOT/'backups').glob('agents-*'),key=lambda p:p.stat().st_mtime_ns)
    if not backups:raise RuntimeError('No hay una copia previa de perfiles de agentes.')
    source=backups[-1]
    targets=read(source/'selection.json',{}).get('targets',['opencode','hermes'])
    if 'opencode' in targets:shutil.copy2(source/'opencode.json',HOME/'.config/opencode/opencode.json')
    if 'hermes' in targets:shutil.copy2(source/'config.yaml',HOME/'.hermes/config.yaml')
    return {'message':'Restaurados los perfiles previos. Reinicia las sesiones para aplicarlos.'}

def evaluation_model(value):
    if not isinstance(value,dict):return get_model(value)
    model=get_model(value.get('id'));context=value.get('context')
    if type(context) is not int or context not in (4096,8192,32768,65536) or context>model.get('max_context',model['context']):raise ValueError('Contexto no compatible para esta evaluación.')
    if context!=model['context']:
        unload_all();contexts=read(ROOT/'contexts.json',{});contexts[model['id']]=context;write(ROOT/'contexts.json',contexts)
        catalog=read(ROOT/'catalog.json',{})
        for row in catalog['models']:
            if row['id']==model['id']:row['context']=context
        write(ROOT/'catalog.json',catalog);save_presets();model['context']=context
        event('evaluation-context',{'model':model['id'],'context':context})
    return model

def benchmark(mid,engine,cancel,progress):
    m=evaluation_model(mid);mid=m['id'];rid=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
    result={'id':rid,'model':mid,'engine':engine,'started':time.time(),'method':'llama-bench pp512/tg128 x3' if engine in ('llama','strata-llama') else 'API sintética x3','parameters':{'context':m['context'],'threads':4,'batch':512,'ubatch':128,'reasoning':'off'},'system':{'os':platform.platform(),'wired':run(['/usr/sbin/sysctl','-n','iogpu.wired_limit_mb']) if sys.platform=='darwin' else None},'status':'running'}
    prior=read(ROOT/'active.json',{});write(ROOT/'benchmark-progress.json',result)
    result['engine_version']=installed(engine,SOURCES.get(engine,(None,None,None))[1]);result['parameters']={'context':m['context'],'synthetic_generation_budget':128,'functional_generation_budget':1024 if engine in ('mirai','lmstudio') else 128,'reasoning':'Según el modelo y el motor'}
    if engine in ('llama','strata-llama'):result['parameters'].update(threads=4,batch=512,ubatch=128,reasoning='off')
    sampling=threading.Event();observed={'min_available_gib':psutil.virtual_memory().available/2**30,'max_used_gib':psutil.virtual_memory().used/2**30,'swap_before_gib':psutil.swap_memory().used/2**30}
    def sample_memory():
        while not sampling.wait(.25):
            mem=psutil.virtual_memory();observed['min_available_gib']=min(observed['min_available_gib'],mem.available/2**30);observed['max_used_gib']=max(observed['max_used_gib'],mem.used/2**30)
    threading.Thread(target=sample_memory,daemon=True).start()
    try:
        progress('Preparando uso exclusivo');unload_all()
        if engine in ('llama','strata-llama'):
            stop(engine)
            binary=LROOT/'optimizacion-m4-pro/bin/llama-bench' if engine=='llama' else STRATA/'engines/llama-b11707/llama-bench'
            args=[str(binary),'-m',m['path'],'-p','512','-n','128','-r','3','-t','4','-b','512','-ub','128','-ngl','99','-fa','1','-o','json']
            path=ROOT/'results'/(rid+'.raw.json');log=ROOT/'results'/(rid+'.log')
            with path.open('w') as out,log.open('w') as err:
                p=subprocess.Popen(args,stdout=out,stderr=err,env={**os.environ,'GGML_METAL_NO_RESIDENCY':'1'},start_new_session=True)
                began=time.monotonic();peak=0
                while p.poll() is None:
                    if cancel.is_set():p.terminate();p.wait(timeout=20);raise RuntimeError('Evaluación cancelada.')
                    try:peak=max(peak,psutil.Process(p.pid).memory_info().rss)
                    except psutil.Error:pass
                    progress('Midiendo pp512 / tg128 · '+str(int(time.monotonic()-began))+' s');time.sleep(.5)
                    if time.monotonic()-began>600:p.terminate();raise RuntimeError('Evaluación agotó el tiempo máximo.')
            if p.returncode:raise RuntimeError('llama-bench falló; no se calcula una tasa válida. Consulta el log del ensayo.')
            raw=json.loads(path.read_text(encoding='utf-8'));result.update(raw=raw,peak_rss_gib=peak/2**30,version=result['engine_version'])
        progress('Comprobación funcional real');began_load=time.monotonic();active=load(mid,engine);result['load_s']=time.monotonic()-began_load
        base=api_base(engine);headers=model_headers(engine)
        result['functional']=functional(engine,active['public_model'])
        if True:
            runs=[]
            for i in range(3):
                if cancel.is_set():raise RuntimeError('Evaluación cancelada.')
                progress('Generación API '+str(i+1)+'/3');start_=time.monotonic();d=http(base,'/v1/chat/completions',{'model':active['public_model'],'messages':[{'role':'user','content':'Escribe una historia en español sobre un faro y un robot. Empieza directamente.'}],'max_tokens':128,'temperature':0,'stream':False},timeout=240,headers=headers);runs.append({'wall_s':time.monotonic()-start_,'response':d})
            result['runs']=runs
        if observed['min_available_gib']<1 or psutil.swap_memory().used/2**30-observed['swap_before_gib']>.5:raise RuntimeError('Margen de memoria insuficiente durante la evaluación. No se considera un resultado válido.')
        result['status']='passed';progress('Evaluación completada')
    except Exception as e:result.update(status='cancelled' if cancel.is_set() else 'failed',error=str(e));raise
    finally:
        sampling.set();observed['swap_after_gib']=psutil.swap_memory().used/2**30;result['memory_system_observed']=observed
        result['finished']=time.time();write(ROOT/'results'/(rid+'.json'),result)
        with db() as c:c.execute('INSERT OR REPLACE INTO results VALUES(?,?,?,?,?)',(rid,time.time(),mid,result['status'],json.dumps(result,ensure_ascii=False)))
        write(ROOT/'benchmark-progress.json',result)
        try:unload_all();write(ROOT/'active.json',{})
        except Exception as e:
            result.update(status='failed',cleanup_error=str(e));write(ROOT/'results'/(rid+'.json'),result)
            with db() as c:c.execute('UPDATE results SET status=?,data=? WHERE id=?',('failed',json.dumps(result,ensure_ascii=False),rid))
    if result.get('cleanup_error'):raise RuntimeError('La prueba terminó, pero no se confirmó la liberación de memoria: '+result['cleanup_error'])
    return result


def benchmark_all(mid,cancel,progress):
    model=evaluation_model(mid);mid=model['id'];engines=list(dict.fromkeys(model['engines']));group='series-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
    report={'id':group,'model':mid,'context':model['context'],'started':time.time(),'status':'running','rows':[],'skipped':[{'engine':s,'reason':'Formato o arquitectura no compatible con este archivo.'} for s in PORTS if s not in engines and s not in ('opencode','hermes','freellmapi')],'order':engines}
    path=ROOT/'results'/(group+'.json');write(path,report)
    try:
        unload_all();write(ROOT/'active.json',{})
        for index,engine in enumerate(engines):
            if cancel.is_set():report['status']='cancelled';break
            prefix=str(index+1)+'/'+str(len(engines))+' · '+NAMES[engine]+' · '
            progress(prefix+'Preparando carga exclusiva…')
            try:
                unload_all();write(ROOT/'active.json',{})
                result=benchmark(mid,engine,cancel,lambda message:progress(prefix+message));report['rows'].append({'engine':engine,'status':result['status'],'result_id':result['id']})
            except Exception as e:
                report['rows'].append({'engine':engine,'status':'cancelled' if cancel.is_set() else 'failed','error':str(e)})
                if cancel.is_set():report['status']='cancelled';break
                if read(ROOT/'active.json',{}).get('id') or psutil.virtual_memory().available<2**30:
                    report['status']='failed';report['error']='No se continúa: la memoria no se ha liberado o queda menos de 1 GiB disponible.';break
            write(path,report)
        if report['status']=='running':report['status']='passed' if report['rows'] and all(r['status']=='passed' for r in report['rows']) else 'partial'
    finally:
        try:unload_all();write(ROOT/'active.json',{})
        except Exception as e:report.update(status='failed',cleanup_error=str(e))
        report['finished']=time.time();write(path,report);write(ROOT/'benchmark-series.json',report);event('benchmark-series',{'id':group,'status':report['status'],'model':mid})
    passed=sum(r['status']=='passed' for r in report['rows']);report['message']='Evaluación secuencial: '+str(passed)+'/'+str(len(engines))+' servidores con resultado válido. Memoria liberada.'
    if report['status'] in ('cancelled','failed'):report['message']='Evaluación '+report['status']+'. Los resultados ya obtenidos se conservan.'
    return report


def functional(engine,public,strict=True):
    base=api_base(engine);headers=model_headers(engine)
    started=time.monotonic();proof=http(base,'/v1/chat/completions',{'model':public,'messages':[{'role':'user','content':'Responde únicamente el resultado de 17 multiplicado por 19.'}],'max_tokens':1024 if engine in ('mirai','lmstudio') else 128,'temperature':0,'stream':False,**({} if engine=='mirai' else {'enable_thinking':False} if engine=='exo' else {'chat_template_kwargs':{'enable_thinking':False}})},timeout=240,headers=headers)
    answer=proof.get('choices',[{}])[0].get('message',{}).get('content','') or ''
    if strict and not re.search(r'\b323\b',answer):raise RuntimeError('Aritmética incorrecta: '+answer[:100])
    arithmetic_s=time.monotonic()-started
    if engine=='fm':
        began=time.monotonic();spanish=http(base,'/v1/chat/completions',{'model':public,'messages':[{'role':'user','content':'Escribe dos frases en español sobre el mar.'}],'max_tokens':128,'stream':False},timeout=240,headers=headers)
        text=(spanish.get('choices') or [{}])[0].get('message',{}).get('content','')
        if not text:raise RuntimeError('Apple FM no produjo texto.')
        return {'arithmetic':answer,'arithmetic_s':arithmetic_s,'spanish_stream':text,'stream_mode':'Respuesta nativa completa; la pasarela adapta a SSE','total_s':time.monotonic()-began}
    body={'model':public,'messages':[{'role':'user','content':'Escribe dos frases en español sobre el mar. Empieza directamente.'}],'max_tokens':1024 if engine in ('mirai','lmstudio') else 128,'temperature':0,'stream':True,'stream_options':{'include_usage':True},**({} if engine=='mirai' else {'enable_thinking':False} if engine=='exo' else {'chat_template_kwargs':{'enable_thinking':False}})}
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**headers});start_=time.monotonic();first=None;chunks=[];usage={};timings={}
    with OPENER.open(req,timeout=240) as response:
        for line in response:
            if not line.startswith(b'data:') or line[5:].strip()==b'[DONE]':continue
            d=json.loads(line[5:].strip());choice=(d.get('choices') or [{}])[0];delta=choice.get('delta',{});text=delta.get('content','')
            if text or delta.get('reasoning_content'):first=first or time.monotonic()
            if text:chunks.append(text)
            usage=d.get('usage') or usage;timings=d.get('timings') or timings
    if not chunks:raise RuntimeError('Streaming sin texto de respuesta.')
    total=time.monotonic()-start_;tokens=usage.get('completion_tokens')
    return {'arithmetic':answer,'arithmetic_s':arithmetic_s,'spanish_stream':''.join(chunks),'ttft_s':None if first is None else first-start_,'ttft_basis':'Primer delta generado, incluido razonamiento','total_s':total,'usage':usage,'timings':timings,'generation_tok_s':timings.get('predicted_per_second') or timings.get('decode_tps') or (tokens/max(.001,total-(first-start_)) if tokens and first else None)}

OPTIMIZABLE_ENGINES={'llama','strata-llama','vllm','mirai'}

def optimize_all(value,cancel,progress):
    model=evaluation_model(value);mid=model['id'];engines=list(dict.fromkeys(model['engines']))
    group='opt-series-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
    report={'id':group,'model':mid,'context':model['context'],'started':time.time(),'status':'running','order':engines,'rows':[],
            'optimization_engines':[s for s in engines if s in OPTIMIZABLE_ENGINES],
            'evaluation_only_engines':[s for s in engines if s not in OPTIMIZABLE_ENGINES]}
    path=ROOT/'results'/(group+'.json')
    def save():
        write(path,report);write(ROOT/'optimization-series.json',report)
    save()
    try:
        for index,engine in enumerate(engines):
            if cancel.is_set():report['status']='cancelled';break
            mode='optimize' if engine in OPTIMIZABLE_ENGINES else 'evaluate'
            prefix=str(index+1)+'/'+str(len(engines))+' · '+NAMES.get(engine,engine)+' · '
            row={'engine':engine,'mode':mode,'status':'running'};report['rows'].append(row);save()
            progress(prefix+('Optimización automática' if mode=='optimize' else 'Evaluación; este motor no admite ajuste automático'))
            try:
                unload_all();write(ROOT/'active.json',{})
                if psutil.virtual_memory().available<2**30:raise RuntimeError('Menos de 1 GiB disponible; no se inicia otro motor.')
                result=(optimize if mode=='optimize' else benchmark)(mid,engine,cancel,lambda message:progress(prefix+message))
                evidence=result['report'] if mode=='optimize' else result
                row.update(status=evidence['status'],result_id=evidence['id'],selected=evidence.get('selected'))
            except Exception as e:row.update(status='cancelled' if cancel.is_set() else 'failed',error=str(e))
            finally:
                try:unload_all();write(ROOT/'active.json',{})
                except Exception as e:
                    report.update(status='failed',cleanup_error=str(e));row.update(status='failed',cleanup_error=str(e))
                save()
            if report['status']=='failed':break
            if cancel.is_set():report['status']='cancelled';break
            if psutil.virtual_memory().available<2**30:
                report.update(status='failed',error='Se detiene el recorrido por margen de memoria insuficiente.');break
        if report['status']=='running':
            valid=sum(row['status']=='passed' for row in report['rows'])
            report['status']='passed' if valid==len(engines) and valid else 'partial' if valid else 'failed'
    except Exception as e:report.update(status='cancelled' if cancel.is_set() else 'failed',error=str(e))
    finally:
        try:unload_all();write(ROOT/'active.json',{})
        except Exception as e:report.update(status='failed',cleanup_error=str(e))
        report['finished']=time.time();save();event('optimization-series',{'id':group,'model':mid,'status':report['status']})
    optimized=sum(r['mode']=='optimize' and r['status']=='passed' for r in report['rows'])
    evaluated=sum(r['mode']=='evaluate' and r['status']=='passed' for r in report['rows'])
    report['message']='Recorrido '+report['status']+': '+str(optimized)+' motores optimizados y '+str(evaluated)+' evaluados sin ajuste. Los perfiles válidos se conservan.'
    if report.get('cleanup_error'):report['message']+=' No se confirmó la liberación de memoria: '+report['cleanup_error']
    else:report['message']+=' Modelos descargados de memoria.'
    save();return report

def optimize(mid,engine,cancel,progress):
    chosen=evaluation_model(mid);mid=chosen['id']
    if engine=='mirai':return optimize_mirai(mid,cancel,progress)
    m=get_model(mid)
    if engine not in ('llama','strata-llama','vllm'):
        raise RuntimeError('La búsqueda de parámetros está disponible en Llama y vLLM. Para este motor usa Evaluar; no se cambian opciones que no admite.')
    prior=read(ROOT/'profiles.json',{});key=engine+'/'+mid;original=prior.get(key)
    variants=[{'threads':4,'batch':512,'ubatch':128},{'threads':6,'batch':1024,'ubatch':128},{'threads':8,'batch':2048,'ubatch':256}] if engine!='vllm' else [{'batch':256},{'batch':512},{'batch':1024}]
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');report={'id':'opt-'+stamp,'model':mid,'engine':engine,'engine_version':installed(engine,SOURCES[engine][1]),'fingerprint':fingerprint(m),'started':time.time(),'context':m['context'],'candidates':[],'status':'running','method':'pp512/tg128 x3 + funcional' if engine!='vllm' else 'Streaming x3 + funcional; mismo contexto'}
    unload_all();swap=psutil.swap_memory().used
    try:
        for i,params in enumerate(variants):
            if cancel.is_set():raise RuntimeError('Optimización cancelada.')
            progress('Ensayo '+str(i+1)+'/'+str(len(variants))+' · '+json.dumps(params))
            candidate={'parameters':params,'status':'running'};report['candidates'].append(candidate)
            try:
                unload_all();profiles=read(ROOT/'profiles.json',{});profiles[key]={**params,'fingerprint':report['fingerprint'],'context':m['context'],'engine_signature':engine_signature(engine)};write(ROOT/'profiles.json',profiles)
                if engine!='vllm':
                    # Both llama engines consume the same generated presets.
                    write(ROOT/'profiles.json',profiles);save_presets(engine=engine)
                    binary=LROOT/'optimizacion-m4-pro/bin/llama-bench' if engine=='llama' else STRATA/'engines/llama-b11707/llama-bench'
                    out=ROOT/'results'/(report['id']+'-'+str(i)+'.raw.json');err=out.with_suffix('.log')
                    args=[str(binary),'-m',m['path'],'-p','512','-n','128','-r','3','-t',str(params['threads']),'-b',str(params['batch']),'-ub',str(params['ubatch']),'-ngl','99','-fa','1','-o','json']
                    with out.open('w') as a,err.open('w') as b:
                        proc=subprocess.Popen(args,stdout=a,stderr=b,env={**os.environ,'GGML_METAL_NO_RESIDENCY':'1'},start_new_session=True);beg=time.monotonic();minimum=psutil.virtual_memory().available
                        while proc.poll() is None:
                            minimum=min(minimum,psutil.virtual_memory().available)
                            if cancel.is_set() or time.monotonic()-beg>600 or psutil.swap_memory().used-swap>512*2**20:
                                proc.terminate();proc.wait(timeout=20);raise RuntimeError('Ensayo cancelado por límite de recursos o tiempo.')
                            time.sleep(.5)
                    if proc.returncode:raise RuntimeError('El motor rechazó el ensayo; no se calcula velocidad válida.')
                    raw=read(out,[]);rates=[v['avg_ts'] for v in raw if v.get('avg_ts',0)>0]
                    candidate.update(raw=raw,min_available_gib=minimum/2**30,min_required_gib=1)
                    if len(rates)!=2 or minimum<1*2**30:raise RuntimeError('Ensayo sin 1 GiB de margen de memoria o sin ambas tasas válidas.')
                    candidate['score']=math.sqrt(rates[0]*rates[1])
                began=time.monotonic();active=load(mid,engine);candidate['load_s']=time.monotonic()-began
                runs=[functional(engine,active['public_model']) for _ in range(3 if engine=='vllm' else 1)]
                candidate['functional']=runs
                if engine=='vllm':
                    rates=[r['generation_tok_s'] for r in runs if r.get('generation_tok_s')]
                    if len(rates)!=3:raise RuntimeError('El motor no publicó tokens; no se estima una tasa con fragmentos SSE.')
                    candidate['score']=statistics.median(rates)
                candidate['status']='passed'
            except Exception as e:candidate.update(status='cancelled' if cancel.is_set() else 'failed',error=str(e))
            finally:unload_all()
        valid=[x for x in report['candidates'] if x['status']=='passed']
        if cancel.is_set():raise RuntimeError('Optimización cancelada.')
        if not valid:raise RuntimeError('Ninguna configuración superó todas las comprobaciones.')
        best=max(valid,key=lambda x:x['score']);report.update(status='passed',selected=best['parameters'],score=best['score'])
        profiles=read(ROOT/'profiles.json',{});profiles[key]={**best['parameters'],'fingerprint':report['fingerprint'],'context':m['context'],'validated':time.time(),'engine_signature':engine_signature(engine),'engine_version':report['engine_version'],'evidence':report['id']}
        write(ROOT/'profiles.json',profiles)
        if engine!='vllm':save_presets(engine=engine)
        load(mid,engine)
    except Exception as e:
        report.update(status='cancelled' if cancel.is_set() else 'failed',error=str(e));write(ROOT/'profiles.json',prior);save_presets();raise
    finally:
        report['finished']=time.time();history=read(ROOT/'optimizations.json',[]);history.insert(0,report);write(ROOT/'optimizations.json',history);write(ROOT/'results'/(report['id']+'.json'),report)
    return {'message':'Perfil más rápido de los ensayos válidos guardado. Contexto conservado: '+str(m['context']),'report':report}

def optimize_mirai(mid,cancel,progress):
    m=get_model(mid)
    if 'mirai' not in m['engines']:raise ValueError('Selecciona un checkpoint nativo de Mirai.')
    prior=read(ROOT/'profiles.json',{});key='mirai/'+mid;stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    report={'id':'opt-mirai-'+stamp,'model':mid,'engine':'mirai','context':m['context'],'fingerprint':fingerprint(m),'started':time.time(),'method':'Caché de prefijo activada/desactivada · calentamiento + 3 continuaciones idénticas','candidates':[],'status':'running'}
    swap=psutil.swap_memory().used
    try:
        for cache in (False,True):
            if cancel.is_set():raise RuntimeError('Optimización cancelada.')
            progress('Mirai · caché de prefijo '+('activada' if cache else 'desactivada'))
            unload_all();profiles=read(ROOT/'profiles.json',{});profiles[key]={'prefix_cache':cache,'fingerprint':fingerprint(m),'context':m['context'],'engine_signature':engine_signature('mirai')};write(ROOT/'profiles.json',profiles)
            candidate={'parameters':{'prefix_cache':cache},'status':'running','runs':[]};report['candidates'].append(candidate)
            try:
                began=time.monotonic();active=load(mid,'mirai');candidate['load_s']=time.monotonic()-began;candidate['functional']=functional('mirai',active['public_model'])
                for i in range(4):
                    if cancel.is_set() or psutil.swap_memory().used-swap>512*2**20 or psutil.virtual_memory().available<1*2**30:raise RuntimeError('Ensayo detenido por cancelación o margen de memoria.')
                    messages=[{'role':'system','content':('Un faro ayuda a navegar. El mar tiene olas y las mareas cambian durante el día. '*40)+'Responde de forma breve en español.'},{'role':'user','content':'¿Cuánto es 17 por 19? Responde solo el número.'}]
                    base='http://127.0.0.1:8000';first=http(base,'/v1/chat/completions',{'model':active['public_model'],'messages':messages,'max_tokens':1024,'temperature':0},timeout=240)
                    answer=first['choices'][0]['message']
                    if not re.search(r'\b323\b',answer.get('content','') or ''):raise RuntimeError('La comprobación aritmética no fue correcta.')
                    messages+=[answer,{'role':'user','content':'Escribe dos frases en español sobre el faro.'}]
                    began=time.monotonic();last=http(base,'/v1/chat/completions',{'model':active['public_model'],'messages':messages,'max_tokens':1024,'temperature':0},timeout=240);wall=time.monotonic()-began
                    if not (last['choices'][0]['message'].get('content') or '').strip():raise RuntimeError('La continuación no produjo texto final.')
                    if i:candidate['runs'].append({'wall_s':wall,'usage':last.get('usage',{}),'finish_reason':last['choices'][0].get('finish_reason')})
                    progress('Mirai · '+('caché' if cache else 'sin caché')+' · '+str(i)+'/3 repeticiones')
                candidate['median_s']=statistics.median(x['wall_s'] for x in candidate['runs']);candidate['score']=1/candidate['median_s'];candidate['status']='passed'
            except Exception as e:candidate.update(status='failed',error=str(e))
            finally:unload_all()
        if cancel.is_set():raise RuntimeError('Optimización cancelada.')
        valid=[x for x in report['candidates'] if x['status']=='passed']
        if not valid:raise RuntimeError('Ningún perfil de Mirai superó las comprobaciones. Se conserva el perfil anterior.')
        best=max(valid,key=lambda x:x['score']);report.update(status='passed',selected=best['parameters'])
        profiles=read(ROOT/'profiles.json',{});profiles[key]={**best['parameters'],'fingerprint':fingerprint(m),'context':m['context'],'engine_signature':engine_signature('mirai'),'engine_version':installed('mirai','/usr/local/bin/mirai'),'validated':time.time(),'evidence':report['id']};write(ROOT/'profiles.json',profiles)
        load(mid,'mirai')
    except Exception as e:report.update(status='failed',error=str(e));write(ROOT/'profiles.json',prior);raise
    finally:
        report['finished']=time.time();history=read(ROOT/'optimizations.json',[]);history.insert(0,report);write(ROOT/'optimizations.json',history);write(ROOT/'results'/(report['id']+'.json'),report)
    return {'message':'Mirai verificado y perfil de caché seleccionado para continuaciones. No se modifican los pesos ni el contexto.','report':report}

def restore_profile(mid,engine):
    profiles=read(ROOT/'profiles.json',{});profiles.pop(engine+'/'+mid,None)
    # Profiles of other engines remain independent.
    write(ROOT/'profiles.json',profiles);save_presets()
    if read(ROOT/'active.json',{}).get('id')==mid:stop(engine)
    return {'message':'Restaurados los parámetros base; vuelve a cargar el modelo.'}


def agent_checks(cancel,progress,only=None):
    import yaml
    scope=only if isinstance(only,list) else [only] if only else []
    previous=read(ROOT/'agent-checks.json',{}) if only else {}
    report={'started':time.time(),'rows':[r for r in previous.get('rows',[]) if r.get('engine') not in scope],'method':'Dos CLI reales → pasarela autenticada → motor local; aritmética 17×19'}
    write(ROOT/'agent-checks.json',report)
    engines=[s for s in ('llama','strata-llama','mirai','vllm','mlx','omlx','lmstudio','unsloth','fm','strata','exo') if not only or s in scope]
    for engine in engines:
        if cancel.is_set():break
        candidates=[m for m in models() if engine in m['engines'] and 'mmproj' not in m['label'].lower()]
        candidates.sort(key=lambda m:(not (m.get('max_context',m['context'])>=65536),m['bytes']))
        # Use an instruct checkpoint without a separate reasoning budget for the access probe.
        if engine=='mirai':candidates.sort(key=lambda m:(not ('LFM2.5-2.6B' in m['label']),m['bytes']))
        if engine=='exo':candidates.sort(key=lambda m:m['bytes'])
        if not candidates:
            report['rows'].append({'engine':engine,'status':'blocked','reason':'Sin modelo compatible verificable o sin enlace exclusivo a loopback.'});write(ROOT/'agent-checks.json',report);continue
        m=candidates[0]
        if m.get('max_context',m['context'])>=65536 and engine in ('llama','strata-llama','vllm','mlx','omlx','lmstudio','unsloth'):
            catalog=read(ROOT/'catalog.json',{})
            for row in catalog['models']:
                if row['id']==m['id']:row['context']=65536
            write(ROOT/'catalog.json',catalog);contexts=read(ROOT/'contexts.json',{});contexts[m['id']]=65536;write(ROOT/'contexts.json',contexts);m=get_model(m['id']);save_presets()
        alias=engine+'/'+m['id'];progress('Comprobando '+NAMES[engine]+' · '+m['label'])
        try:
            with lock():active=load(m['id'],engine)
            proof=functional(engine,active['public_model'],strict=False)
        except Exception as e:
            for agent in ('opencode','hermes'):report['rows'].append({'engine':engine,'model':m['id'],'agent':agent,'status':'failed','error':str(e)})
            write(ROOT/'agent-checks.json',report);continue
        for agent in ('opencode','hermes'):
            if cancel.is_set():break
            if agent=='hermes' and m['context']<64000:
                report['rows'].append({'engine':engine,'agent':agent,'model':m['id'],'status':'blocked','reason':'Hermes exige 64000 tokens; este perfil anuncia '+str(m['context'])+'.'});write(ROOT/'agent-checks.json',report);continue
            progress(NAMES[agent]+' → '+NAMES[engine]);qa=ROOT/'qa'/agent;qa.mkdir(parents=True,mode=0o700,exist_ok=True)
            token=(ROOT/'token').read_text(encoding='utf-8');base='http://127.0.0.1:'+str(CONTROL_PORT)+'/v1';prompt='Responde únicamente el resultado de 17 multiplicado por 19.'
            env={k:v for k,v in os.environ.items() if not any(x in k for x in ('API_KEY','TOKEN','BASE_URL'))};env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',NO_PROXY='127.0.0.1,localhost')
            row={'engine':engine,'engine_version':installed(engine,SOURCES.get(engine,(None,None,None))[1]),'agent':agent,'agent_version':installed(agent,SOURCES[agent][1]),'model':m['id'],'context':m['context'],'functional':proof,'started':time.time()}
            if agent=='opencode':
                conf={'providers':{'ia-local':{'package':'@opencode/ai/providers/openai-compatible','settings':{'baseURL':base,'apiKey':token},'models':{alias:{'limit':{'context':m['context'],'output':1024 if engine=='mirai' else 256},'capabilities':{'tools':False}}}}},'model':'ia-local/'+alias,'agents':{'probe':{'name':'Prueba local','description':'Consulta sintética sin herramientas','mode':'primary','system':'Responde brevemente. No utilices herramientas.','permissions':[{'action':a,'resource':'*','effect':'deny'} for a in ('shell','edit','read','glob','grep','subagent','webfetch','websearch','skill')]}},'policies':[{'action':'provider.use','resource':'*','effect':'deny'},{'action':'provider.use','resource':'ia-local','effect':'allow'}],'update':'disable','snapshots':False,'websearch':False}
                write(qa/'opencode.json',conf);directory=qa/'config/opencode';directory.mkdir(parents=True,exist_ok=True);write(directory/'opencode.json',conf)
                env.update(XDG_CONFIG_HOME=str(qa/'config'),XDG_DATA_HOME=str(qa/'data'),XDG_CACHE_HOME=str(qa/'cache'),OPENCODE_CONFIG=str(qa/'opencode.json'))
                args=[HOME/'.opencode/bin/opencode','run','--standalone','--agent','probe','-m','ia-local/'+alias,'--format','json',prompt]
            else:
                conf={'model':{'provider':'ia-local','default':alias,'base_url':base,'api_mode':'chat_completions','context_length':m['context'],'max_tokens':1024 if engine=='mirai' else 256},'providers':{'ia-local':{'base_url':base,'api_key':token,'transport':'chat_completions','context_length':m['context']}},'fallback_models':[],'agent':{'max_turns':1},'plugins':{'enabled':[]},'display':{'interface':'cli'}}
                (qa/'config.yaml').write_text(yaml.safe_dump(conf),encoding='utf-8');os.chmod(qa/'config.yaml',0o600);env.update(HERMES_HOME=str(qa),HERMES_SKIP_UPDATE_CHECK='1')
                args=[HOME/'.local/bin/hermes','-z',prompt,'--provider','ia-local','-m',alias,'--ignore-rules','-t','bot_room','--usage-file',qa/'usage.json']
            try:
                p=subprocess.run(list(map(str,args)),cwd=qa,env=env,capture_output=True,text=True,timeout=240)
                output=p.stdout+'\n'+p.stderr
                if agent=='opencode':
                    entries=[]
                    for line in p.stdout.splitlines():
                        try:d=json.loads(line)
                        except ValueError:continue
                        if d.get('type')=='text':entries.append(d.get('part',{}).get('text',''))
                    answer=''.join(entries)
                else:answer=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',p.stdout)
                row.update(connection_passed=bool(p.returncode==0 and answer.strip()),arithmetic_passed=bool(re.search(r'\b323\b',answer)),status='passed' if p.returncode==0 and re.search(r'\b323\b',answer) else 'quality-failed' if p.returncode==0 and answer.strip() else 'failed',returncode=p.returncode,answer=answer[-1500:].replace(token,'[privado]'),wall_s=time.time()-row['started'])
                if row['status']=='failed':row['error']=output[-1800:].replace(token,'[privado]')
                (qa/'cli.log').write_text(output,encoding='utf-8');os.chmod(qa/'cli.log',0o600)
            except Exception as e:row.update(status='failed',error=str(e))
            # Test credentials are not retained in the synthetic evidence.
            for configfile in (qa/'opencode.json',qa/'config/opencode/opencode.json',qa/'config.yaml'):configfile.unlink(missing_ok=True)
            report['rows'].append(row);write(ROOT/'agent-checks.json',report)
        try:
            with lock():unload_all()
        except Exception as e:report['rows'].append({'engine':engine,'status':'failed','error':'No se liberó el modelo: '+str(e)})
    report['finished']=time.time();report['status']='cancelled' if cancel.is_set() else 'passed' if report['rows'] and all(r['status']=='passed' for r in report['rows']) else 'attention';write(ROOT/'agent-checks.json',report)
    return {'message':'Pruebas terminadas: '+str(sum(r['status']=='passed' for r in report['rows']))+' correctas de '+str(len(report['rows']))+'. Revisa los fallos y las limitaciones en Evaluación.','report':report}


def configure_cloud():
    import yaml
    start('freellmapi')
    dbpath=ROOT/'freellmapi-data.sqlite'
    with contextlib.closing(sqlite3.connect(dbpath)) as c:row=c.execute("SELECT value FROM settings WHERE key='unified_api_key'").fetchone()
    if not row:raise RuntimeError('FreeLLMAPI no confirmó su clave de cliente.')
    key=row[0];base='http://127.0.0.1:'+str(PORTS['freellmapi'])+'/v1';stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=ROOT/'backups'/('cloud-'+stamp);backup.mkdir()
    oc=HOME/'.config/opencode/opencode.json';hc=HOME/'.hermes/config.yaml';shutil.copy2(oc,backup/'opencode.json');shutil.copy2(hc,backup/'config.yaml')
    c=read(oc,{});c.setdefault('providers',{})['freellmapi']={'name':'FreeLLMAPI · nube','package':'@opencode/ai/providers/openai-compatible','settings':{'baseURL':base,'apiKey':key},'models':{'auto':{'name':'Nube · selección FreeLLMAPI'},'auto:fast':{'name':'Nube · FreeLLMAPI rápido'}}}
    if isinstance(c.get('enabled_providers'),list):
        for provider in ('openai','openai-codex','freellmapi'):
            if provider not in c['enabled_providers']:c['enabled_providers'].append(provider)
    # No change to defaults or to any OpenAI credential.
    d=yaml.safe_load(hc.read_text(encoding='utf-8'));d.setdefault('providers',{})['freellmapi']={'base_url':base,'api_key':key,'transport':'chat_completions','discover_models':True}
    text=yaml.safe_dump(d,allow_unicode=True,sort_keys=False);write(oc,c);tmp=hc.with_suffix('.yaml.ia-local.tmp');tmp.write_text(text,encoding='utf-8');os.chmod(tmp,0o600);tmp.replace(hc)
    event('cloud-configured',{'providers':['OpenAI conservado','FreeLLMAPI añadido'],'backup':str(backup)})
    return {'message':'FreeLLMAPI añadido sin cambiar el proveedor predeterminado. OpenAI permanece disponible. Abre FreeLLMAPI para añadir las claves de los proveedores de nube.'}


def rollback_update(s):
    if s not in ('opencode','hermes'):raise ValueError('Recuperación automática no disponible para este instalador.')
    if port_open(PORTS[s]):raise RuntimeError('Detén '+NAMES[s]+' antes de restaurar su versión.')
    if s=='hermes' and registered('ai.hermes.gateway'):raise RuntimeError('Detén también el gateway de Hermes antes de restaurar el código.')
    candidates=[]
    for folder in (ROOT/'backups').iterdir():
        data=read(folder/'restore.json',{})
        if data.get('service')==s:candidates.append((folder,data))
    if not candidates:raise RuntimeError('No hay una actualización de '+NAMES[s]+' hecha desde IA Local que se pueda deshacer.')
    folder,record=sorted(candidates,key=lambda x:x[0].name)[-1]
    safety=ROOT/'backups'/('before-rollback-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));safety.mkdir()
    if s=='opencode':
        exe=HOME/'.opencode/bin/opencode';config=HOME/'.config/opencode/opencode.json';shutil.copy2(exe,safety/'opencode');shutil.copy2(config,safety/'opencode.json');shutil.copy2(folder/'opencode',exe);shutil.copy2(folder/'opencode.json',config)
    else:
        repo=HOME/'.hermes/hermes-agent'
        if run(['git','-C',repo,'status','--porcelain']):raise RuntimeError('Hay cambios locales en Hermes. No se modifica el checkout.')
        commit=record.get('commit','')
        if not re.fullmatch('[a-f0-9]{40}',commit):raise RuntimeError('La copia no contiene un commit válido.')
        write(safety/'current.json',{'commit':run(['git','-C',repo,'rev-parse','HEAD'])});shutil.copy2(HOME/'.hermes/config.yaml',safety/'config.yaml')
        run(['git','-C',repo,'checkout','--detach',commit],90);shutil.copy2(folder/'config.yaml',HOME/'.hermes/config.yaml')
    version=installed(s,SOURCES[s][1]);event('rollback-update',{'service':s,'restored':str(folder),'safety':str(safety),'version':version})
    return {'message':'Versión anterior restaurada: '+version+'. La versión sustituida también tiene copia de recuperación.'}
