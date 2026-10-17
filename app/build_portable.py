"""Build a native portable executable on the target OS; no cross compilation.

pip install -r requirements-portable.txt
python build_portable.py --out dist/portable
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,zipfile
from install_clean import BACKEND_FILES
HERE=Path(__file__).resolve().parent

def build(out):
    import platform
    if sys.platform not in ('win32','linux'):raise RuntimeError('Ejecuta esta compilación en Windows o Linux.')
    out=Path(out).absolute();out.mkdir(parents=True,exist_ok=True)
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--name','IA-Local','--distpath',str(out/'bin'),'--workpath',str(out/'build'),'--specpath',str(out)]
    for name in BACKEND_FILES:
        if not name.endswith('.py'):args+=['--add-data',str(HERE/name)+os.pathsep+'.']
    for module in [Path(n).stem for n in BACKEND_FILES if n.endswith('.py')]+['desktop_server','portable_security']:
        args+=['--hidden-import',module]
    args+=['--collect-all','gguf','--collect-all','numpy','--collect-all','cryptography']
    if os.name=='nt':args+=['--windowed','--icon',str(HERE/'IA.ico')]
    args+=[str(HERE/'portable_launcher.py')];subprocess.run(args,check=True)
    platform_name='Windows-x64' if os.name=='nt' else 'Linux-'+platform.machine();name='IA-Local.exe' if os.name=='nt' else 'IA-Local';binary=out/'bin'/name
    archive=out/f'IA-Local-1.2.0-{platform_name}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path,target in [(binary,name),(HERE/('install-windows.ps1' if os.name=='nt' else 'install-linux.sh'),'Install.ps1' if os.name=='nt' else 'install.sh'),(HERE/'icon-512.png','icon-512.png'),(HERE/'docs/PORTABLE.md','README.md')]:z.write(path,target)
        license_file=HERE.parent/'LICENSE'
        if not license_file.exists():license_file=HERE.parent/'IA_Local-publicacion/LICENSE'
        z.write(license_file,'LICENSE')
        # Dependency notices are distributed alongside the executable.
        for package in ('psutil','PyYAML','gguf','numpy','requests','tqdm','cryptography','pyinstaller'):
            import importlib.metadata
            distribution=importlib.metadata.distribution(package)
            for f in distribution.files or []:
                if any(x in str(f).lower() for x in ('license','copying','notice')) and '.dist-info/' in str(f):
                    p=Path(distribution.locate_file(f))
                    if p.is_file():z.write(p,'licenses/'+package+'/'+str(f).split('.dist-info/',1)[-1])
    manifest={'version':'1.2.0','platform':platform_name,'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'configured':False,'signature':'unsigned','built_on':platform.platform()};(out/'release-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest));return archive
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',default='dist/portable');build(p.parse_args().out)
