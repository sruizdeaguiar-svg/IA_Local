"""Install the real archive in a selected path, preserving an existing app."""
from pathlib import Path
import hashlib,os,shutil,subprocess,sys,tempfile,zipfile
folder=Path(sys.argv[1]).absolute();destination=Path(sys.argv[2]).absolute();pattern='*-Windows-x64.zip' if os.name=='nt' else '*-Linux-x86_64.zip'
archive=next(folder.glob(pattern))
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 with zipfile.ZipFile(archive) as z:z.extractall(root)
 if os.name=='nt':
  shell=shutil.which('pwsh') or shutil.which('powershell');command=[shell,'-NoProfile','-NonInteractive','-File',str(root/'Install.ps1'),'-Destination',str(destination),'-DataDirectory',str(destination.parent/'selected data directory'),'-DesktopShortcut']
 else:command=['sh',str(root/'install.sh'),str(destination)]
 subprocess.run(command,check=True);exe=destination/('IA-Local.exe' if os.name=='nt' else 'IA-Local');before=hashlib.sha256(exe.read_bytes()).hexdigest()
 assert os.access(exe,os.X_OK)
 second=subprocess.run(command,capture_output=True,text=True);assert second.returncode!=0,'Existing installation was overwritten'
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==before
 print('Selected application directory with spaces, shortcut creation and no-overwrite: passed')
