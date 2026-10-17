"""Explicit cloud connections with private keys and OpenAI/Anthropic adapters.

Local proxy ports are authenticated and loopback-only. No provider is enabled by
startup, discovery or Start all. TLS targets are pinned to validated public IPs.
"""
from core import *
import ssl,ipaddress,urllib.parse,http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
SERVERS={};GUARD=threading.RLock()
PRESETS={'openai':('OpenAI','openai','https://api.openai.com/v1'),'anthropic':('Anthropic','anthropic','https://api.anthropic.com/v1'),'kimi':('Kimi','openai','https://api.moonshot.ai/v1'),'deepseek':('DeepSeek','openai','https://api.deepseek.com/v1'),'freellmapi':('FreeLLMAPI local','openai','http://127.0.0.1:8043/v1')}
def definitions():return read(ROOT/'external-providers.json',{'items':[]}).get('items',[])
def definition(s):return next((d for d in definitions() if d['id']==s),None)
def target(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or not re.fullmatch(r'(?:/[a-zA-Z0-9_.-]+)*',u.path.rstrip('/')):raise ValueError('El proveedor externo requiere HTTPS sin credenciales ni parámetros en la URL.')
    port=u.port or 443
    addresses={x[4][0] for x in socket.getaddrinfo(u.hostname,port,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):raise ValueError('El proveedor externo debe resolver solo a direcciones públicas. Usa Servidor LAN para IP privadas.')
    return u,next(iter(addresses)),port

def upstream(s,path,body=None):
    d=definition(s);key=read(ROOT/'external-credentials.json',{}).get(s,'')
    if not key:raise RuntimeError('Falta la clave API de este proveedor. Añádela en Proveedores externos.')
    if d.get('gateway'):
        check_service_ports('freellmapi')
        if not same(ledger().get('freellmapi')):raise RuntimeError('Arranca primero FreeLLMAPI desde Control. No se envía su clave a un proceso sin identidad.')
        req=urllib.request.Request(d['base_url']+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
        response=OPENER.open(req,timeout=240)
        return response,response
    u,ip,port=target(d['base_url'])
    c=http.client.HTTPSConnection(u.hostname,port,timeout=240,context=ssl.create_default_context())
    # Pin the connection to the already validated address while checking TLS for the hostname.
    c.sock=c._context.wrap_socket(socket.create_connection((ip,port),timeout=240),server_hostname=u.hostname)
    headers={'Content-Type':'application/json','Accept':'application/json'}
    headers.update({'x-api-key':key,'anthropic-version':'2023-06-01'} if d['protocol']=='anthropic' else {'Authorization':'Bearer '+key})
    c.request('GET' if body is None else 'POST',u.path.rstrip('/')+path,body=None if body is None else json.dumps(body).encode(),headers=headers);r=c.getresponse()
    if r.status<200 or r.status>=300:r.read(4096);c.close();raise RuntimeError('El proveedor respondió HTTP '+str(r.status)+'. Revisa clave, permisos, modelo, saldo y límites; no se ha activado una alternativa.')
    return c,r

def register(v):
    sid=v.get('id','');name=str(v.get('name','')).strip();protocol=v.get('protocol')
    if not re.fullmatch(r'cloud-[a-z][a-z0-9-]{1,40}',sid) or not 1<=len(name)<=80 or protocol not in ('openai','anthropic'):raise ValueError('Nombre, identificador cloud- o protocolo no válido.')
    gateway=v.get('preset')=='freellmapi' and v.get('base_url')=='http://127.0.0.1:8043/v1' and protocol=='openai'
    if not gateway:target(v.get('base_url',''))
    port=v.get('port');validate_ports({**{k:p for k,p in PORTS.items() if k!=sid},sid:port})
    context=v.get('context',32768)
    if context not in (4096,8192,32768,65536):raise ValueError('Contexto declarado no válido.')
    ids=v.get('models',[])
    if not isinstance(ids,list) or len(ids)>200 or any(not isinstance(x,str) or not 1<=len(x)<=200 or '\n' in x for x in ids):raise ValueError('Modelos: lista de identificadores del proveedor.')
    key=v.get('api_key','')
    if not isinstance(key,str) or '\n' in key or '\r' in key or len(key)>4096:raise ValueError('Clave no válida.')
    disconnect(sid)
    d={'id':sid,'name':name,'protocol':protocol,'base_url':v['base_url'].rstrip('/'),'port':port,'context':context,'models':list(dict.fromkeys(ids)),'transport':'cloud','kind':'server','gateway':gateway}
    write(ROOT/'external-providers.json',{'items':[x for x in definitions() if x['id']!=sid]+[d]});keys=read(ROOT/'external-credentials.json',{})
    if key:keys[sid]=key
    elif v.get('clear_key'):keys.pop(sid,None)
    write(ROOT/'external-credentials.json',keys);install_registry();return {'message':'Proveedor guardado y desconectado. Conectar solo consulta inventario; las generaciones pueden tener coste.'}
def install_registry():
    for d in definitions():
        try:validate_ports({**PORTS,d['id']:d['port']})
        except RuntimeError:continue
        PORTS[d['id']]=d['port'];NAMES[d['id']]=d['name']
def inventory(s):
    c,r=upstream(s,'/models')
    try:d=json.load(r)
    finally:c.close()
    if not isinstance(d.get('data'),list):raise RuntimeError('El proveedor no devolvió un inventario compatible. Puedes declarar IDs de modelo manualmente.')
    ids=[x['id'] for x in d['data'] if isinstance(x,dict) and isinstance(x.get('id'),str)]
    doc=read(ROOT/'external-providers.json',{'items':[]})
    for item in doc['items']:
        if item['id']==s:item['models']=list(dict.fromkeys(item['models']+ids));item['checked_at']=time.time()
    write(ROOT/'external-providers.json',doc);return len(ids)
def connect(s):
    d=definition(s)
    if not d:raise ValueError('Proveedor no encontrado.')
    with GUARD:
        if s in SERVERS:return {'message':'Proveedor ya conectado.'}
        # Explicit model IDs allow endpoints without GET /models. No generation on connect.
        warning=None
        try:count=inventory(s)
        except Exception as e:
            if not d['models']:raise
            count=len(d['models']);warning=str(e)+' Se conservan los IDs declarados; compatibilidad pendiente de inferencia.'
        core_check=check_service_ports(s);server=ThreadingHTTPServer(('127.0.0.1',d['port']),Proxy);server.daemon_threads=True;server.service=s;SERVERS[s]=server;threading.Thread(target=server.serve_forever,daemon=True).start()
    return {'message':'Conexión preparada para '+str(count)+' modelos. No se ha generado texto.','warnings':[warning] if warning else []}
def disconnect(s):
    with GUARD:
        server=SERVERS.pop(s,None)
        if server:server.shutdown();server.server_close()
    if read(ROOT/'active.json',{}).get('engine')==s:write(ROOT/'active.json',{})
    return {'message':'Proveedor desconectado de IA Local; sus credenciales se conservan.'}
def unregister(s):
    disconnect(s);write(ROOT/'external-providers.json',{'items':[x for x in definitions() if x['id']!=s]});keys=read(ROOT/'external-credentials.json',{});keys.pop(s,None);write(ROOT/'external-credentials.json',keys);PORTS.pop(s,None);NAMES.pop(s,None);return {'message':'Proveedor retirado.'}
def models_cloud():
    result=[]
    for d in definitions():
        for mid in d['models']:
            result.append({'id':'api-'+hashlib.sha256((d['id']+'/'+mid).encode()).hexdigest()[:16],'native_id':mid,'label':mid+' · '+d['name']+' · nube','format':'Cloud API','bytes':0,'context':d['context'],'max_context':d['context'],'engines':[d['id']],'status':'Proveedor externo: los datos salen del Mac y puede haber coste. Contexto declarado; modelo sin verificar hasta inferencia.','remote':True,'external':True})
    return result

def to_anthropic(body):
    if body.get('n',1)!=1 or body.get('response_format',{}).get('type','text')!='text':raise ValueError('Este adaptador Anthropic no admite n>1 ni response_format; utiliza mensajes de texto o herramientas.')
    if any(t.get('type')!='function' for t in body.get('tools',[])):raise ValueError('Solo se admiten herramientas de tipo function.')
    result={'model':body['model'],'max_tokens':min(int(body.get('max_completion_tokens') or body.get('max_tokens') or 1024),8192),'stream':bool(body.get('stream')),'messages':[]};systems=[]
    for m in body.get('messages',[]):
        role=m.get('role');content=m.get('content')
        if role in ('system','developer'):
            if content:systems.append(content if isinstance(content,str) else '\n'.join(x.get('text','') for x in content if x.get('type')=='text'))
            continue
        if role=='tool':row={'role':'user','content':[{'type':'tool_result','tool_use_id':m['tool_call_id'],'content':content or ''}]}
        else:
            blocks=[]
            if isinstance(content,str) and content:blocks.append({'type':'text','text':content})
            elif isinstance(content,list):
                for block in content:
                    if block.get('type')=='text':blocks.append({'type':'text','text':block['text']})
                    elif block.get('type')=='image_url':
                        url=block['image_url']['url']
                        if url.startswith('data:'):
                            media,encoded=url[5:].split(';base64,',1);blocks.append({'type':'image','source':{'type':'base64','media_type':media,'data':encoded}})
                        elif url.startswith('https://'):blocks.append({'type':'image','source':{'type':'url','url':url}})
                        else:raise ValueError('Imagen no compatible con Anthropic.')
                    else:raise ValueError('Contenido no compatible con el adaptador Anthropic de mensajes.')
            for tool in m.get('tool_calls',[]):blocks.append({'type':'tool_use','id':tool['id'],'name':tool['function']['name'],'input':json.loads(tool['function']['arguments'])})
            row={'role':'assistant' if role=='assistant' else 'user','content':blocks or [{'type':'text','text':' '} ]}
        if result['messages'] and result['messages'][-1]['role']==row['role']:result['messages'][-1]['content']+=row['content']
        else:result['messages'].append(row)
    if systems:result['system']='\n\n'.join(systems)
    for key in ('temperature','top_p','stop'):
        if key in body:result['stop_sequences' if key=='stop' else key]=[body[key]] if key=='stop' and isinstance(body[key],str) else body[key]
    if body.get('tools'):result['tools']=[{'name':t['function']['name'],'description':t['function'].get('description',''),'input_schema':t['function'].get('parameters',{'type':'object','properties':{}})} for t in body['tools'] if t.get('type')=='function']
    choice=body.get('tool_choice')
    if choice and choice!='none':result['tool_choice']={'type':'tool','name':choice['function']['name']} if isinstance(choice,dict) else {'type':'any' if choice=='required' else 'auto'}
    if choice=='none':result.pop('tools',None)
    return result

def finish_reason(reason):return {'tool_use':'tool_calls','max_tokens':'length'}.get(reason,'stop')
def from_anthropic(d):
    message={'role':'assistant','content':''.join(b.get('text','') for b in d.get('content',[]) if b.get('type')=='text')};tools=[{'id':b['id'],'type':'function','function':{'name':b['name'],'arguments':json.dumps(b['input'])}} for b in d.get('content',[]) if b.get('type')=='tool_use']
    if tools:message['tool_calls']=tools
    usage=d.get('usage',{});inp=usage.get('input_tokens',0)+usage.get('cache_read_input_tokens',0)+usage.get('cache_creation_input_tokens',0);out=usage.get('output_tokens',0)
    return {'id':d.get('id',''),'object':'chat.completion','model':d.get('model'),'choices':[{'index':0,'message':message,'finish_reason':finish_reason(d.get('stop_reason'))}],'usage':{'prompt_tokens':inp,'completion_tokens':out,'total_tokens':inp+out}}

def anthropic_chunks(response):
    mid='';model='';tools={};usage={};saw_end=False
    for line in response:
        if not line.startswith(b'data:'):continue
        d=json.loads(line[5:]);kind=d.get('type');delta={};finish=None
        if kind=='error':raise RuntimeError('El proveedor interrumpió el streaming: '+str(d.get('error',{}).get('type','error')))
        if kind=='message_start':
            msg=d['message'];mid=msg['id'];model=msg['model'];u=msg.get('usage',{});usage={'prompt_tokens':u.get('input_tokens',0)+u.get('cache_read_input_tokens',0)+u.get('cache_creation_input_tokens',0),'completion_tokens':u.get('output_tokens',0)};delta={'role':'assistant'}
        elif kind=='content_block_start' and d['content_block'].get('type')=='tool_use':
            block=d['content_block'];idx=len(tools);tools[d['index']]=idx;delta={'tool_calls':[{'index':idx,'id':block['id'],'type':'function','function':{'name':block['name'],'arguments':''}}]}
        elif kind=='content_block_delta':
            part=d['delta']
            if part['type']=='text_delta':delta={'content':part['text']}
            elif part['type']=='thinking_delta':delta={'reasoning_content':part['thinking']}
            elif part['type']=='input_json_delta':delta={'tool_calls':[{'index':tools[d['index']],'function':{'arguments':part['partial_json']}}]}
        elif kind=='message_delta':usage['completion_tokens']=d.get('usage',{}).get('output_tokens',usage.get('completion_tokens',0));finish=finish_reason(d.get('delta',{}).get('stop_reason'))
        elif kind=='message_stop':saw_end=True;break
        if delta or finish:
            payload={'id':mid,'object':'chat.completion.chunk','model':model,'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
            if finish:payload['usage']={**usage,'total_tokens':sum(usage.values())}
            yield payload
    if not saw_end:raise RuntimeError('Streaming Anthropic incompleto; no se considera una respuesta válida.')

class Proxy(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*a):pass
    def authorized(self):return self.headers.get('Host','').split(':')[0] in ('127.0.0.1','localhost') and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+(ROOT/'token').read_text())
    def send_json(self,d,status=200):
        b=json.dumps(d).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if not self.authorized():self.send_json({'error':'No autorizado'},401);return
        if self.path!='/v1/models':self.send_json({'error':'Ruta no admitida'},404);return
        self.send_json({'data':[{'id':m} for m in definition(self.server.service)['models']]})
    def do_POST(self):
        started=False;c=None
        try:
            if not self.authorized():self.send_json({'error':'No autorizado'},401);return
            if self.path!='/v1/chat/completions':raise ValueError('Solo Chat Completions compatible; no implementa Responses, archivos ni funciones propias del proveedor.')
            n=int(self.headers.get('Content-Length',0))
            if not 0<n<=4*1024*1024:raise ValueError('Solicitud demasiado grande o vacía.')
            body=json.loads(self.rfile.read(n));d=definition(self.server.service)
            if body.get('model') not in d['models']:raise ValueError('Modelo no declarado en este proveedor.')
            stream=bool(body.get('stream'));anthropic=d['protocol']=='anthropic'
            payload=to_anthropic(body) if anthropic else {k:v for k,v in body.items() if k not in ('chat_template_kwargs','enable_thinking')}
            c,r=upstream(d['id'],'/messages' if anthropic else '/chat/completions',payload)
            if not stream:self.send_json(from_anthropic(json.load(r)) if anthropic else json.load(r));return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.send_header('Cache-Control','no-store');self.end_headers();started=True
            if anthropic:
                for chunk in anthropic_chunks(r):self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode());self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                for line in r:self.wfile.write(line);self.wfile.flush()
            self.close_connection=True
        except Exception as e:
            # Never return a provider response body: it may echo keys or user data.
            if not started:self.send_json({'error':str(e) if isinstance(e,(ValueError,RuntimeError)) else 'No se pudo completar la conexión HTTPS con el proveedor.'},502)
            else:self.wfile.write(b'data: {"error":{"message":"Streaming externo interrumpido"}}\n\n');self.close_connection=True
        finally:
            if c:c.close()
def rows():
    return [{'id':d['id'],'name':d['name']+' · nube','kind':'server','external':True,'remote':True,'port':d['port'],'url':'http://127.0.0.1:'+str(d['port']),'state':'Conexión externa preparada' if d['id'] in SERVERS else 'Desconectado','running':d['id'] in SERVERS,'ready':d['id'] in SERVERS,'managed':True,'models':d['models']} for d in definitions()]
def view():return [{**d,'has_key':bool(read(ROOT/'external-credentials.json',{}).get(d['id'])),'connected':d['id'] in SERVERS} for d in definitions()]


def import_freellmapi():
    path=ROOT/'freellmapi-data.sqlite'
    if not path.exists():raise RuntimeError('FreeLLMAPI no está configurado en esta instalación.')
    with sqlite3.connect(path) as connection:row=connection.execute("SELECT value FROM settings WHERE key='unified_api_key'").fetchone()
    if not row:raise RuntimeError('FreeLLMAPI no tiene una clave de cliente guardada.')
    current=definition('cloud-freellmapi');port=current['port'] if current else next(p for p in range(8050,8400) if p not in PORTS.values() and p not in AUX_PORTS.values() and not port_open(p))
    return register({'id':'cloud-freellmapi','name':'FreeLLMAPI','preset':'freellmapi','protocol':'openai','base_url':'http://127.0.0.1:8043/v1','port':port,'context':4096,'models':['auto','auto:fast'],'api_key':row[0]})
