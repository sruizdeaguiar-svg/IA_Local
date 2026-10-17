"""Fresh, offline installation into user-selected app/data directories.

No existing directory is replaced. Only allowlisted payload files are copied;
no accounts, keys, model paths, histories or network access are preconfigured.
The bundled Python runtime makes the installed backend independent of Strata.
"""
from pathlib import Path
import argparse,json,os,shutil,plistlib,hashlib,sys,platform
BACKEND_FILES=('desktop_server.py','portable_security.py','core.py','operations.py','supervisor.py','lan.py','privileged.py','comparison.py','inference_stats.py','memory_status.py','updater.py','exo_local.py','integrations.py','integration_assistant.py','remote_servers.py','app_settings.py','external_providers.py','gpu_telemetry.py','reset_state.py','index.html','manifest.webmanifest','sw.js','offline.html','icon-180.png','icon-192.png','icon-512.png','MANUAL_ES.md','MANUAL_EN.md','i18n-en.json')
def install(payload_app,applications,data,desktop=False,port=8040):
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise RuntimeError('Esta compilación requiere macOS en Apple Silicon.')
    applications=Path(applications).expanduser().absolute();data=Path(data).expanduser().absolute();source=Path(payload_app).absolute();app=applications/'IA Local.app'
    if app.exists():raise FileExistsError('Ya existe IA Local.app en esta carpeta. Elige otra ubicación; no se sustituye tu instalación.')
    if data.exists() and any(data.iterdir()):raise FileExistsError('La carpeta de datos no está vacía. Elige una nueva; se conserva su contenido.')
    if data==app or app in data.parents or data in app.parents:raise ValueError('La carpeta de datos debe estar fuera de la aplicación.')
    for parent in (applications,data.parent):
        parent.mkdir(parents=True,exist_ok=True)
        if not os.access(parent,os.W_OK):raise PermissionError('Elige una carpeta en la que tu usuario pueda escribir.')
    app_created=False;data_created=not data.exists()
    try:
        shutil.copytree(source,app,symlinks=True,ignore=shutil.ignore_patterns('._*','__pycache__'));app_created=True
        data.mkdir(mode=0o700,exist_ok=True);data.chmod(0o700)
        for file in BACKEND_FILES:
            src=source/'Contents/Resources/backend'/file
            if not src.is_file():raise FileNotFoundError('Falta un archivo del paquete: '+file)
            shutil.copy2(src,data/file);(data/file).chmod(0o600)
        def write(name,obj):
            path=data/name;path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');path.chmod(0o600)
        write('installation.json',{'clean':True,'detached':True,'linked_services':[],'version':'1.2.0','layout':'user-selected','python':'bundled'})
        write('catalog.json',{'time':0,'models':[],'errors':[]})
        write('settings.json',{'language':'es','theme':'auto','poll_seconds':2,'watch_models':False,'watch_integrations':True,'integration_scan_seconds':300,'daily_updates':False,'update_hours':24,'model_dirs':[]})
        write('integrations.json',{'items':[]});write('remote-servers.json',{'items':[]});write('external-providers.json',{'items':[]})
        info=app/'Contents/Info.plist';doc=plistlib.loads(info.read_bytes());doc['IALocalDataDirectory']=str(data);doc['IALocalPort']=port;doc['CFBundleIdentifier']='local.ia-local.manager.'+hashlib.sha256(str(data).encode()).hexdigest()[:10];info.write_bytes(plistlib.dumps(doc))
        import subprocess
        # Local ad-hoc signing confirms package integrity; it is not Developer ID notarization.
        subprocess.run(['/usr/bin/codesign','--force','--deep','--sign','-',str(app)],check=True,capture_output=True)
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True,capture_output=True)
        shortcut=Path.home()/'Desktop/IA Local.app'
        if desktop and not shortcut.exists() and not shortcut.is_symlink():shortcut.symlink_to(app,target_is_directory=True)
        return {'app':str(app),'data':str(data),'clean':True,'message':'Instalación limpia completada. No hay usuarios, claves, modelos ni acceso LAN configurados.'}
    except Exception:
        if app_created:shutil.rmtree(app)
        if data_created and data.exists():shutil.rmtree(data)
        raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--payload-app',required=True);p.add_argument('--applications',default=str(Path.home()/'Applications'));p.add_argument('--data',default=str(Path.home()/'Library/Application Support/IA-Local'));p.add_argument('--desktop',action='store_true');p.add_argument('--port',type=int,default=8040);a=p.parse_args()
    try:print(json.dumps(install(a.payload_app,a.applications,a.data,a.desktop,a.port),ensure_ascii=False))
    except Exception as e:print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(1)
