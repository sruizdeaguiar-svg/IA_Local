"""Contract tests use synthetic API events; no provider credentials or billing."""
import os,sys,tempfile,unittest,json,ipaddress
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));_temp=tempfile.TemporaryDirectory();os.environ.setdefault('IA_LOCAL_HOME',_temp.name)
import external_providers as api
class ExternalProviders(unittest.TestCase):
 def test_presets_and_custom_protocols(self):
  self.assertIn('freellmapi',api.PRESETS);self.assertEqual(api.PRESETS['anthropic'][1],'anthropic');self.assertEqual(api.PRESETS['kimi'][1],'openai')
 def test_cloud_url_rejects_private_dns_and_plaintext(self):
  with patch.object(api.socket,'getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):self.assertRaises(ValueError,api.target,'https://example.test/v1')
  self.assertRaises(ValueError,api.target,'http://example.test/v1');self.assertRaises(ValueError,api.target,'https://user:private@example.test/v1')
 def test_anthropic_tools_system_and_results(self):
  body={'model':'synthetic','max_tokens':100,'messages':[{'role':'system','content':'System'},{'role':'user','content':'Hello'},{'role':'assistant','content':None,'tool_calls':[{'id':'call1','function':{'name':'sum','arguments':'{"a":1}'}}]},{'role':'tool','tool_call_id':'call1','content':'2'}],'tools':[{'type':'function','function':{'name':'sum','parameters':{'type':'object'}}}],'tool_choice':'auto'}
  d=api.to_anthropic(body);self.assertEqual(d['system'],'System');self.assertEqual(d['messages'][1]['content'][0]['type'],'tool_use');self.assertEqual(d['messages'][2]['content'][0]['tool_use_id'],'call1');self.assertEqual(d['tools'][0]['input_schema']['type'],'object')
 def test_anthropic_normal_response_and_usage(self):
  d=api.from_anthropic({'id':'m','model':'synthetic','content':[{'type':'text','text':'Hello'},{'type':'tool_use','id':'t','name':'sum','input':{'a':1}}],'stop_reason':'tool_use','usage':{'input_tokens':10,'cache_read_input_tokens':4,'output_tokens':3}})
  self.assertEqual(d['usage']['total_tokens'],17);self.assertEqual(d['choices'][0]['finish_reason'],'tool_calls');self.assertEqual(d['choices'][0]['message']['tool_calls'][0]['function']['name'],'sum')
 def test_stream_tools_usage_and_complete_end(self):
  events=[{'type':'message_start','message':{'id':'m','model':'synthetic','usage':{'input_tokens':4}}},{'type':'content_block_start','index':1,'content_block':{'type':'tool_use','id':'t','name':'sum','input':{}}},{'type':'content_block_delta','index':1,'delta':{'type':'input_json_delta','partial_json':'{"a":1}'}},{'type':'message_delta','delta':{'stop_reason':'tool_use'},'usage':{'output_tokens':8}},{'type':'message_stop'}]
  rows=list(api.anthropic_chunks([('data: '+json.dumps(e)+'\n').encode() for e in events]));self.assertEqual(rows[2]['choices'][0]['delta']['tool_calls'][0]['index'],0);self.assertEqual(rows[-1]['usage']['total_tokens'],12)
  self.assertRaises(RuntimeError,list,api.anthropic_chunks([('data: '+json.dumps(e)+'\n').encode() for e in events[:-1]]))
 def test_unsupported_anthropic_options_fail_explicitly(self):
  for option in ({'n':2},{'response_format':{'type':'json_object'}},{'tools':[{'type':'custom'}]}):self.assertRaises(ValueError,api.to_anthropic,{'model':'synthetic',**option})
if __name__=='__main__':unittest.main()
