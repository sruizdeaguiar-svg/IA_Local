"""Official EXO v1.0.71, restricted to this Mac. No libp2p sockets/mDNS.

Only the transport is local-only; Node/Master/Worker/inference and dashboard are
EXO's real implementation. Cluster features are deliberately unavailable.
"""
from pathlib import Path
import os,sys
ROOT=Path.home()/'Library/Application Support/IA-Local'
sys.path.insert(0,str(ROOT/'exo-local/src'))
internal=Path('/Applications/EXO.app/Contents/Resources/exo/_internal')
for key,value in {'EXO_HOME':ROOT/'exo-state','EXO_DEFAULT_MODELS_DIR':ROOT/'exo-models','EXO_MODELS_READ_ONLY_DIRS':ROOT/'exo-models-readonly','EXO_DASHBOARD_DIR':internal/'dashboard','EXO_RESOURCES_DIR':internal/'resources','EXO_OFFLINE':'true','EXO_MAX_CONCURRENT_REQUESTS':'1','EXO_ENABLE_IMAGE_MODELS':'false'}.items():os.environ[key]=str(value)
import anyio
from exo.routing.router import Router
from exo.api.main import API,Config,serve,InterceptLogger
class LocalTransport:
    async def gossipsub_subscribe(self,topic):pass
    async def gossipsub_unsubscribe(self,topic):pass
    async def gossipsub_publish(self,topic,data):pass
    async def recv(self):await anyio.sleep_forever()
Router.create=classmethod(lambda cls,identity,bootstrap_peers=(),listen_port=0:cls(handle=LocalTransport()))
async def loopback_api(self,ev):
    config=Config();config.bind=['127.0.0.1:'+str(self.port)];config.accesslog=None;config.errorlog='-';config.logger_class=InterceptLogger
    with anyio.CancelScope(shield=True):await serve(self.app,config,shutdown_trigger=ev.wait)
API.run_api=loopback_api
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
API._setup_cors=lambda self:self.app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:52415','http://localhost:52415'],allow_methods=['*'],allow_headers=['*'])
original_init=API.__init__
def local_api_init(self,*args,**kwargs):
    original_init(self,*args,**kwargs)
    @self.app.middleware('http')
    async def exclusive_instance(request,call_next):
        if request.method=='POST' and request.url.path in ('/instance','/place_instance'):
            import json
            active_file=ROOT/'active.json'
            active=json.loads(active_file.read_text()) if active_file.exists() else {}
            if active.get('id') and active.get('engine')!='exo':return JSONResponse({'error':'Libera el modelo del otro motor en IA Local antes de cargar EXO.'},409)
            if self.state.instances:return JSONResponse({'error':'Solo se permite una instancia. Elimina la actual antes de cambiar de modelo.'},409)
        return await call_next(request)
API.__init__=local_api_init

def prepare_catalog():
    import json
    from exo.shared.models.model_cards import ModelCard
    directory=ROOT/'exo-models-readonly';directory.mkdir(exist_ok=True)
    catalog=json.loads((ROOT/'catalog.json').read_text());mapped={}
    async def save():
        for model in catalog['models']:
            path=Path(model.get('path','/nonexistent'))
            if model.get('format') not in ('MLX','Safetensors') or not (path/'config.json').is_file():continue
            cfg=json.loads((path/'config.json').read_text())
            if cfg.get('model_type') not in ('qwen2','qwen3','qwen3_moe'):continue
            if not cfg.get('num_hidden_layers') or not cfg.get('hidden_size'):continue
            alias='IA-Local/'+model['id'];target=directory/alias.replace('/','--')
            if not list(path.glob('*.safetensors.index.json')) and (path/'model.safetensors').is_file():
                # EXO requires an index even for a single-file checkpoint.
                # Build a metadata-only view; never change the original checkpoint.
                import struct
                if target.is_symlink() and target.resolve()==path.resolve():target.unlink()
                target.mkdir(exist_ok=True)
                for item in path.iterdir():
                    link=target/item.name
                    if item.is_file() and not item.name.startswith('._') and not link.exists():link.symlink_to(item)
                with open(path/'model.safetensors','rb') as weights:
                    length=struct.unpack('<Q',weights.read(8))[0]
                    if length>64*2**20:raise ValueError('Cabecera safetensors excesiva.')
                    header=json.loads(weights.read(length))
                mapping={name:'model.safetensors' for name in header if name!='__metadata__'}
                (target/'model.safetensors.index.json').write_text(json.dumps({'metadata':{'total_size':model['bytes']},'weight_map':mapping}))
            elif not target.exists():target.symlink_to(path,target_is_directory=True)
            card=ModelCard(model_id=alias,storage_size={'in_bytes':model['bytes']},n_layers=cfg['num_hidden_layers'],hidden_size=cfg['hidden_size'],supports_tensor=False,num_key_value_heads=cfg.get('num_key_value_heads'),context_length=model['context'],trust_remote_code=False,tasks=['TextGeneration'],is_custom=True)
            await card.save_to_custom_dir();mapped[model['id']]=alias
    anyio.run(save)
    (ROOT/'exo-catalog.json').write_text(json.dumps(mapped))
    return mapped

if __name__=="__main__":
    prepare_catalog()
    from exo.main import main
    main()
