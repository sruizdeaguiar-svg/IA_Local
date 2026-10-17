"""Headless Chromium E2E against each platform's real frozen executable.

The custom agent is a synthetic local HTTP fixture, not model inference. No
cloud credentials, weights or existing installations are used by this test.
"""
import json,socket,sys,time
from pathlib import Path
from packaged_session import PackagedSession
from playwright.sync_api import sync_playwright,expect
expect.set_options(timeout=45000)
with PackagedSession(sys.argv[1]) as app,sync_playwright() as pw:
 browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1365,'height':950});page.set_default_timeout(45000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto(app.request('/desktop-session')['url']);expect(page.locator('#connection')).to_have_text('Supervisor conectado');expect(page.locator('[data-action="start-all"]')).to_be_disabled()
  page.locator('[data-tab="settings"]').first.click();page.locator('#appLanguage').select_option('en');page.locator('#saveAppSettings').click();expect(page.get_by_role('tab',name='Settings',exact=True)).to_be_visible()
  expect(page.get_by_role('heading',name='Reset IA Local',exact=True)).to_be_visible();page.get_by_role('tab',name='Help',exact=True).click();expect(page.get_by_role('heading',name='IA Local user guide',exact=True)).to_be_visible()
  for name in ('Models','Evaluation','GPU memory','Updates','Activity','External APIs','Network and users','Server details','Integrations'):
   page.get_by_role('tab',name=name,exact=True).click();expect(page.locator('#connection')).to_have_text('Supervisor connected')
  page.get_by_role('tab',name='GPU memory',exact=True).click();expect(page.locator('#applyWired')).to_be_disabled();expect(page.locator('#installHelper')).to_be_disabled()
  # Review/register an actual synthetic HTTP process using the same UI controls.
  fixture=Path(app.temp.name)/'fixture_agent.py';fixture.write_text('''import argparse,json\nfrom http.server import BaseHTTPRequestHandler,HTTPServer\np=argparse.ArgumentParser();p.add_argument('--host');p.add_argument('--port',type=int);a=p.parse_args()\nclass H(BaseHTTPRequestHandler):\n def log_message(self,*a):pass\n def do_GET(self):\n  b=b'{"data":[]}';self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)\nHTTPServer((a.host,a.port),H).serve_forever()\n''',encoding='utf-8')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  definition={'id':'custom-qa-agent','name':'QA synthetic agent','kind':'agent','executable':sys.executable,'args':[str(fixture),'--host','{host}','--port','{port}'],'port':port,'health_path':'/v1/models','formats':[],'start_mode':'idle'}
  page.get_by_role('tab',name='Integrations',exact=True).click();page.locator('#integrationDefinition').fill(json.dumps(definition));page.on('dialog',lambda d:d.accept());page.locator('#integrationSave').click()
  page.get_by_role('tab',name='Control',exact=True).click();card=page.locator('[data-engine="custom-qa-agent"]');expect(card).to_be_visible();card.locator('[data-service="custom-qa-agent"]').click();expect(card.locator('[data-operation="stop"]')).to_be_enabled();expect(card.locator('.state')).not_to_have_text('Stopped')
  card.locator('[data-operation="stop"]').click();expect(card.locator('[data-operation="start"]')).to_be_enabled()
  # Full reset and recovery are exercised with synthetic profile state only.
  page.get_by_role('tab',name='Settings',exact=True).click();page.locator('#resetApplication').click();page.locator('#resetPhrase').fill('RESTABLECER');page.locator('#resetDialog button[value="confirm"]').click();expect(page.get_by_role('tab',name='Configuración',exact=True)).to_be_visible();expect(page.locator('#restoreReset')).to_be_enabled();page.locator('#restoreReset').click();expect(page.get_by_role('tab',name='Settings',exact=True)).to_be_visible()
  # Model discovery and destructive controls reflect empty model/active state.
  page.get_by_role('tab',name='Models',exact=True).click();expect(page.locator('#loadModel')).to_be_disabled();page.get_by_role('tab',name='Control',exact=True).click();expect(page.locator('#recoverMemory')).to_be_disabled()
  assert not errors,errors
  folder=Path('dist/browser-evidence');folder.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(folder/'panel.png'),full_page=True);(folder/'result.json').write_text(json.dumps({'platform':app.state['platform'],'browser':'Chromium headless','result':'passed','checks':['owner session','real state','ES/EN settings/help','all tabs','Mac-only controls disabled','reviewed agent register/start/stop','full reset/recovery','empty-model controls'],'fixture':'synthetic HTTP agent; no model inference'}),encoding='utf-8')
  print('Packaged browser E2E: passed')
 finally:browser.close()
