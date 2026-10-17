import os,sys,tempfile,unittest,sqlite3,json,time,base64,hmac,struct,socket,importlib.util,re
from pathlib import Path
sandbox=tempfile.TemporaryDirectory();os.environ['IA_LOCAL_HOME']=sandbox.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lan,comparison,inference_stats,operations,threading,core
from unittest.mock import patch
from contextlib import closing
lan.init()
class Management(unittest.TestCase):
 def test_totp_enrollment_and_replay(self):
  lan.save_user({'name':'test-admin','password':'synthetic-password-987','role':'admin'})
  pending=lan.totp_begin('test-admin');self.assertFalse(lan.security_status('test-admin')['enabled'])
  step=int(time.time()//30);digest=hmac.new(base64.b32decode(pending['secret']),struct.pack('>Q',step),'sha1').digest();off=digest[-1]&15;code=str((struct.unpack('>I',digest[off:off+4])[0]&0x7fffffff)%1000000).zfill(6)
  self.assertFalse(lan.totp_check('test-admin',code));self.assertTrue(lan.totp_check('test-admin',code,True));self.assertFalse(lan.totp_check('test-admin',code));self.assertTrue(lan.security_status('test-admin')['enabled'])
  self.assertRaises(ValueError,lan.totp_begin,'test-admin');self.assertFalse(lan.totp_check('test-admin','123x00'))
 def test_aggregation_failure_unknown_missing_values(self):
  with closing(sqlite3.connect(':memory:')) as db:
   db.execute('CREATE TABLE events(time REAL,kind TEXT,data TEXT)')
   for d in [{'success':True,'timings':{'predicted_per_second':10},'wall_s':2,'ttft_s':.5},{'success':True,'timings':{'predicted_per_second':20},'wall_s':4},{'success':False,'timings':{'predicted_per_second':999},'wall_s':99},{'timings':{'predicted_per_second':888}}]:db.execute('INSERT INTO events VALUES(?,?,?)',(time.time(),'request',json.dumps(d)))
   result=inference_stats.summary(db);day=result['periods'][0];self.assertEqual(day['count'],4);self.assertEqual(day['valid'],2);self.assertEqual(day['failed'],1);self.assertEqual(day['unknown'],1);self.assertEqual(day['generation_tok_s'],15);self.assertEqual(day['ttft_samples'],1);self.assertEqual(day['total_s'],3)
   self.assertEqual(inference_stats.summary(db)['periods'][0]['count'],4)
 def test_comparison_no_fabricated_equivalence(self):
  model={'id':'m','engines':['llama','mlx'],'context':8192,'max_context':65536}
  results=[{'id':'r','model':'m','data':{'engine':'llama','status':'passed','parameters':{'context':4096},'raw':[{'n_prompt':512,'avg_ts':100},{'n_gen':128,'avg_ts':20}],'functional':{'ttft_s':.2}}}]
  a,b=comparison.build([model],results,[])['m'];self.assertFalse(a['same_context']);self.assertEqual(a['generation_tok_s'],20);self.assertEqual(b['status'],'Sin mediciones');self.assertNotIn('generation_tok_s',b)
 def test_stream_fragmentation_and_no_space(self):
  c=inference_stats.Capture()
  for part in [b'da',b'ta:{"choices":[{"delta":{"reasoning_content":"test"}}]}\n\n',b'data: {"usage":{"completion_tokens":3},"timings":{"predicted_per_second":12}}\n\n']:c.feed(part)
  d=c.finish();self.assertEqual(d['usage']['completion_tokens'],3);self.assertEqual(d['timings']['predicted_per_second'],12);self.assertIsNotNone(d['ttft_s']);self.assertNotIn('test',json.dumps(d))
 def test_batch_continues_after_failure_and_keeps_order(self):
  model={'id':'batch-model','engines':['llama','mlx','lmstudio'],'context':8192};order=[]
  def bench(mid,engine,cancel,progress):
   order.append(engine)
   if engine=='mlx':raise RuntimeError('Fallo del motor')
   return {'id':'result-'+engine,'status':'passed'}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all') as free,patch.object(operations,'benchmark',side_effect=bench):
   result=operations.benchmark_all('batch-model',threading.Event(),lambda message:None)
  self.assertEqual(order,['llama','mlx','lmstudio']);self.assertEqual(result['status'],'partial');self.assertEqual([r['status'] for r in result['rows']],['passed','failed','passed']);self.assertGreaterEqual(free.call_count,4)
 def test_batch_cancel_releases_and_retains_completed(self):
  flag=threading.Event();model={'id':'cancel-model','engines':['llama','mlx'],'context':4096}
  def bench(*args):flag.set();return {'id':'done-first','status':'passed'}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all') as free,patch.object(operations,'benchmark',side_effect=bench) as execute:
   result=operations.benchmark_all('cancel-model',flag,lambda message:None)
  self.assertEqual(execute.call_count,1);self.assertEqual(result['status'],'cancelled');self.assertEqual(result['rows'][0]['result_id'],'done-first');self.assertGreaterEqual(free.call_count,2)
 def test_context_cannot_exceed_model_limit(self):
  with patch.object(operations,'get_model',return_value={'id':'small','context':4096,'max_context':32768}):
   self.assertRaises(ValueError,operations.evaluation_model,{'id':'small','context':65536})
   self.assertRaises(ValueError,operations.evaluation_model,{'id':'small','context':1024})
 def test_privilege_allowlist(self):
  self.assertIn('gpu-set',lan.SENSITIVE);self.assertIn('update',lan.SENSITIVE);self.assertNotIn('gpu-set',lan.ALLOWED_ACTIONS)
 def test_shared_ui_actions_have_authorized_web_routes(self):
  ui=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8');actions=set(re.findall(r"action\('([a-z-]+)'",ui))|set(re.findall(r'data-action="([a-z-]+)"',ui))
  self.assertFalse(actions-lan.ALLOWED_ACTIONS-lan.ADMIN_ACTIONS)
 def test_ports_cannot_duplicate_primary_or_auxiliary(self):
  self.assertEqual(len(core.validate_ports()),len(core.PORTS)+len(core.AUX_PORTS))
  for duplicate in (core.PORTS['strata'],core.AUX_PORTS['mirai-backend'],8440):
   with self.subTest(port=duplicate):self.assertRaises(RuntimeError,core.validate_ports,{**core.PORTS,'strata-llama':duplicate})
 def test_foreign_listener_blocks_load_before_releasing_current_model(self):
  with socket.socket() as foreign:
   foreign.bind(('127.0.0.1',0));foreign.listen();port=foreign.getsockname()[1]
   with patch.dict(core.PORTS,{'strata-llama':port}),patch.object(core,'listener_pids',return_value={os.getpid()}),patch.object(core,'get_model',return_value={'id':'test','engines':['strata-llama']}),patch.object(core,'unload_all') as unload,patch.object(core,'start') as start:
    self.assertRaisesRegex(RuntimeError,'ocupado por otro proceso',core.load,'test','strata-llama')
    unload.assert_not_called();start.assert_not_called()
   self.assertEqual(foreign.getsockname()[1],port)
 def test_mirai_backend_collision_blocks_router_start(self):
  with patch.object(core.socket,'socket'),patch.object(core,'port_open',side_effect=lambda p:p==8001),patch.object(core,'listener_pids',return_value={1}),patch.object(core,'expected_listener',return_value=False),patch.object(core,'run') as run:
   self.assertRaisesRegex(RuntimeError,'8001',core.start,'mirai');run.assert_not_called()
 def test_lmstudio_embedded_official_api_is_recognized(self):
  with patch.object(core,'find',return_value=None),patch.object(core.psutil,'Process') as process:
   p=process.return_value;p.uids.return_value.real=getattr(os,'getuid',lambda:0)();p.username.return_value=core.psutil.Process().username();p.cmdline.return_value=['/Applications/LM Studio.app/Contents/MacOS/LM Studio','--run-as-service'];p.exe.return_value=p.cmdline.return_value[0]
   self.assertTrue(core.expected_listener('lmstudio',123))
   p.exe.return_value='/tmp/LM Studio';self.assertFalse(core.expected_listener('lmstudio',123))
 def test_alternative_stop_does_not_stop_original_strata(self):
  with patch.object(core,'stop_process') as stop,patch.object(core,'run') as run:
   core.stop('strata-llama');stop.assert_called_once_with('strata-llama');run.assert_not_called()
 @unittest.skipUnless((Path(__file__).resolve().parents[2]/'strata-mac/manager_control.py').exists(),'Adaptador Strata heredado opcional no incluido')
 def test_old_strata_shortcuts_use_same_ports_as_ia_local(self):
  source=Path(__file__).resolve().parents[2]/'strata-mac/manager_control.py';spec=importlib.util.spec_from_file_location('legacy_ports_test',source);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
  self.assertEqual(legacy.port_for('strata'),core.PORTS['strata'])
  self.assertEqual(legacy.port_for('qwen36'),core.PORTS['strata-llama'])
  self.assertEqual(legacy.port_for('new-model'),core.PORTS['strata-llama'])
 def test_optimization_series_separates_tuning_from_evaluation(self):
  model={'id':'opt-mixed','context':8192,'engines':['llama','mlx','strata-llama']};calls=[]
  def tune(mid,engine,*args):
   calls.append(engine);profiles=core.read(core.ROOT/'profiles.json',{});profiles[engine+'/'+mid]={'threads':4};core.write(core.ROOT/'profiles.json',profiles)
   return {'report':{'id':'opt-'+engine,'status':'passed','selected':{'threads':4}}}
  def evaluate(mid,engine,*args):calls.append(engine);return {'id':'bench-'+engine,'status':'passed'}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all'),patch.object(operations,'optimize',side_effect=tune),patch.object(operations,'benchmark',side_effect=evaluate):
   result=operations.optimize_all({'id':model['id'],'context':8192},threading.Event(),lambda message:None)
  self.assertEqual(calls,model['engines']);self.assertEqual(result['status'],'passed');self.assertEqual([r['mode'] for r in result['rows']],['optimize','evaluate','optimize']);self.assertEqual(result['evaluation_only_engines'],['mlx'])
  self.assertIsNone(result['rows'][1]['selected']);self.assertIn('llama/opt-mixed',core.read(core.ROOT/'profiles.json'));self.assertIn('strata-llama/opt-mixed',core.read(core.ROOT/'profiles.json'));self.assertIn('optimize-all',lan.ALLOWED_ACTIONS)
 def test_optimization_series_partial_failure_preserves_completed(self):
  model={'id':'opt-partial','context':4096,'engines':['llama','mlx']}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all'),patch.object(operations,'optimize',side_effect=RuntimeError('No hay perfil válido')),patch.object(operations,'benchmark',return_value={'id':'bench-mlx','status':'passed'}):
   result=operations.optimize_all(model['id'],threading.Event(),lambda message:None)
  self.assertEqual(result['status'],'partial');self.assertEqual([r['status'] for r in result['rows']],['failed','passed']);self.assertEqual(result['rows'][1]['result_id'],'bench-mlx')
 def test_optimization_series_cancel_releases_models(self):
  flag=threading.Event();model={'id':'opt-cancel','context':4096,'engines':['llama','mlx']}
  def tune(*args):flag.set();return {'report':{'id':'complete-first','status':'passed','selected':{'threads':4}}}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all') as release,patch.object(operations,'optimize',side_effect=tune),patch.object(operations,'benchmark') as evaluate:
   result=operations.optimize_all(model['id'],flag,lambda message:None)
  self.assertEqual(result['status'],'cancelled');self.assertEqual(result['rows'][0]['result_id'],'complete-first');evaluate.assert_not_called();self.assertGreaterEqual(release.call_count,3)
 def test_optimization_series_cleanup_failure_stops_next_engine(self):
  model={'id':'opt-cleanup','context':4096,'engines':['llama','mlx']}
  with patch.object(operations,'evaluation_model',return_value=model),patch.object(operations,'unload_all',side_effect=[None,RuntimeError('Proceso todavía residente'),None]),patch.object(operations,'optimize',return_value={'report':{'id':'opt-first','status':'passed'}}),patch.object(operations,'benchmark') as evaluate:
   result=operations.optimize_all(model['id'],threading.Event(),lambda message:None)
  self.assertEqual(result['status'],'failed');self.assertIn('cleanup_error',result);evaluate.assert_not_called();self.assertNotIn('Modelos descargados',result['message'])
 def test_hermes_exec_transition_waits_for_health(self):
  record={'pid':42,'exe':'/initial/launcher','birth':1,'argv_hash':'initial','managed':True}
  changed={'pid':42,'exe':'/installed/python','birth':1,'argv_hash':'settled'}
  with patch.object(core,'check_service_ports'),patch.object(core,'probe',side_effect=[None,None,{'ok':True}]),patch.object(core,'find',return_value=None),patch.object(core,'spawn'),patch.object(core,'ledger',return_value={'hermes':record}),patch.object(core,'identity',return_value=changed),patch.object(core.time,'sleep'):
   core.start('hermes')
 def test_agent_group_uses_only_linked_available_services(self):
  import supervisor
  class Immediate:
   def __init__(self,target,**kw):self.target=target
   def start(self):self.target()
  with patch.object(supervisor.threading,'Thread',Immediate),patch.object(supervisor,'available_services',return_value=['custom-agent']),patch.dict(supervisor.NAMES,{'custom-agent':'QA agent'}),patch.object(supervisor.integrations,'definition',return_value={'kind':'agent'}),patch.object(supervisor,'start') as start,patch.object(supervisor,'pending_gpu',return_value=False),patch.object(supervisor,'lock',lambda *a,**k:__import__('contextlib').nullcontext()):
   old=supervisor.JOBS;supervisor.JOBS={}
   try:
    jid=supervisor.job('agents-start')['job'];self.assertEqual(supervisor.JOBS[jid]['state'],'done');self.assertEqual([c.args[0] for c in start.call_args_list],['custom-agent'])
   finally:supervisor.JOBS=old
 def test_agents_start_after_cancelled_benchmark_is_independent(self):
  import supervisor
  class ImmediateThread:
   def __init__(self,target,**kwargs):self.target=target
   def start(self):self.target()
  supervisor.CANCEL.set()
  try:
   with patch.dict(supervisor.JOBS,{},clear=True),patch.object(supervisor,'available_services',return_value=['opencode','hermes']),patch.object(supervisor,'start') as start,patch.object(supervisor.threading,'Thread',ImmediateThread):
    jid=supervisor.job('agents-start')['job'];self.assertEqual(supervisor.JOBS[jid]['state'],'done');self.assertEqual([c.args[0] for c in start.call_args_list],['opencode','hermes'])
  finally:supervisor.CANCEL.clear()
 def test_opencode_selection_preserves_cloud_and_hermes_bytes(self):
  import yaml
  with tempfile.TemporaryDirectory() as t:
   home=Path(t);oc=home/'.config/opencode/opencode.json';hc=home/'.hermes/config.yaml';oc.parent.mkdir(parents=True);hc.parent.mkdir(parents=True)
   cloud={'openai':{'unchanged':'synthetic'},'freellmapi':{'unchanged':'synthetic'}};core.write(oc,{'providers':cloud,'model':'openai/test'});hc.write_text('model:\n  provider: openai\n  default: test\n',encoding='utf-8');prior=hc.read_bytes();m={'id':'m','label':'Modelo','context':4096,'engines':['llama']}
   with patch.object(operations,'HOME',home),patch.object(operations,'get_model',return_value=m),patch.object(operations,'models',return_value=[m]),patch.object(operations,'probe',return_value=None):operations.configure_agents('m',engine='llama',targets=['opencode'])
   result=core.read(oc);self.assertEqual(result['model'],'ia-local/llama/m');self.assertEqual(hc.read_bytes(),prior)
   for name,value in cloud.items():self.assertEqual(result['providers'][name],value)
 def test_hermes_selection_preserves_opencode_and_cloud(self):
  import yaml
  with tempfile.TemporaryDirectory() as t:
   home=Path(t);oc=home/'.config/opencode/opencode.json';hc=home/'.hermes/config.yaml';oc.parent.mkdir(parents=True);hc.parent.mkdir(parents=True)
   core.write(oc,{'model':'openai/test'});prior=oc.read_bytes();cloud={'openai':{'unchanged':'synthetic'},'freellmapi':{'unchanged':'synthetic'}};hc.write_text(yaml.safe_dump({'model':{'provider':'openai','default':'test'},'providers':cloud}),encoding='utf-8');m={'id':'m','label':'Modelo','context':65536,'engines':['strata-llama']}
   with patch.object(operations,'HOME',home),patch.object(operations,'get_model',return_value=m),patch.object(operations,'models',return_value=[m]):operations.configure_agents('m',engine='strata-llama',targets=['hermes'])
   result=yaml.safe_load(hc.read_text(encoding='utf-8'));self.assertEqual(oc.read_bytes(),prior);self.assertEqual(result['model']['default'],'strata-llama/m');self.assertEqual(result['model']['context_length'],65536)
   for name,value in cloud.items():self.assertEqual(result['providers'][name],value)
 def test_hermes_short_context_rejected_before_writing(self):
  with patch.object(operations,'get_model',return_value={'id':'m','context':4096}),patch.object(operations,'write') as write:
   self.assertRaisesRegex(RuntimeError,'64000',operations.configure_agents,'m',targets=['hermes']);write.assert_not_called()
 def test_active_agent_passes_actual_engine_after_readiness(self):
  active={'id':'m','public_model':'public-m','engine':'llama','context':65536};model={'id':'m','context':65536,'engines':['llama']}
  with patch.object(operations,'read',return_value=active),patch.object(operations,'get_model',return_value=model),patch.object(operations,'check_service_ports'),patch.object(operations,'probe',return_value={'data':[]}),patch.object(operations,'http',return_value={'choices':[{}]}) as http,patch.object(operations,'configure_agents',return_value={}) as configure:
   operations.configure_active_agents('opencode');configure.assert_called_once_with('m',engine='llama',targets=['opencode']);self.assertEqual(http.call_args.args[2]['model'],'public-m')
 def test_runtime_upgrade_replaces_symlinks_in_fresh_tree(self):
  import updater
  with tempfile.TemporaryDirectory() as t:
   parent=Path(t);incoming=parent/'incoming';target=parent/'runtime';incoming.mkdir();target.mkdir()
   for folder,version in ((incoming,'new'),(target,'old')):
    (folder/'llama-server').write_text(version,encoding='utf-8');(folder/('lib-'+version)).write_text(version,encoding='utf-8');(folder/'libggml.dylib').symlink_to('lib-'+version)
   with patch.object(updater,'run',return_value='version'):updater.replace_llama_runtime(incoming,target)
   self.assertEqual((target/'llama-server').read_text(encoding='utf-8'),'new');self.assertEqual((target/'libggml.dylib').read_text(encoding='utf-8'),'new');self.assertFalse((target/'lib-old').exists())
 def test_runtime_upgrade_validation_failure_restores_original(self):
  import updater
  with tempfile.TemporaryDirectory() as t:
   parent=Path(t);incoming=parent/'incoming';target=parent/'runtime';incoming.mkdir();target.mkdir();(incoming/'llama-server').write_text('new',encoding='utf-8');(target/'llama-server').write_text('old',encoding='utf-8')
   with patch.object(updater,'run',side_effect=['ok',RuntimeError('Validación fallida')]):self.assertRaises(RuntimeError,updater.replace_llama_runtime,incoming,target)
   self.assertEqual((target/'llama-server').read_text(encoding='utf-8'),'old');self.assertFalse(list(parent.glob('runtime.ia-*')))
if __name__=='__main__':
 result=unittest.main(exit=False).result;sandbox.cleanup();sys.exit(not result.wasSuccessful())
