"""Install the portable source edition using an existing Python 3.12+.

This edition is usable before frozen binary distribution: a private virtualenv
installs official PyPI dependencies, with source/configuration kept separate.
Never overwrites an installation or installs an inference engine/model.
"""
from pathlib import Path
import argparse,os,shutil,subprocess,sys,venv
HERE=Path(__file__).resolve().parent

def install(destination,data,desktop=False):
    if sys.version_info<(3,12):raise RuntimeError('Se necesita Python 3.12 o posterior.')
    destination=Path(destination).expanduser().absolute();data=Path(data).expanduser().absolute()
    if destination.exists():raise FileExistsError('La carpeta de aplicación ya existe; elige una nueva.')
    if destination==data or destination in data.parents or data in destination.parents:raise ValueError('Separa aplicación y datos.')
    if any(c in str(destination)+str(data) for c in ('\n','\r','\x00')):raise ValueError('Ruta no válida.')
    destination.mkdir(parents=True)
    try:
        from install_clean import BACKEND_FILES
        for name in (*BACKEND_FILES,'install_clean.py','portable_launcher.py','IA.ico','requirements.txt'):
            shutil.copy2(HERE/name,destination/name)
        (destination/'requirements-source.txt').write_text('-r requirements.txt\ncryptography>=46.0.0,<48\n',encoding='utf-8')
        venv.create(destination/'.venv',with_pip=True)
        python=destination/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
        subprocess.run([str(python),'-m','pip','install','--index-url','https://pypi.org/simple','-r',str(destination/'requirements-source.txt')],check=True)
        if os.name=='nt':
            # The shortcut runs Python directly, not a shell command string.
            def quote(s):return "'"+str(s).replace("'","''")+"'"
            pyw=python.with_name('pythonw.exe');launcher=destination/'portable_launcher.py'
            if '"' in str(data):raise ValueError('Ruta de datos no válida.')
            script="$s=New-Object -ComObject WScript.Shell;"
            places=[Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/IA Local.lnk']
            if desktop:places.append(Path.home()/'Desktop/IA Local.lnk')
            for path in places:
                if path.exists():continue
                script+='$l=$s.CreateShortcut('+quote(path)+');$l.TargetPath='+quote(pyw)+';$l.Arguments='+quote('"'+str(launcher)+'" --data "'+str(data)+'"')+';$l.IconLocation='+quote(str(destination/'IA.ico'))+';$l.Save();'
            subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],check=True)
        else:
            def desktop_quote(s):return '"'+str(s).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
            entry='[Desktop Entry]\nType=Application\nName=IA Local\nExec='+desktop_quote(python)+' '+desktop_quote(destination/'portable_launcher.py')+' --data '+desktop_quote(data)+'\nIcon='+str(destination/'icon-512.png')+'\nTerminal=false\nCategories=Utility;Development;\n'
            target=Path.home()/'.local/share/applications/ia-local.desktop';target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_text(entry,encoding='utf-8');target.chmod(0o700)
            if desktop and (Path.home()/'Desktop').is_dir():
                target=Path.home()/'Desktop/IA Local.desktop'
                if not target.exists():target.write_text(entry,encoding='utf-8');target.chmod(0o700)
        print('Instalación de código completada. Lanzar: '+str(python)+' '+str(destination/'portable_launcher.py')+' --data '+str(data))
    except Exception:
        # Partial app files are harmless and retained for diagnosis; never remove data.
        print('Instalación incompleta. Se conserva la carpeta para diagnóstico: '+str(destination),file=sys.stderr);raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',required=True);p.add_argument('--data',required=True);p.add_argument('--desktop',action='store_true');a=p.parse_args();install(a.destination,a.data,a.desktop)
