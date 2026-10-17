"""Isolated tests: no real profiles, models, credentials or services are changed."""
import os,sys,tempfile,unittest,ipaddress,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_session=tempfile.TemporaryDirectory();os.environ['IA_LOCAL_HOME']=_session.name
import core,integrations,remote_servers,app_settings,integration_assistant
class Integrations(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'backups').mkdir();self.oldports=dict(core.PORTS);self.oldnames=dict(core.NAMES)
  self.patches=[patch.object(m,'ROOT',self.root) for m in (core,integrations,remote_servers,app_settings,integration_assistant)]+[patch.object(integrations,'REGISTRY',self.root/'integrations.json')]
  for p in self.patches:p.start()
  core.init()
 def tearDown(self):
  core.PORTS.clear();core.PORTS.update(self.oldports);core.NAMES.clear();core.NAMES.update(self.oldnames)
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def draft(self):return dict(id='custom-test',name='Test',kind='server',executable=sys.executable,args=['--host','{host}','--port','{port}'],port=8771,formats=['GGUF'])
 def test_schema_rejects_shell_credentials_bad_templates_and_collisions(self):
  for change in ({'executable':'/bin/sh'},{'args':['--host','{host}','--port','{port}','--api-key','private']},{'args':['{host}','{port}','{oops}']},{'args':['{host}','{port}','{']},{'args':['{host}','{port}','{host.__class__}']},{'port':8040},{'port':True},{'formats':['universal']}):
   with self.subTest(change=change):self.assertRaises((ValueError,RuntimeError),integrations.validate,{**self.draft(),**change})
 def test_registration_is_idle_and_compatibility_is_declared(self):
  with patch.object(integrations,'port_open',return_value=False),patch.object(integrations,'spawn') as launch:
   integrations.register(self.draft());launch.assert_not_called();self.assertEqual(core.PORTS['custom-test'],8771)
   rows=integrations.attach_models([{'id':'a','format':'GGUF','engines':['llama']},{'id':'b','format':'MLX','engines':['mlx']}]);self.assertIn('custom-test',rows[0]['engines']);self.assertNotIn('custom-test',rows[1]['engines']);integrations.unregister('custom-test');self.assertNotIn('custom-test',core.PORTS)
 def test_passive_discovery_never_runs_discovered_binaries(self):
  with patch.object(integrations.subprocess,'run',side_effect=AssertionError('Discovery must be passive')):self.assertIn('items',integrations.scan())
 def test_remote_requires_current_private_subnet_and_v1(self):
  with patch.object(remote_servers,'networks',return_value=[ipaddress.ip_network('192.168.10.0/24')]):
   self.assertEqual(remote_servers.validate_url('http://192.168.10.20:8080/v1'),'http://192.168.10.20:8080/v1')
   for url in ['http://127.0.0.1:8080/v1','http://8.8.8.8/v1','http://10.0.0.1/v1','http://192.168.10.255/v1','http://user:pass@192.168.10.20/v1','http://192.168.10.20/v1?url=x','http://192.168.10.20/admin','http://192.168.10.20:99999/v1']:
    self.assertRaises(ValueError,remote_servers.validate_url,url)
 def test_remote_credentials_private_not_in_catalog(self):
  with patch.object(remote_servers,'networks',return_value=[ipaddress.ip_network('192.168.10.0/24')]):
   d={'id':'remote-test','name':'Test LAN','base_url':'http://192.168.10.20:8080/v1','context':4096,'api_key':'synthetic-test-only'}
   self.assertRaises(ValueError,remote_servers.register,d)
   remote_servers.register({**d,'allow_insecure':True});self.assertNotIn('synthetic-test-only',json.dumps(remote_servers.definitions()));self.assertEqual((self.root/'remote-credentials.json').stat().st_mode&0o777,0o600)
   with patch.object(remote_servers,'request',return_value={'data':[{'id':'m'}]}):remote_servers.connect('remote-test')
   self.assertEqual(remote_servers.models_remote()[0]['format'],'Remote API');remote_servers.disconnect('remote-test');self.assertFalse(remote_servers.connected('remote-test'))
 def test_settings_rejects_hidden_parameters_and_bad_types(self):
  for val in [{'token':'x'},{'poll_seconds':0},{'poll_seconds':True},{'language':'unknown'},{'theme':'blue'},{'update_hours':169}]:self.assertRaises(ValueError,app_settings.save,val)
  self.assertEqual(app_settings.save({'language':'en','poll_seconds':3})['language'],'en')
 def test_agent_json_parser_handles_both_clis(self):
  obj={'id':'custom-test','args':['{host}','{port}']};self.assertEqual(integration_assistant.parse('```json\n'+json.dumps(obj)+'\n```'),obj)
  self.assertEqual(integration_assistant.parse(json.dumps({'type':'text','part':{'text':json.dumps(obj)}})),obj)
  self.assertRaises(RuntimeError,integration_assistant.parse,'No compatible HTTP service available.')
if __name__=='__main__':unittest.main()
