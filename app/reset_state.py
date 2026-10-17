"""Reversible application reset. Never uninstalls engines, weights or agent data.

Invoke under the supervisor lifecycle lock. Stop only identities in this data
profile's managed ledger. Back up own configuration and SQLite consistently;
restoration invalidates sessions and does not restart services or enable LAN.
"""
from core import *
import shutil
JSON_STATE=('installation.json','settings.json','catalog.json','contexts.json','profiles.json','active.json','processes.json','integrations.json','integration-discovery.json','integration-proposal.json','remote-servers.json','remote-credentials.json','remote-catalog.json','remote-connections.json','external-providers.json','external-credentials.json','benchmark-series.json','optimization-series.json','optimizations.json','agent-checks.json','updates.json','models.ini','models-strata.ini')
DB_STATE=('access.sqlite','history.sqlite')

def latest():
    folders=[p for p in (ROOT/'backups').glob('reset-*') if p.is_dir() and not p.is_symlink() and (p/'manifest.json').is_file()]
    return max(folders,key=lambda p:p.stat().st_mtime_ns) if folders else None

def status():
    p=latest();return {'available':p is not None,'time':read(p/'manifest.json',{}).get('time') if p else None,'detached':read(ROOT/'installation.json',{}).get('detached',False)}

def snapshot(prefix='reset-'):
    folder=ROOT/'backups'/(prefix+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(4));folder.mkdir(mode=0o700)
    names=[]
    for name in JSON_STATE:
        p=ROOT/name
        if p.is_file() and not p.is_symlink():shutil.copy2(p,folder/name);os.chmod(folder/name,0o600);names.append(name)
    for name in DB_STATE:
        if not (ROOT/name).exists():continue
        with sqlite3.connect(ROOT/name) as source,sqlite3.connect(folder/name) as dest:source.backup(dest)
        os.chmod(folder/name,0o600);names.append(name)
    write(folder/'manifest.json',{'time':time.time(),'files':{n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in names},'scope':'IA Local only; no model weights, installed runtimes or agent conversations'})
    return folder

def clear_sessions():
    import lan
    with lan.access_db() as c:
        for table in ('sessions','stepups'):c.execute('DELETE FROM '+table)

def detach(value,progress):
    if not isinstance(value,dict) or value.get('confirmation')!='RESTABLECER':raise ValueError('Escribe RESTABLECER para confirmar el restablecimiento completo de IA Local.')
    import integrations,remote_servers,external_providers,lan,app_settings
    progress('Guardando copia recuperable de la configuración y los usuarios…');folder=snapshot()
    # Only this profile's owned processes may be stopped; no name/port kills.
    progress('Deteniendo únicamente los procesos gestionados por este perfil…')
    for sid,record in list(ledger().items()):
        if record.get('managed') and same(record):stop(sid)
    for sid in list(external_providers.SERVERS):external_providers.disconnect(sid)
    # Close this profile's web listeners. Existing agent programs and their home
    # configurations remain outside the reset scope.
    lan.configure(False,lambda *args:None)
    for sid in list(NAMES):
        if sid.startswith(('custom-','remote-','cloud-')):NAMES.pop(sid,None);PORTS.pop(sid,None)
    for name in ('contexts.json','profiles.json','active.json','processes.json','remote-credentials.json','external-credentials.json','remote-catalog.json','integration-discovery.json','integration-proposal.json','benchmark-series.json','optimization-series.json','agent-checks.json'):write(ROOT/name,{})
    for name in ('integrations.json','remote-servers.json','external-providers.json'):write(ROOT/name,{'items':[]})
    for name in ('remote-connections.json','optimizations.json','updates.json'):write(ROOT/name,[])
    write(ROOT/'catalog.json',{'time':0,'models':[],'errors':[]})
    write(ROOT/'settings.json',{**app_settings.DEFAULTS,'watch_models':False,'daily_updates':False,'model_dirs':[],'lan_enabled':False})
    write(ROOT/'installation.json',{'clean':True,'detached':True,'linked_services':[],'version':'1.2.0'})
    with lan.access_db() as c:
        for table in ('stepups','sessions','totp','users'):c.execute('DELETE FROM '+table)
    with db() as c:c.execute('DELETE FROM events');c.execute('DELETE FROM results')
    token=ROOT/'token';token.write_text(secrets.token_urlsafe(40));token.chmod(0o600)
    event('application-reset',{'backup':folder.name,'programs_preserved':True})
    return {'message':'IA Local restablecida: sin instalaciones vinculadas, usuarios ni preferencias personales. Programas, modelos y conversaciones conservados. El acceso web está desactivado. Recupera la copia desde el Mac si lo necesitas.','backup':str(folder),'reset':True}

def restore(progress):
    import integrations,remote_servers,external_providers,lan
    folder=latest()
    if folder is None:raise RuntimeError('No hay un restablecimiento recuperable.')
    files=read(folder/'manifest.json',{}).get('files',{})
    for name,digest in files.items():
        if name not in JSON_STATE+DB_STATE or not (folder/name).is_file() or (folder/name).is_symlink() or hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('La copia no supera la comprobación de integridad.')
    snapshot('before-restore-reset-')
    progress('Recuperando configuración sin arrancar servicios ni abrir la red…')
    for sid,record in list(ledger().items()):
        if record.get('managed') and same(record):raise RuntimeError('Detén los servicios de este perfil antes de recuperar una copia de configuración.')
    for sid in list(external_providers.SERVERS):external_providers.disconnect(sid)
    lan.configure(False,lambda *args:None)
    for name in files:
        if name in DB_STATE:
            with sqlite3.connect(folder/name) as source,sqlite3.connect(ROOT/name) as dest:source.backup(dest)
        else:shutil.copy2(folder/name,ROOT/name)
        os.chmod(ROOT/name,0o600)
    for name in JSON_STATE:
        if name not in files:
            if name.endswith('.ini'):(ROOT/name).write_text('')
            else:write(ROOT/name,{'items':[]} if name in ('integrations.json','remote-servers.json','external-providers.json') else [] if name in ('remote-connections.json','optimizations.json','updates.json') else {})
    clear_sessions();write(ROOT/'active.json',{});write(ROOT/'processes.json',{});write(ROOT/'remote-connections.json',[])
    cfg=read(ROOT/'settings.json',{});cfg.update(lan_enabled=False,waiting=[]);write(ROOT/'settings.json',cfg)
    for sid in list(NAMES):
        if sid.startswith(('custom-','remote-','cloud-')):NAMES.pop(sid,None);PORTS.pop(sid,None)
    integrations.install_registry();remote_servers.install_registry();external_providers.install_registry()
    token=ROOT/'token';token.write_text(secrets.token_urlsafe(40));token.chmod(0o600)
    return {'message':'Configuración y usuarios recuperados. Sesiones anteriores invalidadas; servicios y acceso LAN permanecen detenidos. Vuelve a sincronizar los perfiles de agentes si usaban la pasarela.','restored':True}

def attach_known(sid):
    if sid not in PORTS or sid.startswith(('custom-','cloud-')) or sid not in available_services(include_unlinked=True):raise ValueError('Adaptador integrado no encontrado en este equipo; utiliza el asistente de integración.')
    profile=read(ROOT/'installation.json',{});linked=profile.setdefault('linked_services',[])
    if sid not in linked:linked.append(sid)
    write(ROOT/'installation.json',profile);return {'message':NAMES[sid]+' vinculado. No se ha arrancado ni cargado ningún modelo.'}
