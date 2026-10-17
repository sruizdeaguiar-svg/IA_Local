"""Isolated real HTTP lifecycle of the portable owner UI, security and reset."""
import http.cookiejar,json,os,re,socket,subprocess,sys,tempfile,time,unittest,urllib.error,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
class PortableHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)/'profile'
  with socket.socket() as s:s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1]
  cls.base='http://127.0.0.1:'+str(cls.port)
  env={**os.environ,'IA_LOCAL_HOME':str(cls.root)}
  subprocess.run([sys.executable,str(HERE/'portable_launcher.py'),'--data',str(cls.root),'--port',str(cls.port),'--no-browser'],env=env,check=True,capture_output=True,timeout=60)
  # Discover only our exact child command/creation identity for teardown.
  import psutil
  cls.server=next(p for p in psutil.process_iter(['cmdline']) if p.info['cmdline'] and '--serve' in p.info['cmdline'] and str(cls.root) in p.info['cmdline'])
  cls.token=(cls.root/'token').read_text()
  cls.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 @classmethod
 def tearDownClass(cls):
  cls.server.terminate()
  try:cls.server.wait(10)
  except Exception:cls.server.kill();cls.server.wait(10)
  cls.temp.cleanup()
 def request(self,path,body=None,headers=None,opener=None):
  req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
  return (opener or self.opener).open(req,timeout=30)
 def session(self):
  with self.request('/desktop-session',headers={'Authorization':'Bearer '+self.token}) as r:url=json.load(r)['url']
  jar=http.cookiejar.CookieJar();browser=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
  with browser.open(url) as r:html=r.read().decode();base=urllib.parse.urlsplit(r.url).path
  csrf=json.loads(re.search(r'csrf=("[^"]+")',html)[1]);return browser,base,csrf,url,html
 def test_owner_session_cookie_one_use_and_csrf(self):
  browser,base,csrf,url,html=self.session();self.assertIn('window.iaDesktop=true',html);self.assertIn("'X-IA-CSRF':csrf",html);self.assertNotIn('http-equiv="Content-Security-Policy"',html);self.assertNotIn(self.token,html)
  with self.assertRaises(urllib.error.HTTPError) as error:browser.open(url)
  self.assertEqual(error.exception.code,401)
  body={'path':'/status'}
  for headers in ({},{'Origin':self.base},{'Origin':'http://evil.example','X-IA-CSRF':csrf}):
   with self.assertRaises(urllib.error.HTTPError) as error:self.request(base+'bridge',body,headers,browser)
   self.assertEqual(error.exception.code,403)
  headers={'Origin':self.base,'X-IA-CSRF':csrf}
  with self.request(base+'bridge',body,headers,browser) as r:data=json.load(r)
  until=time.monotonic()+15
  while data.get('starting') and time.monotonic()<until:
   time.sleep(.25)
   with self.request(base+'bridge',body,headers,browser) as r:data=json.load(r)
  self.assertEqual(data['services'],[]);self.assertEqual(data['models'],[]);self.assertEqual(data['lan']['users'],[])
  with self.assertRaises(urllib.error.HTTPError):self.request(base+'bridge',{'path':'http://evil.example/status'},headers,browser)
  # Exact Host blocks DNS rebinding, even with a valid owner cookie.
  with self.assertRaises(urllib.error.HTTPError) as error:self.request(base+'bridge',body,{**headers,'Host':'evil.example'},browser)
  self.assertEqual(error.exception.code,403)
 def test_settings_and_reversible_full_reset(self):
  browser,base,csrf,_,_=self.session();headers={'Origin':self.base,'X-IA-CSRF':csrf}
  def action(a,value=None):
   with self.request(base+'bridge',{'path':'/action','method':'POST','body':{'action':a,'value':value}},headers,browser) as r:jid=json.load(r)['job']
   until=time.monotonic()+20
   while time.monotonic()<until:
    time.sleep(.15)
    with self.request(base+'bridge',{'path':'/status'},headers,browser) as r:d=json.load(r)
    job=next((j for j in d.get('jobs',[]) if j['id']==jid),None)
    if job and job['state']!='running':self.assertEqual(job['state'],'done',job);return d
   self.fail('Job timeout')
  action('save-settings',{'language':'en','poll_seconds':3})
  action('user-save',{'name':'qa-user','password':'synthetic-only-passphrase','role':'admin','enabled':True})
  preserved=self.root/'user-model.gguf';preserved.write_bytes(b'synthetic marker; never loaded')
  d=action('reset-application',{'confirmation':'RESTABLECER'});self.assertEqual(d['lan']['users'],[]);self.assertTrue(d['reset_state']['available']);self.assertTrue(preserved.exists());self.assertEqual(d['services'],[])
  d=action('restore-reset');self.assertEqual(d['lan']['users'][0]['name'],'qa-user');self.assertEqual(d['settings']['language'],'en');self.assertFalse(d['lan']['enabled']);self.assertTrue(preserved.exists())
if __name__=='__main__':unittest.main()
