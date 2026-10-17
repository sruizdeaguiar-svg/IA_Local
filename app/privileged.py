"""Client for the fixed GPU helper. Never accepts arbitrary privileged operations."""
import json, os, socket, stat,sys
from pathlib import Path
SOCKET=Path('/var/run')/('local.ia-local.gpu-'+str(getattr(os,'getuid',lambda:0)())+'.sock')
def request(value=None):
    if sys.platform!='darwin':raise RuntimeError('El límite iogpu solo está disponible en macOS.')
    st=SOCKET.lstat()
    if not stat.S_ISSOCK(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600:raise RuntimeError('Permisos del socket del ayudante no válidos.')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(5);s.connect(str(SOCKET))
        # LOCAL_PEERCRED via getpeereid is not exposed in Python. Root-owned
        # launchd plist/executable and the non-user-writable /var/run protect endpoint.
        if value is not None and (type(value) is not int or value<0):raise ValueError('Valor GPU no válido.')
        s.sendall(('GET\n' if value is None else 'SET '+str(value)+'\n').encode());data=b''
        while len(data)<4096:
            part=s.recv(1024)
            if not part:break
            data+=part
            if b'\n'in data:break
    result=json.loads(data)
    if result.get('error'):raise RuntimeError(result['error'])
    return result

def status():
    if sys.platform!='darwin':return {'installed':False,'supported':False,'message':'El ajuste de memoria iogpu es exclusivo de macOS.'}
    try:return {'installed':True,**request()}
    except (OSError,ValueError,RuntimeError) as e:return {'installed':False,'message':str(e) if SOCKET.exists() else 'Instala el ayudante una vez desde IA Local en el Mac.'}
