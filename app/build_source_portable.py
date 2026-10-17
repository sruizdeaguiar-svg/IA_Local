"""Create clean source-edition installers; these are not native executable builds."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from install_clean import BACKEND_FILES
HERE=Path(__file__).resolve().parent

def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);results=[]
    names=(*BACKEND_FILES,'install_clean.py','portable_launcher.py','install_portable_source.py','IA.ico','requirements.txt')
    for system,installer in [('Windows','install-source-windows.ps1'),('Linux','install-source-linux.sh')]:
        archive=out/f'IA-Local-1.2.0-{system}-source.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name in names:z.write(HERE/name,'app/'+name)
            z.write(HERE/installer,'Instalar.ps1' if system=='Windows' else 'instalar.sh');z.write(HERE/'docs/PORTABLE.md','README.md')
            license_file=HERE.parent/'IA_Local-publicacion/LICENSE'
            if not license_file.exists():license_file=HERE.parent/'LICENSE'
            if not license_file.exists():raise FileNotFoundError('Repository LICENSE must accompany the package')
            z.write(license_file,'LICENSE')
        results.append({'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'edition':'source installer; Python 3.12+ required','native_runtime_verified':False})
    (out/'source-manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(results,indent=2));return results
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',default='dist/source');build(p.parse_args().out)
