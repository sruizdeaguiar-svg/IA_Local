"""Authenticated HTTPS access on one physical, private LAN interface.

Inference backends keep their loopback bindings. This gateway is the only LAN listener.
Account administration is deliberately available only through the native Mac panel.
"""
from core import *
import html, ipaddress, select, ssl, base64, hmac, struct
from http import client as http_client
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SERVERS=[];STARTED={};GUARD=threading.RLock();FAILURES={}
COOKIE='__Host-ia_local';ITERATIONS=600000
PROXIES={8441:'opencode',8442:'llama',8443:'hermes',8444:'omlx',8445:'strata-llama',8446:'exo',8447:'freellmapi'}
ALLOWED_ACTIONS={'integration-scan','start','stop','start-all','stop-all','agents-start','agents-stop','load','unload','scan','benchmark','benchmark-all','optimize','optimize-all','restore-profile','cancel','set-context','updates','server-check','agent-checks'}
ADMIN_ACTIONS={'reset-application','restore-reset','integration-attach-known','external-register','external-remove','external-import-freellmapi','external-inventory','integration-assist','integration-register','integration-remove','remote-register','remote-remove','user-save','lan-enable','configure-agents','configure-active-agent','configure-cloud','sync-agents','restore-agents','gateway-start','gateway-stop','update','rollback-update','save-settings','logs','gpu-set'}

@contextlib.contextmanager
def access_db():
    p=ROOT/'access.sqlite';c=sqlite3.connect(p,timeout=10);os.chmod(p,0o600)
    c.execute('CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY,salt TEXT,hash TEXT,role TEXT,enabled INTEGER,changed REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY,name TEXT,expires REAL,csrf TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS totp (name TEXT PRIMARY KEY,secret TEXT,confirmed INTEGER,last_counter INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS stepups (session TEXT PRIMARY KEY,expires REAL)')
    try:
        with c:yield c
    finally:c.close()

def users():
    with access_db() as c:return [{'name':n,'role':r,'enabled':bool(e),'changed':t} for n,r,e,t in c.execute('SELECT name,role,enabled,changed FROM users ORDER BY name')]

def save_user(v):
    name=str(v.get('name','')).strip();password=v.get('password','');role=v.get('role','control');enabled=bool(v.get('enabled',True))
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,40}',name):raise ValueError('Usuario: entre 3 y 40 letras, números, puntos, guiones o guiones bajos.')
    if role not in ('admin','control','lectura'):raise ValueError('Rol no válido.')
    if not isinstance(password,str) or (password and not 12<=len(password)<=256):raise ValueError('La contraseña debe tener entre 12 y 256 caracteres.')
    with access_db() as c:
        prior=c.execute('SELECT salt,hash FROM users WHERE name=?',(name,)).fetchone()
        if not prior and not password:raise ValueError('Introduce una contraseña para crear la cuenta.')
        salt=secrets.token_hex(32) if password else prior[0]
        digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),ITERATIONS).hex() if password else prior[1]
        c.execute('INSERT OR REPLACE INTO users VALUES(?,?,?,?,?,?)',(name,salt,digest,role,int(enabled),time.time()))
        c.execute('DELETE FROM stepups WHERE session IN (SELECT hash FROM sessions WHERE name=?)',(name,));c.execute('DELETE FROM sessions WHERE name=?',(name,))
    event('lan-user-saved',{'name':name,'role':role,'enabled':enabled})
    return {'message':'Cuenta guardada. Sus sesiones anteriores se han cerrado.'}

def security_status(name=None):
    with access_db() as c:
        if name:return {'enabled':bool(c.execute('SELECT 1 FROM totp WHERE name=? AND confirmed=1',(name,)).fetchone())}
        return {'accounts':[{'name':n,'enabled':bool(ok)} for n,ok in c.execute('SELECT u.name,COALESCE(t.confirmed,0) FROM users u LEFT JOIN totp t ON t.name=u.name WHERE u.enabled=1 AND u.role="admin"')]}

def totp_begin(name):
    with access_db() as c:
        if not c.execute('SELECT 1 FROM users WHERE name=? AND enabled=1 AND role="admin"',(name,)).fetchone():raise ValueError('Elige una cuenta administradora habilitada.')
        if c.execute('SELECT 1 FROM totp WHERE name=? AND confirmed=1',(name,)).fetchone():raise ValueError('La cuenta ya tiene segundo factor. Para sustituirlo, desactívalo primero en este Mac.')
        secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
        c.execute('INSERT OR REPLACE INTO totp VALUES(?,?,0,-1)',(name,secret))
    return {'secret':secret,'uri':'otpauth://totp/IA%20Local:'+urllib.parse.quote(name)+'?secret='+secret+'&issuer=IA%20Local&algorithm=SHA1&digits=6&period=30'}

def totp_check(name,code,enroll=False):
    if not isinstance(code,str) or not re.fullmatch('[0-9]{6}',code):return False
    with GUARD,access_db() as c:
        r=c.execute('SELECT secret,confirmed,last_counter FROM totp WHERE name=?',(name,)).fetchone()
        if not r or not (enroll or r[1]):return False
        for step in range(int(time.time()//30)-1,int(time.time()//30)+2):
            if step<=r[2]:continue
            digest=hmac.new(base64.b32decode(r[0]+'='*((8-len(r[0])%8)%8)),struct.pack('>Q',step),'sha1').digest();offset=digest[-1]&15
            expected=str((struct.unpack('>I',digest[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
            if secrets.compare_digest(expected,code):
                c.execute('UPDATE totp SET confirmed=1,last_counter=? WHERE name=?',(step,name));return True
    return False

def security_local(body):
    name=body.get('name');op=body.get('operation')
    if op=='begin':return totp_begin(name)
    if op=='confirm':
        if not totp_check(name,body.get('code'),True):raise ValueError('Código no válido, caducado o ya utilizado.')
        event('second-factor-enabled',{'name':name});return {'message':'Segundo factor activado para '+name+'.'}
    if op=='disable':
        with access_db() as c:c.execute('DELETE FROM totp WHERE name=?',(name,));c.execute('DELETE FROM stepups WHERE session IN (SELECT hash FROM sessions WHERE name=?)',(name,));c.execute('DELETE FROM sessions WHERE name=?',(name,))
        event('second-factor-disabled',{'name':name});return {'message':'Segundo factor desactivado en este Mac. Las operaciones administrativas remotas quedan bloqueadas hasta volver a configurarlo.'}
    return security_status()

SENSITIVE={'reset-application','restore-reset','integration-attach-known','external-register','external-remove','external-import-freellmapi','external-inventory','integration-assist','integration-register','integration-remove','remote-register','remote-remove','update','rollback-update','gpu-set','user-save','lan-enable','configure-cloud','configure-agents','configure-active-agent','sync-agents','restore-agents'}

def address():
    for interface,addresses in psutil.net_if_addrs().items():
        if (sys.platform=='darwin' and not interface.startswith('en')) or interface.lower().startswith(('utun','tun','tap','wg','lo','awdl','llw','veth','docker','br-','virbr','tailscale')) or not psutil.net_if_stats().get(interface) or not psutil.net_if_stats()[interface].isup:continue
        for a in addresses:
            if a.family==socket.AF_INET and ipaddress.ip_address(a.address).is_private and not ipaddress.ip_address(a.address).is_loopback:return a.address,a.netmask
    raise RuntimeError('No hay una interfaz Ethernet o Wi-Fi con dirección privada disponible.')

def certificate(ip):
    cert=ROOT/'lan-cert.pem';key=ROOT/'lan-key.pem'
    if sys.platform!='darwin':
        from portable_security import certificate as portable_certificate
        return portable_certificate(ROOT,ip)
    hostname=run(['/usr/sbin/scutil','--get','LocalHostName']).strip().lower()+'.local'
    if not cert.exists() or not key.exists():
        run(['/opt/homebrew/bin/openssl','req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-noenc','-days','825','-subj','/CN='+hostname,'-addext','subjectAltName=DNS:'+hostname+',IP:'+ip,'-addext','basicConstraints=critical,CA:FALSE','-keyout',key,'-out',cert],30)
        os.chmod(key,0o600);os.chmod(cert,0o644)
    digest=run(['/opt/homebrew/bin/openssl','x509','-in',cert,'-noout','-fingerprint','-sha256']).split('=',1)[-1]
    return cert,key,hostname,digest

def status():
    return {**STARTED,'enabled':bool(SERVERS),'users':users(),'ports':{'panel':8440,**{v:k for k,v in PROXIES.items()}}}

def configure(enabled,dispatch=None):
    with GUARD:
        for s in SERVERS:s.shutdown();s.server_close()
        SERVERS.clear();STARTED.clear()
        cfg=read(ROOT/'settings.json',{});cfg['lan_enabled']=bool(enabled);write(ROOT/'settings.json',cfg)
        if not enabled:return {'message':'Acceso de red detenido.'}
        ip,mask=address();cert,key,host,digest=certificate(ip)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(cert,key)
        try:
            for port in (8440,*PROXIES):
                s=ThreadingHTTPServer((ip,port),Gateway);s.daemon_threads=True;s.dispatch=dispatch;s.network=ipaddress.ip_network(ip+'/'+mask,strict=False);s.hostname=host;s.service=PROXIES.get(port);s.socket=context.wrap_socket(s.socket,server_side=True);SERVERS.append(s)
            STARTED.update(address=ip,hostname=host,url='https://'+host+':8440',ip_url='https://'+ip+':8440',fingerprint=digest)
            write(ROOT/'lan-info.json',STARTED)
            for s in SERVERS:threading.Thread(target=s.serve_forever,daemon=True).start()
        except Exception:
            for s in SERVERS:s.server_close()
            SERVERS.clear();raise
    event('lan-enabled',{'address':ip,'ports':[8440,*PROXIES]})
    return {'message':'HTTPS disponible en '+STARTED['url']+'. Crea una cuenta en Red y usuarios.'}

LOGIN='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IA Local · Acceso</title><style>body{background:#eef1f6;color:#18263a;font:16px -apple-system,sans-serif;max-width:370px;margin:12vh auto;padding:25px}form{background:white;border-radius:16px;padding:28px}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0 18px;font:inherit}button{background:#3156ca;color:white;border:0;border-radius:8px}small{color:#57667a}</style><h1>IA Local</h1><p>Acceso privado a IA Local</p><form method="post" action="/__ia/login"><label>Usuario<input name="username" required autocomplete="username"></label><label>Contraseña<input name="password" type="password" required autocomplete="current-password"></label><button>Entrar</button><small>{message}</small></form></html>'''

class Gateway(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def send(self,value,code=200,ctype='application/json',headers=None):
        body=json.dumps(value,ensure_ascii=False).encode() if ctype=='application/json' else value.encode() if isinstance(value,str) else value
        self.send_response(code);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','DENY')
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def allowed_host(self):
        host=self.headers.get('Host','');allowed={STARTED.get('address'),self.server.hostname}
        return host in {h+':'+str(self.server.server_port) for h in allowed if h} and ipaddress.ip_address(self.client_address[0]) in self.server.network
    def origin_ok(self):
        origin=self.headers.get('Origin','')
        expected=urllib.parse.urlsplit('https://'+self.headers.get('Host',''))
        def same_origin(value):
            parsed=urllib.parse.urlsplit(value)
            return (parsed.scheme,parsed.hostname,parsed.port or 443)==(expected.scheme,expected.hostname,expected.port or 443)
        if origin and origin!='null' and same_origin(origin):return True
        # Safari can omit Origin on a same-origin form POST. Require both browser
        # Fetch Metadata and an exact same-origin Referer; never accept null alone.
        if origin in ('','null') and self.headers.get('Sec-Fetch-Site')=='same-origin' and same_origin(self.headers.get('Referer','')):return True
        event('lan-origin-rejected',{'host':self.headers.get('Host',''),'origin':origin,'fetch_site':self.headers.get('Sec-Fetch-Site',''),'path':urllib.parse.urlsplit(self.path).path})
        return False
    def session(self):
        try:cookie=SimpleCookie(self.headers.get('Cookie',''));token=cookie[COOKIE].value
        except (KeyError,ValueError):return None
        with access_db() as c:
            row=c.execute('SELECT u.name,u.role,s.csrf FROM sessions s JOIN users u ON u.name=s.name WHERE s.hash=? AND s.expires>? AND u.enabled=1',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        return {'name':row[0],'role':row[1],'csrf':row[2],'session':hashlib.sha256(token.encode()).hexdigest()} if row else None
    def payload(self):
        if self.headers.get('Transfer-Encoding'):raise ValueError('Solo se admiten cuerpos con longitud explícita.')
        n=int(self.headers.get('Content-Length','0'))
        if n<0 or n>16*1024*1024:raise ValueError('Solicitud demasiado grande.')
        return self.rfile.read(n)
    def login(self):
        if not self.origin_ok():self.send({'error':'Origen no permitido'},403);return
        now=time.time();attempts=[t for t in FAILURES.get(self.client_address[0],[]) if now-t<600]
        if len(attempts)>=8:self.send({'error':'Espera diez minutos antes de volver a intentarlo.'},429);return
        fields=urllib.parse.parse_qs(self.payload().decode());name=fields.get('username',[''])[0];password=fields.get('password',[''])[0]
        if len(name)>40 or len(password)>256:
            FAILURES[self.client_address[0]]=attempts+[now];self.send({'error':'Usuario o contraseña incorrectos.'},401);return
        with access_db() as c:row=c.execute('SELECT salt,hash,enabled FROM users WHERE name=?',(name,)).fetchone()
        salt=row[0] if row else '00'*32;digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),ITERATIONS).hex()
        if not row or not row[2] or not secrets.compare_digest(digest,row[1]):
            FAILURES[self.client_address[0]]=attempts+[now];self.send(LOGIN.replace('{message}','Usuario o contraseña incorrectos.'),401,'text/html; charset=utf-8');return
        token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(32)
        with access_db() as c:
            c.execute('DELETE FROM sessions WHERE expires<?',(now,));c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),name,now+12*3600,csrf))
        FAILURES.pop(self.client_address[0],None);event('lan-login',{'name':name})
        self.send('',303,'text/plain',{'Location':'/','Set-Cookie':COOKIE+'='+token+'; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200'})
    def do_GET(self):self.handle_request()
    def do_POST(self):self.handle_request()
    def do_PUT(self):self.handle_request()
    def do_DELETE(self):self.handle_request()
    def do_PATCH(self):self.handle_request()
    def do_OPTIONS(self):self.handle_request()
    def handle_request(self):
        try:
            if not self.allowed_host():self.send({'error':'Host o red no permitidos'},403);return
            if not self.path.startswith('/') or self.path.startswith('//'):self.send({'error':'Ruta no permitida'},400);return
            path=urllib.parse.urlsplit(self.path).path
            public={'/manifest.webmanifest':('manifest.webmanifest','application/manifest+json'),'/sw.js':('sw.js','text/javascript'),'/icon-180.png':('icon-180.png','image/png'),'/icon-192.png':('icon-192.png','image/png'),'/icon-512.png':('icon-512.png','image/png'),'/offline.html':('offline.html','text/html; charset=utf-8')}
            if path in public and self.command=='GET':
                filename,mime=public[path];self.send((ROOT/filename).read_bytes(),ctype=mime);return
            if path=='/__ia/login' and self.command=='POST':self.login();return
            user=self.session()
            if not user:
                if path.startswith('/__ia/'):
                    self.send({'error':'Sesión cerrada. Vuelve a entrar.'},401);return
                self.send(LOGIN.replace('{message}','Crea tu cuenta desde Red y usuarios en el panel del Mac.'),401 if self.command!='GET' else 200,'text/html; charset=utf-8');return
            if path=='/__ia/session' and self.command=='GET':self.send({'csrf':user['csrf'],'name':user['name'],'role':user['role'],'second_factor':security_status(user['name'])['enabled']});return
            if path=='/__ia/step-up' and self.command=='POST':
                if not self.origin_ok() or self.headers.get('X-IA-CSRF')!=user['csrf'] or user['role']!='admin':self.send({'error':'Sin permiso.'},403);return
                body=json.loads(self.payload());key=self.client_address[0]+'/totp/'+user['name'];now=time.time();failed=[t for t in FAILURES.get(key,[]) if now-t<600]
                if len(failed)>=8:self.send({'error':'Demasiados códigos incorrectos. Espera diez minutos.'},429);return
                if not totp_check(user['name'],body.get('code')):
                    FAILURES[key]=failed+[now];self.send({'error':'Código no válido, caducado o ya utilizado.'},403);return
                with access_db() as c:c.execute('INSERT OR REPLACE INTO stepups VALUES(?,?)',(user['session'],now+300))
                FAILURES.pop(key,None);event('remote-step-up',{'name':user['name']});self.send({'ok':True,'expires':now+300});return
            if path=='/__ia/logout' and self.command=='POST':
                if not self.origin_ok() or self.headers.get('X-IA-CSRF')!=user['csrf']:self.send({'error':'Origen no permitido'},403);return
                c=SimpleCookie(self.headers.get('Cookie',''))
                with access_db() as db_:db_.execute('DELETE FROM sessions WHERE hash=?',(hashlib.sha256(c[COOKIE].value.encode()).hexdigest(),))
                self.send({'ok':True},headers={'Set-Cookie':COOKIE+'=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0'});return
            if self.server.service:
                if user['role'] not in ('admin','control') or self.server.service=='freellmapi' and user['role']!='admin':self.send({'error':'Sin permiso para esta interfaz.'},403);return
                if self.command not in ('GET','HEAD','OPTIONS') or self.headers.get('Upgrade','').lower()=='websocket':
                    if not self.origin_ok():self.send({'error':'Origen no permitido'},403);return
                self.proxy();return
            if path=='/' and self.command=='GET':
                page=(ROOT/'index.html').read_text(encoding='utf-8').replace('__IA_UI_BUILD__',str((ROOT/'index.html').stat().st_mtime_ns)).replace("default-src 'none';", "default-src 'none'; connect-src 'self'; worker-src 'self'; manifest-src 'self';")
                self.send(page,ctype='text/html; charset=utf-8');return
            if path=='/__ia/certificate' and self.command=='GET':self.send((ROOT/'lan-cert.pem').read_bytes(),ctype='application/x-pem-file',headers={'Content-Disposition':'attachment; filename="IA-Local-certificado.pem"'});return
            if path=='/__ia/bridge' and self.command=='POST':
                if not self.origin_ok() or self.headers.get('X-IA-CSRF')!=user['csrf']:self.send({'error':'Origen no permitido'},403);return
                body=json.loads(self.payload());command=body.get('command','request')
                if command=='install-helper':raise ValueError('La instalación inicial del ayudante requiere autorización una vez en el Mac.')
                if command=='gpu':raise ValueError('Utiliza la operación gpu-set con verificación en dos pasos.')
                if command=='authorize-ssd':
                    if user['role']!='admin':raise ValueError('Se requiere una cuenta administradora.')
                    self.send(self.server.dispatch.host_request(command,body,user['name']));return
                if command=='native-result':self.send(self.server.dispatch.host_result(body.get('id'),user['name']));return
                if command=='agent-link' and user['role'] in ('admin','control'):
                    service=body.get('service')
                    if service not in PROXIES.values():raise ValueError('Interfaz web no disponible para este motor.')
                    port=next(p for p,s in PROXIES.items() if s==service);target='https://'+self.headers['Host'].split(':')[0]+':'+str(port)+'/'
                    if service=='opencode':
                        text=run([HOME/'.opencode/bin/opencode','pair'],30);match=re.search(r'http://(?:127\.0\.0\.1|localhost):\d+(/auth/connect/\S+)',text)
                        if not match:raise RuntimeError('Arranca OpenCode antes de abrir su interfaz.')
                        target=target.rstrip('/')+match[1]
                    if service=='omlx':target+='admin'
                    self.send({'url':target});return
                if command!='request':raise ValueError('Esta función requiere el panel nativo del Mac.')
                path=body.get('path');method=body.get('method','GET')
                if path not in ('/status','/health','/export','/action'):raise ValueError('Ruta no permitida.')
                if path=='/action':
                    value=body.get('body',{});action=value.get('action')
                    if not (user['role']=='admin' and action in ALLOWED_ACTIONS|ADMIN_ACTIONS or user['role']=='control' and action in ALLOWED_ACTIONS):raise ValueError('Sin permiso para esta operación.')
                    if action in SENSITIVE:
                        if not security_status(user['name'])['enabled']:self.send({'error':'Configura el segundo factor de esta cuenta en IA Local en el Mac.','code':'second_factor_setup'},403);return
                        with access_db() as c:confirmed=c.execute('SELECT 1 FROM stepups WHERE session=? AND expires>?',(user['session'],time.time())).fetchone()
                        if not confirmed:self.send({'error':'Confirma tu código de verificación para continuar.','code':'step_up_required'},403);return
                    self.send(self.server.dispatch(action,value.get('value'),value.get('engine'),actor=user['name']));return
                if method!='GET':raise ValueError('Método no permitido.')
                result=http('http://127.0.0.1:8040',path,timeout=15,headers={'Authorization':'Bearer '+(ROOT/'token').read_text(encoding='utf-8')})
                if path=='/status':
                    result['remote']={'user':user['name'],'role':user['role'],'second_factor':security_status(user['name'])['enabled']}
                    if user['role']!='admin':result.get('lan',{}).pop('users',None)
                self.send(result);return
            self.send({'error':'Ruta desconocida'},404)
        except (OSError,ValueError,RuntimeError) as e:
            try:self.send({'error':str(e)},400)
            except OSError:pass
    def proxy(self):
        service=self.server.service;port=PORTS[service];upstream=http_client.HTTPConnection('127.0.0.1',port,timeout=300)
        upgrade=self.headers.get('Upgrade','').lower()=='websocket'
        headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','origin','connection','accept-encoding','cookie','x-forwarded-for','x-forwarded-host','x-forwarded-proto')}
        headers['Host']='127.0.0.1:'+str(port);headers['Accept-Encoding']='identity'
        if self.headers.get('Origin'):headers['Origin']='http://127.0.0.1:'+str(port)
        cookie=SimpleCookie(self.headers.get('Cookie',''))
        headers['Cookie']='; '.join(k+'='+m.value for k,m in cookie.items() if k!=COOKIE)
        if upgrade:headers['Connection']='Upgrade';headers['Upgrade']='websocket'
        body=self.payload() if self.command not in ('GET','HEAD') else None
        import inference_stats
        capture=inference_stats.Capture() if service in ('llama','strata-llama','omlx','exo') and self.path.split('?')[0] in ('/v1/chat/completions','/chat/completions','/completion') and self.command=='POST' else None
        success=False
        try:
            upstream.request(self.command,self.path,body=body,headers=headers);response=upstream.getresponse()
            self.send_response(response.status)
            for k,v in response.getheaders():
                if k.lower() in ('connection','transfer-encoding','content-length'):continue
                if k.lower()=='location':v=v.replace('http://127.0.0.1:'+str(port),'https://'+self.headers['Host']).replace('http://localhost:'+str(port),'https://'+self.headers['Host'])
                self.send_header(k,v)
            if upgrade and response.status==101:
                self.send_header('Connection','Upgrade');self.end_headers();self.wfile.flush();self.close_connection=True
                peer=upstream.sock;self.connection.settimeout(None);peer.settimeout(None)
                while True:
                    if not self.session():return
                    readable,_,_=select.select([self.connection,peer],[],[],60)
                    if not readable:continue
                    for current in readable:
                        data=current.recv(65536)
                        if not data:return
                        (peer if current is self.connection else self.connection).sendall(data)
            else:
                self.send_header('Connection','close');self.send_header('Cache-Control','no-store');self.end_headers();self.close_connection=True
                while chunk:=response.read1(65536):
                    if capture:capture.feed(chunk)
                    self.wfile.write(chunk);self.wfile.flush()
                success=response.status==200
        finally:
            upstream.close()
            if capture:
                try:model=json.loads(body or b'{}').get('model')
                except ValueError:model=None
                event('request',{'engine':service,'model':model,'source':'Interfaz HTTPS','success':success,**capture.finish()})
