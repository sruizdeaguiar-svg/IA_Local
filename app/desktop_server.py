"""Loopback desktop browser bridge for the portable Windows/Linux distribution.

The launcher owns a private bearer, obtains a single-use 30-second capability,
then opens a random, cookie-scoped desktop session. No bearer is embedded in JS.
Only same-origin, CSRF-protected bridge requests can administer this profile.
This interface is never bound to LAN; LAN access uses lan.py's HTTPS accounts.
"""
import hashlib,json,mimetypes,re,secrets,threading,time,urllib.parse,urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from core import ROOT,CONTROL_PORT,OPENER,executable_path,read,run

_GUARD=threading.RLock();_NONCES={};_SESSIONS={}
ASSETS={'icon-180.png','icon-192.png','icon-512.png'}
BRIDGE_PATHS={'/status','/health','/action','/export','/security','/native-next','/native-complete','/native-result'}

def launch_url():
    with _GUARD:
        now=time.time()
        for k,v in list(_NONCES.items()):
            if v<now:del _NONCES[k]
        nonce=secrets.token_urlsafe(32);_NONCES[nonce]=now+30
    return f'http://127.0.0.1:{CONTROL_PORT}/desktop/open/{nonce}'

def bootstrap_js(base,csrf):
    return '''<script>window.iaDesktop=true;window.iaPortableRequest=async function(body){
const base=__BASE_VALUE__,csrf=__CSRF_VALUE__;
if(body.command==='export'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(body.data,null,2)],{type:'application/json'}));a.download='IA-Local-resultados.json';a.click();URL.revokeObjectURL(a.href);return{ok:true};}
if(body.command==='export-certificate'){location.assign(base+'certificate');return{ok:true};}
const response=await fetch(base+'bridge',{method:'POST',headers:{'Content-Type':'application/json','X-IA-CSRF':csrf},body:JSON.stringify(body)});const value=await response.json();if(!response.ok||value.error)throw Error(value.error||'Sesión local caducada; abre IA Local de nuevo.');if(value.url)window.open(value.url,'_blank','noopener,noreferrer');return value;
};</script>'''.replace('__BASE_VALUE__',json.dumps(base)).replace('__CSRF_VALUE__',json.dumps(csrf))

def handler_class(parent):
    class DesktopHandler(parent):
        def desktop_send(self,value,code=200,ctype='application/json',headers=None):
            payload=json.dumps(value,ensure_ascii=False).encode() if ctype=='application/json' else value.encode() if isinstance(value,str) else value
            self.send_response(code)
            for k,v in {'Content-Type':ctype,'Content-Length':str(len(payload)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',**(headers or {})}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(payload)
        def desktop_host(self):return self.headers.get('Host')==f'127.0.0.1:{CONTROL_PORT}' and self.client_address[0]=='127.0.0.1'
        def desktop_session(self):
            path=urllib.parse.urlsplit(self.path).path;parts=path.split('/')
            if len(parts)<4:return None,None
            sid=parts[2]
            with _GUARD:
                for k,v in list(_SESSIONS.items()):
                    if v['expires']<time.time():del _SESSIONS[k]
                session=_SESSIONS.get(sid)
            try:cookie=SimpleCookie(self.headers.get('Cookie',''));value=cookie['ia_desktop'].value
            except (KeyError,ValueError):return None,None
            if not session or not secrets.compare_digest(hashlib.sha256(value.encode()).hexdigest(),session['cookie']):return None,None
            return sid,session
        def do_GET(self):
            path=urllib.parse.urlsplit(self.path).path
            if path=='/desktop-session':
                if not self.desktop_host() or not self.auth():self.desktop_send({'error':'No autorizado'},401);return
                self.desktop_send({'url':launch_url()});return
            if not path.startswith('/desktop/'):return super().do_GET()
            if not self.desktop_host():self.desktop_send({'error':'Origen no permitido'},403);return
            if path.startswith('/desktop/open/'):
                nonce=path.removeprefix('/desktop/open/')
                with _GUARD:expires=_NONCES.pop(nonce,0)
                if expires<time.time():self.desktop_send({'error':'Enlace caducado o utilizado. Abre IA Local de nuevo.'},401);return
                sid=secrets.token_urlsafe(24);cookie=secrets.token_urlsafe(32);base=f'/desktop/{sid}/'
                with _GUARD:_SESSIONS[sid]={'cookie':hashlib.sha256(cookie.encode()).hexdigest(),'csrf':secrets.token_urlsafe(32),'expires':time.time()+12*3600}
                self.desktop_send('',303,'text/plain',{'Location':base,'Set-Cookie':f'ia_desktop={cookie}; HttpOnly; SameSite=Strict; Path={base}'});return
            sid,session=self.desktop_session()
            if not session:self.desktop_send({'error':'Sesión local caducada. Abre IA Local de nuevo.'},401);return
            base=f'/desktop/{sid}/';tail=path.removeprefix(base)
            if not tail:
                html=(ROOT/'index.html').read_text(encoding='utf-8');html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>','',html);html=html.replace('</head>',f'<link rel="icon" href="{base}icon-192.png"></head>');html=html.replace('<script>',bootstrap_js(base,session['csrf'])+'<script>',1)
                # Offline worker is a LAN/PWA feature; never cache owner capabilities.
                html=re.sub(r"if\('serviceWorker' in navigator[^\n]+",'',html)
                self.desktop_send(html,ctype='text/html; charset=utf-8',headers={'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"});return
            if tail in ASSETS:
                self.desktop_send((ROOT/tail).read_bytes(),ctype=mimetypes.guess_type(tail)[0] or 'application/octet-stream');return
            if tail=='certificate' and (ROOT/'lan-cert.pem').is_file():self.desktop_send((ROOT/'lan-cert.pem').read_bytes(),ctype='application/x-pem-file',headers={'Content-Disposition':'attachment; filename="IA-Local-certificado.pem"'});return
            self.desktop_send({'error':'Ruta desconocida'},404)
        def do_POST(self):
            path=urllib.parse.urlsplit(self.path).path
            if not path.startswith('/desktop/'):return super().do_POST()
            sid,session=self.desktop_session()
            if not self.desktop_host() or self.headers.get('Origin')!=f'http://127.0.0.1:{CONTROL_PORT}':self.desktop_send({'error':'Origen no permitido'},403);return
            if not session:self.desktop_send({'error':'No autorizado'},401);return
            if not secrets.compare_digest(self.headers.get('X-IA-CSRF',''),session['csrf']):self.desktop_send({'error':'Verificación CSRF fallida'},403);return
            if path!=f'/desktop/{sid}/bridge':self.desktop_send({'error':'Ruta desconocida'},404);return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if self.headers.get('Transfer-Encoding') or not 0<n<=4*1024*1024:raise ValueError('Solicitud no válida.')
                body=json.loads(self.rfile.read(n));command=body.get('command')
                if command=='open':
                    u=urllib.parse.urlsplit(body.get('url',''))
                    allowed=(u.scheme=='http' and u.hostname in ('127.0.0.1','localhost')) or (u.scheme=='https' and u.hostname in {'github.com','opencode.ai','lmstudio.ai','support.apple.com','assets.exolabs.net',read(ROOT/'lan-info.json',{}).get('hostname'),read(ROOT/'lan-info.json',{}).get('address')})
                    if not allowed or u.username or u.password:raise ValueError('Destino no permitido.')
                    self.desktop_send({'ok':True,'url':u.geturl()});return
                if command=='open-opencode':
                    text=run([executable_path('opencode'),'pair'],30);match=re.search(r'http://(?:127\.0\.0\.1|localhost):[0-9]+/auth/connect/[^\s]+',text)
                    if not match:raise ValueError('OpenCode no entregó un enlace local. Comprueba que esté arrancado.')
                    self.desktop_send({'ok':True,'url':match[0]});return
                if command:raise ValueError('Esta operación requiere macOS. Configura las carpetas en Configuración.')
                route=body.get('path','');parsed=urllib.parse.urlsplit(route)
                if parsed.scheme or parsed.netloc or parsed.path not in BRIDGE_PATHS:raise ValueError('Ruta no permitida.')
                method=body.get('method','GET')
                if method not in ('GET','POST'):raise ValueError('Método no permitido.')
                payload=json.dumps(body['body']).encode() if method=='POST' else None
                request=urllib.request.Request(f'http://127.0.0.1:{CONTROL_PORT}'+route,data=payload,method=method,headers={'Authorization':'Bearer '+(ROOT/'token').read_text(encoding='utf-8'),'Content-Type':'application/json'})
                with OPENER.open(request,timeout=30) as response:result=json.load(response)
                self.desktop_send(result)
            except Exception as e:self.desktop_send({'error':str(e)},400)
    return DesktopHandler
