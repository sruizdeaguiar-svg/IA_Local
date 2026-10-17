"""Portable per-user launcher. Starts a loopback supervisor and opens its panel.

A PyInstaller build bundles the shared backend and Python dependencies. From
source: python portable_launcher.py [--data DIRECTORY] [--port 8040]. Engines,
weights and credentials are never bundled. No administrator account is needed.
"""
from pathlib import Path
import argparse,json,os,runpy,shutil,subprocess,sys,time,urllib.request,webbrowser
HERE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))

def prepare(data):
    from portable_security import secure_directory
    secure_directory(data)
    from install_clean import BACKEND_FILES
    # Static assets are refreshed; configuration and runtime databases are not.
    for name in BACKEND_FILES:
        if name.endswith('.py'):continue
        source=HERE/name
        if source.is_file():shutil.copy2(source,data/name)
    fresh=not (data/'installation.json').exists()
    if fresh:
        from core import write
        write(data/'installation.json',{'clean':True,'detached':True,'linked_services':[],'version':'1.2.0','layout':'portable'})
        write(data/'settings.json',{'language':'es','theme':'auto','watch_models':False,'daily_updates':False,'watch_integrations':True,'model_dirs':[]})
    return fresh

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data');parser.add_argument('--port',type=int,default=8040);parser.add_argument('--serve',action='store_true');parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if args.data:os.environ['IA_LOCAL_HOME']=str(Path(args.data).expanduser().absolute())
    os.environ['IA_LOCAL_PORT']=str(args.port);os.environ['IA_DESKTOP_UI']='1'
    from core import ROOT,OPENER
    if not 1024<=args.port<=65535:raise RuntimeError('Puerto no válido.')
    if args.serve:
        from portable_security import secure_directory
        secure_directory(ROOT)
        runpy.run_module('supervisor',run_name='__main__');return
    prepare(ROOT)
    from core import init
    init();token=(ROOT/'token').read_text(encoding='utf-8')
    def request(path):
        with OPENER.open(urllib.request.Request(f'http://127.0.0.1:{args.port}'+path,headers={'Authorization':'Bearer '+token}),timeout=2) as response:return json.load(response)
    try:request('/health')
    except urllib.error.HTTPError:raise RuntimeError('El puerto pertenece a otro perfil o aplicación. Usa otro puerto; no se detiene el proceso existente.') from None
    except (OSError,ValueError):
        command=[sys.executable]+([] if getattr(sys,'frozen',False) else [str(Path(__file__).resolve())])+['--serve','--data',str(ROOT),'--port',str(args.port)]
        (ROOT/'logs').mkdir(exist_ok=True)
        with (ROOT/'logs/portable-supervisor.log').open('ab') as log:
            child=subprocess.Popen(command,env={**os.environ,**({'PYINSTALLER_RESET_ENVIRONMENT':'1'} if getattr(sys,'frozen',False) else {})},stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=os.name!='nt',creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.DETACHED_PROCESS) if os.name=='nt' else 0)
        until=time.monotonic()+40
        while True:
            try:request('/health');break
            except Exception:
                if child.poll() is not None or time.monotonic()>until:raise RuntimeError('El supervisor no arrancó. Revisa logs/portable-supervisor.log.') from None
                time.sleep(.25)
    if not args.no_browser:webbrowser.open(request('/desktop-session')['url'])
    # Do not print one-use capabilities, cookies or the private bearer to logs.
    print('IA Local: supervisor disponible en loopback. Datos privados: '+str(ROOT))

if __name__=='__main__':
    try:main()
    except Exception as error:
        message='IA Local: '+str(error)
        if os.name=='nt' and '--no-browser' not in sys.argv and '--serve' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,message,'IA Local',0x10)
        else:print(message,file=sys.stderr)
        sys.exit(1)
