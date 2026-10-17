"""Reset tests operate only on temporary application data; no real process stops."""
import os,sys,tempfile,unittest,json,sqlite3
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));_temp=tempfile.TemporaryDirectory();os.environ.setdefault('IA_LOCAL_HOME',_temp.name)
import core,lan,integrations,remote_servers,external_providers,app_settings,reset_state
class Reset(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'profile';self.root.mkdir();self.maps=(dict(core.PORTS),dict(core.NAMES));self.patches=[patch.object(m,'ROOT',self.root) for m in (core,lan,integrations,remote_servers,external_providers,app_settings,reset_state)]+[patch.object(integrations,'REGISTRY',self.root/'integrations.json'),patch.object(lan,'configure',return_value={})]
  for p in self.patches:p.start()
  core.init();lan.init()
 def tearDown(self):
  core.PORTS.clear();core.PORTS.update(self.maps[0]);core.NAMES.clear();core.NAMES.update(self.maps[1])
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_explicit_confirmation_before_backup_or_mutation(self):
  with patch.object(reset_state,'snapshot') as save:self.assertRaises(ValueError,reset_state.detach,{},lambda m:None);save.assert_not_called()
 def test_reset_and_restore_users_settings_and_program_preservation(self):
  model=Path(self.temp.name)/'weights.gguf';model.write_text('synthetic weights remain',encoding='utf-8');conversation=Path(self.temp.name)/'conversation.json';conversation.write_text('synthetic conversation remains',encoding='utf-8')
  lan.save_user({'name':'qa-user','password':'synthetic-qa-password-777','role':'admin'});core.write(self.root/'settings.json',{'language':'en','watch_models':True});core.write(self.root/'catalog.json',{'models':[{'id':'qa'}]});oldtoken=(self.root/'token').read_text(encoding='utf-8')
  result=reset_state.detach({'confirmation':'RESTABLECER'},lambda m:None)
  self.assertTrue(result['reset']);self.assertEqual(lan.users(),[]);self.assertEqual(core.read(self.root/'catalog.json')['models'],[]);self.assertTrue(core.read(self.root/'installation.json')['detached']);self.assertNotEqual(oldtoken,(self.root/'token').read_text(encoding='utf-8'));self.assertEqual(model.read_text(encoding='utf-8'),'synthetic weights remain');self.assertEqual(conversation.read_text(encoding='utf-8'),'synthetic conversation remains');self.assertEqual(core.available_services(),[])
  restored=reset_state.restore(lambda m:None);self.assertTrue(restored['restored']);self.assertEqual(lan.users()[0]['name'],'qa-user');self.assertEqual(core.read(self.root/'settings.json')['language'],'en');self.assertFalse(core.read(self.root/'settings.json')['lan_enabled']);self.assertEqual(core.read(self.root/'active.json'),{});self.assertFalse(core.read(self.root/'installation.json').get('detached',False))
 def test_restore_checks_integrity_and_does_not_execute_backup_contents(self):
  folder=reset_state.snapshot();manifest=core.read(folder/'manifest.json');manifest['files']['../outside']='x';core.write(folder/'manifest.json',manifest);self.assertRaisesRegex(RuntimeError,'integridad',reset_state.restore,lambda m:None)
 def test_only_owned_unchanged_identities_are_stopped(self):
  with patch.object(reset_state,'ledger',return_value={'owned':{'managed':True},'foreign':{'managed':False}}),patch.object(reset_state,'same',return_value=True),patch.object(reset_state,'stop') as stop:reset_state.detach({'confirmation':'RESTABLECER'},lambda m:None);stop.assert_called_once_with('owned')
if __name__=='__main__':unittest.main()
