#!/usr/bin/env python3
'Loopback authenticated supervisor, serialized jobs and OpenAI-compatible routing. Background state/maintenance threads never imply model readiness. The optional portable owner UI is enabled only by its launcher.'
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from operations import *
import collections, urllib.parse
import integrations,remote_servers,external_providers

JOBS={};JOB_LOCK=threading.Lock();CANCEL=threading.Event();LIVE={'state':'En espera','tokens':0,'tok_s':None,'ttft_ms':None,'requests':0,'errors':0};SAMPLES=collections.deque(maxlen=90)
CACHE={};SHUTDOWN=False
HOST_REQUESTS={};HOST_GUARD=threading.RLock()
def pending_gpu():return any(r['command']=='gpu' and r['state'] in ('queued','running') for r in HOST_REQUESTS.values())
def host_request(command,body,actor):
    if command not in ('gpu','authorize-ssd'):raise ValueError('Operación nativa no permitida.')
    with lock(),HOST_GUARD:
        if any(r['state'] in ('queued','running') for r in HOST_REQUESTS.values()):raise RuntimeError('Ya hay una solicitud esperando confirmación en el Mac.')
        if command=='gpu' and (any(j['state']=='running' for j in JOBS.values()) or read(ROOT/'active.json',{}).get('id')):raise RuntimeError('Termina la operación actual y descarga los modelos antes de ajustar la memoria GPU.')
        if command=='gpu' and (not isinstance(body.get('value'),int) or body['value'] not in (0,) and not 1024<=body['value']<=22528):raise ValueError('Valor de memoria no permitido.')
        rid=secrets.token_hex(16);HOST_REQUESTS[rid]={'id':rid,'command':command,'value':body.get('value'),'actor':actor,'state':'queued','time':time.time()}
        return {'host_job':rid,'message':'Esperando confirmación en la app IA Local del Mac…'}
def host_result(rid,actor=None):
    r=HOST_REQUESTS.get(rid)
    if not r or actor is not None and r['actor']!=actor:raise ValueError('Solicitud nativa desconocida.')
    if r['state']=='queued' and time.time()-r['time']>180:r.update(state='done',result={'error':'Abre IA Local en el Mac y vuelve a solicitar la operación.'})
    return {'state':r['state'],'result':r.get('result')}
def host_next():
    with HOST_GUARD:
        for rid,r in HOST_REQUESTS.items():
            host_result(rid)
            if r['state']=='queued':r['state']='running';return {'request':{k:r[k] for k in ('id','command','value')}}
    return {'request':None}
def host_complete(body):
    with HOST_GUARD:
        r=HOST_REQUESTS.get(body.get('id'))
        if not r or r['state']!='running':raise ValueError('Solicitud nativa no vigente.')
        r.update(state='done',result=body.get('result',{'error':'Sin resultado nativo.'}))
    return {'ok':True}
def job(action,value=None,engine=None,actor='Mac'):
    independent=(action in ('start','stop') and value in ('hermes','opencode')) or action in ('agents-start','agents-stop','gateway-start','gateway-stop')
    with JOB_LOCK:
        if action=='cancel':
            if any(j['state']=='running' and j['action'] in ('reset-application','restore-reset') for j in JOBS.values()):return {'message':'El restablecimiento o recuperación termina el paso actual para conservar la copia. Espera a que finalice.'}
            if any(j['state']=='running' and j['action'] in ('update','rollback-update') for j in JOBS.values()):return {'message':'El instalador oficial ya está en marcha. Se deja terminar para conservar una instalación coherente; existe copia de recuperación.'}
            CANCEL.set();return {'message':'Cancelación solicitada.'}
        if any(j['state']=='running' and j['action'] in ('reset-application','restore-reset') for j in JOBS.values()):raise RuntimeError('Espera a que termine el restablecimiento o recuperación antes de cambiar servicios.')
        if pending_gpu():raise RuntimeError('Confirma o cancela la autorización de memoria GPU pendiente en el Mac.')
        if any(j['state']=='running' and (not independent or j.get('independent')) for j in JOBS.values()):raise RuntimeError('Hay una operación en curso. Puedes arrancar o detener los agentes; espera para cambiar de motor o ejecutar otra prueba.')
        jid=secrets.token_hex(6);JOBS[jid]={'id':jid,'action':action,'state':'running','message':'Preparando…','target':value if isinstance(value,str) else None,'engine':engine,'time':time.time(),'independent':independent,'actor':actor}
        if not independent:CANCEL.clear()
    def progress(message):
        JOBS[jid]['message']=message
        for service,name in NAMES.items():
            if ' · '+name+' · ' in message:JOBS[jid]['engine']=service;break
    def work():
        try:
            if action=='integration-assist':
                import integration_assistant
                result=integration_assistant.propose(value,CANCEL,progress)
                JOBS[jid].update(state='done',message=result['message'],result=result);return
            if action=='agent-checks':
                result=agent_checks(CANCEL,progress,value)
                JOBS[jid].update(state='done',message='Pruebas completadas',result=result);return
            with lock('agents' if independent else 'lifecycle'):
                if action=='start':start(value);result={'message':NAMES[value]+' iniciado o en espera de modelo.'}
                elif action=='stop':stop(value);result={'message':NAMES[value]+' detenido.'}
                elif action in ('start-all','stop-all','agents-start','agents-stop'):
                    group=[s for s in available_services() if s in ('opencode','hermes') or (integrations.definition(s) or {}).get('kind')=='agent'] if action.startswith('agents') else [s for s in available_services() if action=='stop-all' or not s.startswith('cloud-')]
                    if action=='start-all':unload_all()
                    errors=[];completed=[]
                    for s in group:
                        if not independent and CANCEL.is_set():break
                        progress(('Deteniendo ' if 'stop' in action else 'Arrancando ')+NAMES[s])
                        try:(stop if 'stop' in action else start)(s);completed.append(NAMES[s])
                        except Exception as e:errors.append(NAMES[s]+': '+str(e))
                    result={'message':'Completados: '+', '.join(completed),'warnings':errors}
                elif action=='reset-application':
                    import reset_state
                    result=reset_state.detach(value,progress)
                elif action=='restore-reset':
                    import reset_state
                    result=reset_state.restore(progress)
                elif action=='integration-attach-known':
                    import reset_state
                    result=reset_state.attach_known(value)
                elif action=='external-register':result=external_providers.register(value)
                elif action=='external-remove':result=external_providers.unregister(value)
                elif action=='external-import-freellmapi':result=external_providers.import_freellmapi()
                elif action=='external-inventory':result={'message':str(external_providers.inventory(value))+' modelos recibidos.'}
                elif action=='integration-scan':result=integrations.scan()
                elif action=='integration-register':result=integrations.register(value)
                elif action=='integration-remove':result=integrations.unregister(value)
                elif action=='remote-register':result=remote_servers.register(value)
                elif action=='remote-remove':result=remote_servers.unregister(value)
                elif action=='scan':result=discover()
                elif action=='load':progress('Liberando otros modelos y cargando…');result=load(value,engine)
                elif action=='unload':unload_all();write(ROOT/'active.json',{});result={'message':'Modelos liberados; los motores que requieren pesos se han detenido.'}
                elif action=='benchmark':result=benchmark(value,engine,CANCEL,progress)
                elif action=='benchmark-all':result=benchmark_all(value,CANCEL,progress)
                elif action=='optimize':result=optimize(value,engine,CANCEL,progress)
                elif action=='optimize-all':result=optimize_all(value,CANCEL,progress)
                elif action=='restore-profile':result=restore_profile(value,engine)
                elif action=='server-check':
                    progress('Cargando y comprobando '+NAMES[engine])
                    began=time.monotonic();active=load(value,engine);load_s=time.monotonic()-began
                    result={'message':NAMES[engine]+' comprobado: respuesta y streaming recibidos.','diagnostic':{'engine':engine,'active':active,'load_s':load_s,**functional(engine,active['public_model'])}}
                elif action=='logs':
                    logs={}
                    for s in PORTS:
                        p=ROOT/'logs'/(s+'.log')
                        if p.exists():
                            text=p.read_bytes()[-24000:].decode('utf-8',errors='replace')
                            token=(ROOT/'token').read_text();text=text.replace(token,'[privado]')
                            text='\n'.join('[Línea con credenciales omitida]' if re.search(r'api[_ -]?key|authorization|bearer|password|license|setup.?code|auth/connect|sk-[a-zA-Z0-9]|freellmapi-[a-f0-9]{20,}',line,re.I) else line for line in text.splitlines()[-100:])
                            logs[s]=text
                    result={'message':'Registros disponibles; líneas con credenciales omitidas.','diagnostic':logs}
                elif action=='set-context':
                    m=get_model(value['id']);n=int(value['context'])
                    if n not in (4096,8192,32768,65536) or n>m.get('max_context',m['context']):raise ValueError('El modelo no anuncia ese contexto. Se conserva el perfil anterior.')
                    if read(ROOT/'active.json',{}).get('id')==m['id']:unload_all()
                    contexts=read(ROOT/'contexts.json',{});contexts[m['id']]=n;write(ROOT/'contexts.json',contexts)
                    catalog=read(ROOT/'catalog.json',{})
                    for row in catalog['models']:
                        if row['id']==m['id']:row['context']=n
                    write(ROOT/'catalog.json',catalog);save_presets();result={'message':'Contexto guardado: '+str(n)+'. Se verificará al cargar.'}
                elif action=='gpu-set':
                    if sys.platform!='darwin':raise RuntimeError('El límite iogpu solo está disponible en macOS.')
                    import privileged
                    if read(ROOT/'active.json',{}).get('id'):raise RuntimeError('Descarga los modelos antes de ajustar la memoria GPU.')
                    if json.loads(run([HOME/'.lmstudio/bin/lms','ps','--json'],20)):raise RuntimeError('LM Studio conserva un modelo residente. Descárgalo antes de ajustar el límite GPU.')
                    if (probe('exo','/state') or {}).get('instances'):raise RuntimeError('EXO conserva una instancia. Descárgala antes de ajustar el límite GPU.')
                    result=privileged.request(value)
                    confirmed=privileged.request()
                    if confirmed['current']!=result['applied']:raise RuntimeError('La lectura posterior no coincide con el cambio solicitado.')
                    write(ROOT/'gpu-previous.json',{'value':result['previous'],'applied':result['applied'],'time':time.time()});event('gpu-set',{**result,'actor':actor});result['message']='Aplicado y verificado: '+str(result['applied'])+' MiB.'
                elif action=='updates':result=check_updates()
                elif action=='update':
                    import updater
                    result=updater.update(value,progress)
                elif action=='rollback-update':
                    import updater
                    result=updater.rollback(value)
                elif action=='configure-active-agent':result=configure_active_agents(value)
                elif action=='configure-agents':result=configure_agents(value,engine=engine)
                elif action=='configure-cloud':result=configure_cloud()
                elif action=='lan-enable':
                    import lan
                    result=lan.configure(bool(value),job)
                elif action=='user-save':
                    import lan
                    result=lan.save_user(value)
                elif action=='sync-agents':result=configure_agents(value,select=False)
                elif action=='restore-agents':result=restore_agents()
                elif action in ('gateway-start','gateway-stop'):
                    run([HOME/'.local/bin/hermes','gateway','start' if action.endswith('start') else 'stop'],90);result={'message':'Gateway de mensajería de Hermes: operación completada.'}
                elif action=='save-settings':
                    if not isinstance(value,dict):raise ValueError('Ajustes no válidos.')
                    import app_settings
                    current=app_settings.save(value);result={'message':'Preferencias guardadas.'}
                else:raise ValueError('Acción desconocida.')
            JOBS[jid].update(state='done',message='Operación completada',result=result)
        except Exception as e:
            JOBS[jid].update(state='cancelled' if CANCEL.is_set() else 'error',message=str(e));event('operation-error',{'action':action,'message':str(e)})
        finally:JOBS[jid]['finished']=time.time()
    threading.Thread(target=work,daemon=True).start();return {'job':jid}
job.host_request=host_request;job.host_result=host_result

def monitor():
    psutil.cpu_percent()
    while not SHUTDOWN:
        try:
            d=state();d['jobs']=list(JOBS.values())[-12:];d['live']=dict(LIVE);d['samples']=list(SAMPLES);d['host_pending']=any(r['state'] in ('queued','running') for r in HOST_REQUESTS.values())
            for service in d['services']:
                if LIVE.get('engine')==service['id'] and LIVE['state'] in ('Cargando','Generando'):service['state']=LIVE['state']
                for operation in d['jobs']:
                    if operation['state']=='running' and operation['action'] in ('start','load') and (operation.get('engine') or operation.get('target'))==service['id']:service['state']='Cargando' if operation['action']=='load' else 'Arrancando'
            CACHE.clear();CACHE.update(d);SAMPLES.append({'time':time.time(),'cpu':d['cpu'],'gpu':d['gpu'],'tok_s':LIVE['tok_s'] or 0,'ram':d['ram_used']})
        except Exception as e:CACHE['error']='No se pudo completar la muestra de estado.'
        time.sleep(2)

def maintenance():
    last_integration=0;last_scan=0;last_update=(ROOT/'updates.json').stat().st_mtime if (ROOT/'updates.json').exists() else 0;signature=None
    while not SHUTDOWN:
        try:
            cfg=read(ROOT/'settings.json',{})
            if cfg.get('watch_integrations',True) and time.time()-last_integration>cfg.get('integration_scan_seconds',300):
                last_integration=time.time();integrations.scan()
            if cfg.get('watch_models') and time.time()-last_scan>60:
                last_scan=time.time();current=[]
                for m in models():
                    p=Path(m.get('path','/nonexistent'))
                    if p.is_file():current.append((str(p),p.stat().st_size,p.stat().st_mtime))
                # Full periodic scan also discovers new model paths, not only modifications of old ones.
                if time.time()-read(ROOT/'catalog.json',{}).get('time',0)>300:job('scan')
                signature=current
            if cfg.get('daily_updates') and time.time()-last_update>cfg.get('update_hours',24)*3600:
                last_update=time.time();job('updates')
        except Exception:pass
        time.sleep(20)

def forward_chat(handler,body):
    if any(j['state']=='running' and j['action'] in ('reset-application','restore-reset') for j in JOBS.values()):raise RuntimeError('La aplicación se está restableciendo; no admite nuevas consultas durante esa operación.')
    mid=body.get('model','');alias,sep,model=mid.partition('/')
    m=get_model(model if sep else mid);engine=alias if sep and alias in NAMES else m['engines'][0]
    with lock():
        if pending_gpu():raise RuntimeError('Hay una autorización de memoria GPU pendiente en el Mac. No se carga un modelo durante ese ajuste.')
        loading=time.monotonic();LIVE.update(state='Cargando',engine=engine)
        try:active=load(m['id'],engine)
        except Exception:
            LIVE.update(state='En espera');LIVE['errors']+=1;raise
        load_s=time.monotonic()-loading;body=dict(body);body['model']=active['public_model'];body['stream']=bool(body.get('stream'))
        LIVE.update(state='Generando',tokens=0,tok_s=None,ttft_ms=None,started_at=time.time(),load_s=load_s)
        start_=time.monotonic();first=None;count=0;reported_usage={};reported_timings={};success=False;saw_done=False
        upstream_body=dict(body)
        if body['stream'] and engine!='fm':upstream_body['stream_options']={'include_usage':True}
        if engine=='fm':upstream_body['stream']=False
        if engine=='exo' and isinstance(upstream_body.get('chat_template_kwargs',{}).get('enable_thinking'),bool):upstream_body['enable_thinking']=upstream_body['chat_template_kwargs']['enable_thinking']
        req=urllib.request.Request(api_base(engine)+'/v1/chat/completions',data=json.dumps(upstream_body).encode(),headers={'Content-Type':'application/json',**model_headers(engine)})
        try:
            with OPENER.open(req,timeout=300) as r:
                handler.send_response(200);handler.send_header('Content-Type','text/event-stream' if body['stream'] else 'application/json');handler.send_header('Cache-Control','no-store');handler.send_header('Connection','close');handler.end_headers()
                if body['stream'] and engine=='fm':
                    payload=json.load(r);reported_usage=payload.get('usage') or {};reported_timings=payload.get('timings') or {};answer=(payload.get('choices') or [{}])[0].get('message',{}).get('content','');first=time.monotonic();count=payload.get('usage',{}).get('completion_tokens',0)
                    for chunk in ({'id':'fm-buffered','object':'chat.completion.chunk','choices':[{'index':0,'delta':{'role':'assistant','content':answer},'finish_reason':None}]},{'id':'fm-buffered','object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':'stop'}],'usage':payload.get('usage',{})}):handler.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
                    handler.wfile.write(b'data: [DONE]\n\n');handler.wfile.flush()
                    LIVE.update(ttft_ms=(first-start_)*1000)
                elif body['stream']:
                    for line in r:
                        if line.startswith(b'data:') and line[5:].strip()==b'[DONE]':saw_done=True
                        if line.startswith(b'data:') and line[5:].strip()!=b'[DONE]':
                            try:
                                data=json.loads(line[5:].strip())
                                if data.get('error'):raise RuntimeError('El motor interrumpió el streaming. No se considera una inferencia correcta.')
                                reported_usage=data.get('usage') or reported_usage;reported_timings=data.get('timings') or reported_timings;delta=(data.get('choices') or [{}])[0].get('delta',{})
                                if delta.get('content') or delta.get('reasoning_content'):
                                    first=first or time.monotonic();count+=1
                                    LIVE.update(tokens=count,tok_s=(count-1)/max(.001,time.monotonic()-first) if count>1 else None,ttft_ms=(first-start_)*1000)
                            except (ValueError,IndexError):pass
                        handler.wfile.write(line);handler.wfile.flush()
                    if not saw_done:raise RuntimeError('Streaming incompleto; no se calcula como respuesta correcta.')
                else:
                    content=r.read();data=json.loads(content);reported_usage=data.get('usage') or {};reported_timings=data.get('timings') or {};count=reported_usage.get('completion_tokens',0);handler.wfile.write(content)
                LIVE['requests']+=1;success=True
        except Exception:
            LIVE['errors']+=1;raise
        finally:
            rate=reported_timings.get('predicted_per_second') or reported_timings.get('decode_tps');input_rate=reported_timings.get('prompt_per_second') or reported_timings.get('prefill_tps')
            if rate is None and engine!='fm' and first and reported_usage.get('completion_tokens',0)>1:
                rate=(reported_usage['completion_tokens']-1)/max(.001,time.monotonic()-first)
            LIVE.update(state='En espera',tokens=0,tok_s=None,last_generation_tok_s=rate,last_input_tok_s=input_rate,last_total_s=time.monotonic()-start_,last_load_s=load_s)
            # Aggregate timing only: agent conversations are never saved here.
            event('request',{'engine':engine,'model':m['id'],'success':success,'generation_tok_s':rate,'source':'Pasarela','ttft_s':first-start_ if first else None,'wall_s':time.monotonic()-start_,'output_tokens_or_chunks':count,'load_s':load_s,'usage':reported_usage,'timings':reported_timings,'stream':body['stream'],'counter_type':'chunks' if body['stream'] else 'tokens'})

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*a):pass
    def send(self,d,code=200):
        b=json.dumps(d,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def auth(self):
        host=self.headers.get('Host','').split(':')[0]
        return host in ('127.0.0.1','localhost') and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+(ROOT/'token').read_text())
    def do_GET(self):
        if not self.auth():self.send({'error':'No autorizado'},401);return
        path=urllib.parse.urlsplit(self.path).path
        if path=='/health':self.send({'status':'ok','service':'IA Local','version':'1.0.0'})
        elif path=='/native-next':self.send(host_next())
        elif path=='/native-result':self.send(host_result(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('id',[''])[0]))
        elif path=='/status':self.send(CACHE or {'starting':True})
        elif path=='/v1/models':self.send({'object':'list','data':[{'id':engine+'/'+m['id'],'object':'model','owned_by':engine,'context_length':m['context']} for m in models() for engine in m['engines']]})
        elif path=='/export':self.send({'results':CACHE.get('results',[]),'models':models(),'agent_checks':read(ROOT/'agent-checks.json',{}),'optimizations':read(ROOT/'optimizations.json',[]),'exported_at':time.time()})
        else:self.send({'error':'Ruta desconocida'},404)
    def do_POST(self):
        if not self.auth():self.send({'error':'No autorizado'},401);return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=4*1024*1024:raise ValueError('Solicitud demasiado grande o vacía.')
            body=json.loads(self.rfile.read(n))
            if self.path=='/action':self.send(job(body.get('action'),body.get('value'),body.get('engine')))
            elif self.path=='/security':
                import lan
                self.send(lan.security_local(body))
            elif self.path=='/native-request':self.send(host_request(body.get('command'),body,'Mac'))
            elif self.path=='/native-complete':self.send(host_complete(body))
            elif self.path=='/v1/chat/completions':forward_chat(self,body)
            else:self.send({'error':'Ruta desconocida'},404)
        except Exception as e:
            try:self.send({'error':str(e)},400)
            except (OSError,ValueError):pass

def ensure():
    init()
    if sys.platform!='darwin':return {'ok':True,'managed_by':'portable launcher'}
    if not (ROOT/'catalog.json').exists():discover()
    label='local.ia-local.supervisor'+('-'+hashlib.sha256(str(ROOT).encode()).hexdigest()[:10] if read(ROOT/'installation.json',{}).get('clean') else '')
    if not registered(label):
        p=ROOT/(label+'.plist');p.write_bytes(plistlib.dumps({'Label':label,'ProgramArguments':[str(PYTHON),str(ROOT/'supervisor.py'),'serve'],'WorkingDirectory':str(ROOT),'EnvironmentVariables':{'IA_LOCAL_HOME':str(ROOT),'IA_LOCAL_PYTHON':str(PYTHON),'IA_LOCAL_PORT':str(CONTROL_PORT)},'RunAtLoad':True,'KeepAlive':True,'ProcessType':'Interactive','StandardOutPath':str(ROOT/'logs/supervisor.log'),'StandardErrorPath':str(ROOT/'logs/supervisor.err.log')}));run(['launchctl','bootstrap',DOMAIN,p])
    return {'ok':True}

if __name__=='__main__':
    init()
    if sys.argv[1:] and sys.argv[1]=='ensure':print(json.dumps(ensure()))
    elif sys.argv[1:] and sys.argv[1]=='scan':print(json.dumps(discover()))
    else:
        # Claim socket before scanning or starting background tasks.
        if os.environ.get('IA_DESKTOP_UI')=='1':
            from desktop_server import handler_class
            server_handler=handler_class(Handler)
        else:server_handler=Handler
        server=ThreadingHTTPServer(('127.0.0.1',CONTROL_PORT),server_handler);server.daemon_threads=True
        for f in (monitor,maintenance):threading.Thread(target=f,daemon=True).start()
        if read(ROOT/'settings.json',{}).get('lan_enabled'):
            try:
                import lan
                lan.configure(True,job)
            except Exception as e:event('lan-start-failed',{'error':str(e)})
        server.serve_forever()
