"""Keep a frozen app's private loader paths out of external engine processes.

PyInstaller changes library search paths for its bundled dependencies. External
engines must use their own libraries. On Windows, serialize the short-lived
SetDllDirectory override while creating a child, then restore the app's path.
"""
import contextlib,os,subprocess,sys,threading
_guard=threading.RLock()

def environment(env=None):
    result=dict(os.environ if env is None else env)
    if not getattr(sys,'frozen',False):return result
    for key in ('LD_LIBRARY_PATH','LIBPATH'):
        original=result.get(key+'_ORIG')
        if original is None:result.pop(key,None)
        else:result[key]=original
    home=str(getattr(sys,'_MEIPASS',''))
    if home:result['PATH']=os.pathsep.join(p for p in result.get('PATH','').split(os.pathsep) if not os.path.normcase(p).startswith(os.path.normcase(home)))
    return result

@contextlib.contextmanager
def external_loader():
    if not getattr(sys,'frozen',False) or os.name!='nt':yield;return
    import ctypes
    with _guard:
        kernel=ctypes.windll.kernel32;buffer=ctypes.create_unicode_buffer(32768);kernel.GetDllDirectoryW(len(buffer),buffer)
        if not kernel.SetDllDirectoryW(None):raise OSError('No se pudo aislar el cargador del proceso externo.')
        try:yield
        finally:
            if not kernel.SetDllDirectoryW(buffer.value or None):raise OSError('No se pudo restaurar el cargador de IA Local.')

def popen(*args,**kwargs):
    kwargs['env']=environment(kwargs.get('env'))
    with external_loader():return subprocess.Popen(*args,**kwargs)

def run(*args,**kwargs):
    kwargs['env']=environment(kwargs.get('env'))
    with external_loader():return subprocess.run(*args,**kwargs)
