"""Build the unsigned-source/ad-hoc-signed macOS arm64 distribution.

Provide a prepared relocatable CPython prefix with requirements.txt installed.
Only allowlisted app source/assets enter the payload. Personal runtime state,
models, vendor checkouts, evidence and credentials are never copied.
"""
from pathlib import Path
import argparse,hashlib,json,os,plistlib,shutil,subprocess,sys,tempfile
from install_clean import BACKEND_FILES
HERE=Path(__file__).resolve().parent

def command(args):subprocess.run(list(map(str,args)),check=True)
def build(runtime,out):
    out=Path(out).absolute();runtime=Path(runtime).absolute();out.mkdir(parents=True,exist_ok=True)
    app=out/'payload/IA Local.app'
    if app.exists():shutil.rmtree(app) # Generated build output only, never an installed app.
    for folder in ('MacOS','Resources/backend','Helpers'):(app/'Contents'/folder).mkdir(parents=True,exist_ok=True)
    for name in (*BACKEND_FILES,'install_clean.py'):
        source=HERE/name
        if not source.is_file():raise FileNotFoundError(name)
        shutil.copy2(source,app/'Contents/Resources/backend'/name)
    shutil.copytree(runtime,app/'Contents/Resources/python',symlinks=True,ignore=shutil.ignore_patterns('._*','__pycache__','tests','test'))
    license_file=HERE.parent/'LICENSE'
    if not license_file.exists():license_file=HERE.parent/'IA_Local-publicacion/LICENSE'
    shutil.copy2(license_file,app/'Contents/Resources/LICENSE')
    shutil.copy2(HERE/'IA.icns',app/'Contents/Resources/IA.icns')
    info={'CFBundleIconFile':'IA.icns','CFBundleName':'IA Local','CFBundleDisplayName':'IA Local','CFBundleIdentifier':'local.ia-local.manager.clean','CFBundleExecutable':'ia-local','CFBundlePackageType':'APPL','CFBundleShortVersionString':'1.2.0','CFBundleVersion':'12','LSMinimumSystemVersion':'14.0','NSRemovableVolumesUsageDescription':'Leer las carpetas de modelos que el usuario autorice.','NSHighResolutionCapable':True,'NSPrincipalClass':'NSApplication','NSAppTransportSecurity':{'NSAllowsLocalNetworking':True}}
    (app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    obj=out/'authorize.o';command(['clang','-mmacosx-version-min=14.0','-O2','-Wno-deprecated-declarations','-c',HERE/'authorize.c','-o',obj])
    command(['xcrun','swiftc','-module-cache-path',out/'swift-cache','-O','-target','arm64-apple-macos14.0',HERE/'App.swift',obj,'-framework','AppKit','-framework','WebKit','-framework','Security','-o',app/'Contents/MacOS/ia-local'])
    for source,name in [('gpu_helper.c','ia-gpu-helper'),('privileged_gpu.c','ia-privileged-gpu')]:command(['clang','-mmacosx-version-min=14.0','-O2','-Wall',HERE/source,'-o',app/'Contents/Helpers'/name]);command(['codesign','--force','--sign','-',app/'Contents/Helpers'/name])
    command(['codesign','--force','--deep','--sign','-',app]);command(['codesign','--verify','--deep','--strict',app])
    installer=out/'Instalar IA Local.app'
    if installer.exists():shutil.rmtree(installer)
    (installer/'Contents/MacOS').mkdir(parents=True);(installer/'Contents/Resources').mkdir()
    shutil.copy2(HERE/'IA.icns',installer/'Contents/Resources/IA.icns')
    (installer/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIconFile':'IA.icns','CFBundleName':'Instalar IA Local','CFBundleIdentifier':'local.ia-local.installer','CFBundleExecutable':'install-ia-local','CFBundlePackageType':'APPL','CFBundleShortVersionString':'1.2.0','LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,'NSPrincipalClass':'NSApplication'}))
    command(['xcrun','swiftc','-module-cache-path',out/'swift-cache','-O','-target','arm64-apple-macos14.0',HERE/'Installer.swift','-framework','AppKit','-o',installer/'Contents/MacOS/install-ia-local'])
    command(['ditto','-c','-k','--norsrc','--keepParent',app,installer/'Contents/Resources/payload.zip']);command(['codesign','--force','--sign','-',installer]);command(['codesign','--verify','--deep','--strict',installer])
    archive=out/'IA-Local-1.2.0-macOS-arm64.zip';command(['ditto','-c','-k','--norsrc','--keepParent',installer,archive])
    manifest={'version':'1.2.0','platform':'macOS arm64','archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'payload_files':list(BACKEND_FILES),'configured':False,'signing':'ad-hoc; no Developer ID notarization'}
    (out/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2));return archive
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',required=True);p.add_argument('--out',default=str(Path(tempfile.gettempdir())/'IA-Local-release'));a=p.parse_args();build(a.runtime,a.out)
