"""Validated user preferences. Secrets and managed runtime state are excluded."""
from core import *
DEFAULTS={'language':'es','theme':'auto','poll_seconds':2,'watch_models':True,'watch_integrations':True,'integration_scan_seconds':300,'daily_updates':False,'update_hours':24,'model_dirs':[]}
def save(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Parámetro no configurable. Usa su adaptador para cambiar puertos, modelos, red o credenciales.')
    for k,v in value.items():
        if k=='model_dirs' and (not isinstance(v,list) or len(v)>20 or any(not isinstance(x,str) or not Path(x).is_absolute() or Path(x)==Path('/') or not Path(x).is_dir() for x in v)):raise ValueError('Carpetas de modelos: rutas absolutas a directorios existentes; no se admite la raíz del sistema.')
        if k in ('watch_models','watch_integrations','daily_updates') and type(v) is not bool:raise ValueError('Preferencia booleana no válida.')
        if k=='language' and v not in ('es','en'):raise ValueError('Idioma: es o en.')
        if k=='theme' and v not in ('auto','light','dark'):raise ValueError('Tema: auto, light o dark.')
        if k in ('poll_seconds','integration_scan_seconds','update_hours') and (type(v) is not int or not {'poll_seconds':(1,10),'integration_scan_seconds':(60,3600),'update_hours':(1,168)}[k][0]<=v<={'poll_seconds':(1,10),'integration_scan_seconds':(60,3600),'update_hours':(1,168)}[k][1]):raise ValueError('Intervalo fuera del rango permitido.')
    current=read(ROOT/'settings.json',{});current.update(value);write(ROOT/'settings.json',current);return current
