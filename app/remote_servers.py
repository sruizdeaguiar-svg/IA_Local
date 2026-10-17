"""Opt-in LAN APIs. No remote process control, redirects or internet targets."""
from core import *
import ipaddress,urllib.parse,hashlib

def definitions():return read(ROOT/'remote-servers.json',{'items':[]}).get('items',[])
def definition(s):return next((d for d in definitions() if d['id']==s),None)
def networks():
    result=[]
    for name,addresses in psutil.net_if_addrs().items():
        if name.startswith(('utun','tun','tap','wg','lo','awdl','llw','veth','docker','br-','virbr','tailscale')):continue
        if not psutil.net_if_stats().get(name) or not psutil.net_if_stats()[name].isup:continue
        for a in addresses:
            if a.family==socket.AF_INET and a.netmask:
                ip=ipaddress.ip_address(a.address)
                if ip.is_private and not ip.is_loopback and not ip.is_link_local:result.append(ipaddress.ip_network(a.address+'/'+a.netmask,strict=False))
    return result

def validate_url(url):
    try:
        u=urllib.parse.urlsplit(url);ip=ipaddress.ip_address(u.hostname or '');port=u.port or (443 if u.scheme=='https' else 80)
    except ValueError:raise ValueError('Usa la dirección IP privada del servidor, por ejemplo http://192.168.1.20:8080/v1.') from None
    if u.scheme not in ('http','https') or u.username or u.password or u.query or u.fragment or not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)*',u.path.rstrip('/')):raise ValueError('URL de API no válida; sin credenciales, parámetros ni fragmentos.')
    if not isinstance(ip,ipaddress.IPv4Address) or not ip.is_private or ip.is_loopback or ip.is_link_local or not any(ip in net and ip not in (net.network_address,net.broadcast_address) for net in networks()):raise ValueError('La IP debe pertenecer a una red privada conectada actualmente a este Mac. No se admiten Internet, VPN ni loopback.')
    if not u.path.rstrip('/').endswith('/v1'):raise ValueError('La URL debe terminar en /v1, por ejemplo http://192.168.1.20:8080/v1.')
    if not 1<=port<=65535:raise ValueError('Puerto remoto no válido.')
    return u.scheme+'://'+str(ip)+':'+str(port)+u.path.rstrip('/')

def headers(s):
    key=read(ROOT/'remote-credentials.json',{}).get(s,'')
    return {'Authorization':'Bearer '+key} if key else {}
def api_base(s):return validate_url(definition(s)['base_url'])
def request(s,path,body=None,timeout=5):return http(api_base(s),path,body,timeout,headers=headers(s))
def connected(s):return s in read(ROOT/'remote-connections.json',[])
def connect(s):
    d=definition(s)
    if not d:raise ValueError('Servidor remoto desconocido.')
    listing=request(s,'/models')
    if not isinstance(listing,dict) or not isinstance(listing.get('data'),list) or any(not isinstance(x,dict) or not isinstance(x.get('id'),str) for x in listing['data']):raise RuntimeError('La API no devolvió un inventario OpenAI compatible.')
    cache=read(ROOT/'remote-catalog.json',{});cache[s]={'time':time.time(),'models':listing['data']};write(ROOT/'remote-catalog.json',cache)
    live=read(ROOT/'remote-connections.json',[])
    if s not in live:live.append(s)
    write(ROOT/'remote-connections.json',live);return {'message':str(len(listing['data']))+' modelos anunciados. No significa que estén cargados.','models':len(listing['data'])}
def disconnect(s):
    write(ROOT/'remote-connections.json',[x for x in read(ROOT/'remote-connections.json',[]) if x!=s])
    if read(ROOT/'active.json',{}).get('engine')==s:write(ROOT/'active.json',{})
    return {'message':'Desconectado de IA Local. El proceso y los modelos del otro ordenador se conservan.'}
def register(v):
    sid=v.get('id','')
    if not re.fullmatch(r'remote-[a-z][a-z0-9-]{1,40}',sid):raise ValueError('Identificador: remote- seguido de letras, números o guiones.')
    name=str(v.get('name','')).strip();url=validate_url(str(v.get('base_url','')))
    if not 1<=len(name)<=80:raise ValueError('Nombre no válido.')
    context=v.get('context',4096)
    if type(context) is not int or context not in (4096,8192,32768,65536):raise ValueError('Contexto: 4096, 8192, 32768 o 65536; debe confirmarse en el servidor remoto.')
    key=v.get('api_key','')
    if not isinstance(key,str) or len(key)>4096 or '\n' in key or '\r' in key:raise ValueError('Clave no válida.')
    if (key or headers(sid)) and url.startswith('http:') and v.get('allow_insecure') is not True:raise ValueError('Una API con clave requiere HTTPS, o aceptar expresamente el envío sin cifrado por esta LAN.')
    disconnect(sid)
    d={'id':sid,'name':name,'base_url':url,'context':context,'kind':'server','transport':'lan','allow_insecure':bool(v.get('allow_insecure'))}
    write(ROOT/'remote-servers.json',{'items':[x for x in definitions() if x['id']!=sid]+[d]})
    keys=read(ROOT/'remote-credentials.json',{})
    if key:keys[sid]=key
    elif v.get('clear_key'):keys.pop(sid,None)
    write(ROOT/'remote-credentials.json',keys);install_registry();return {'message':'Servidor LAN guardado. Pulsa Conectar para comprobar su inventario.'}
def unregister(s):
    disconnect(s);write(ROOT/'remote-servers.json',{'items':[x for x in definitions() if x['id']!=s]});keys=read(ROOT/'remote-credentials.json',{});keys.pop(s,None);write(ROOT/'remote-credentials.json',keys);NAMES.pop(s,None);return {'message':'Servidor LAN retirado. No se modifica el ordenador remoto.'}
def install_registry():
    for d in definitions():NAMES[d['id']]=d['name']
def models_remote():
    rows=[];cache=read(ROOT/'remote-catalog.json',{})
    for d in definitions():
        for m in cache.get(d['id'],{}).get('models',[]):
            context=read(ROOT/'contexts.json',{}).get('lan-'+hashlib.sha256((d['id']+'/'+m['id']).encode()).hexdigest()[:16],d['context'])
            rows.append({'id':'lan-'+hashlib.sha256((d['id']+'/'+m['id']).encode()).hexdigest()[:16],'label':m['id']+' · '+d['name'],'native_id':m['id'],'format':'Remote API','path':'','bytes':0,'context':context,'max_context':d['context'],'engines':[d['id']],'architecture':'remote','status':'Inventario remoto; contexto declarado por el usuario. Memoria y carga en el equipo remoto no verificadas.','remote':True})
    return rows
def rows():
    result=[]
    for d in definitions():
        enabled=connected(d['id']);cache=read(ROOT/'remote-catalog.json',{}).get(d['id'],{});reachable=False
        if enabled:
            try:reachable=bool(request(d['id'],'/models',timeout=1).get('data') is not None)
            except Exception:pass
        result.append({'id':d['id'],'name':d['name'],'kind':'server','remote':True,'port':urllib.parse.urlsplit(d['base_url']).port,'url':d['base_url'].removesuffix('/v1'),'state':'API remota disponible' if reachable else 'Remoto sin respuesta' if enabled else 'Desconectado','running':enabled,'ready':reachable,'managed':False,'models':[m['id'] for m in cache.get('models',[])],'has_key':bool(headers(d['id']))})
    return result
