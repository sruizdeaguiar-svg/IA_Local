"""Fixed update adapters. All downloads/builds execute as the logged-in user."""
from core import *
import shutil, tarfile, urllib.parse

SUPPORTED={'opencode','hermes','vllm','lmstudio','mlx','omlx','exo','llama','strata-llama'}
REASONS={'strata':'Motor con parches Metal locales: requiere reconstrucción y verificación de esos parches.','mirai':'Pendiente verificar el canal firmado de la aplicación Mirai; se conservan el router y sus adaptaciones.','unsloth':'Runtime compartido con adaptaciones locales: se conserva hasta disponer de una migración aislada.','fm':'Forma parte de macOS; se actualiza en Ajustes del Sistema.','freellmapi':'Compilación local: revisar migraciones de la base de datos y conservar claves antes de actualizar.'}

def policy(s):
    return {'automatic':s in SUPPORTED,'update_label':'Actualizar runtime' if s=='lmstudio' else 'Actualizar','reason':REASONS.get(s,'Copia previa, instalador oficial y comprobación posterior.'),'privileged':False}

_version_cache={};_version_time=0
def rows_with_current_versions(rows):
    global _version_time
    if time.monotonic()-_version_time>60 or not _version_cache:
        from operations import installed,SOURCES
        for row in rows:
            if row['id'] in SOURCES:_version_cache[row['id']]=installed(row['id'],SOURCES[row['id']][1])
        _version_time=time.monotonic()
    result=[]
    for row in rows:
        item={**row,**policy(row['id']),'installed':_version_cache.get(row['id'],row.get('installed','No comprobada'))}
        if row.get('status') in ('Actualización disponible','Sin versión estable posterior'):
            a=re.search(r'\d+\.\d+\.\d+',item['installed']);b=re.search(r'\d+\.\d+\.\d+',item.get('latest') or '')
            if a and b:item['status']='Actualización disponible' if tuple(map(int,a[0].split('.')))<tuple(map(int,b[0].split('.'))) else 'Sin versión estable posterior'
        item['rollback_available']=any(read(p/'restore.json',{}).get('service')==row['id'] for p in (ROOT/'backups').glob('update-'+row['id']+'-*'))
        result.append(item)
    return result

def github(repo,path='releases?per_page=30'):
    req=urllib.request.Request('https://api.github.com/repos/'+repo+'/'+path,headers={'User-Agent':'IA-Local/1.1','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def stable_release(repo,asset_filter):
    for r in github(repo):
        if r.get('draft') or (r.get('prerelease') and not (repo=='ggml-org/llama.cpp' and re.fullmatch(r'b\d+',r['tag_name']))) or re.search(r'(?:rc|alpha|beta|dev)[.-]?\d',r['tag_name'],re.I):continue
        assets=[a for a in r.get('assets',[]) if asset_filter(a['name'])]
        if assets:return r,assets[0]
    raise RuntimeError('No hay un paquete estable compatible en las publicaciones oficiales. No se cambia el canal.')

def download(asset,folder):
    url=asset['browser_download_url'];u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname!='github.com':raise RuntimeError('La descarga no pertenece al repositorio oficial.')
    target=folder/'package';sha=hashlib.sha256();size=0
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'IA-Local'}),timeout=90) as r,open(target,'wb') as f:
        while block:=r.read(1048576):
            size+=len(block)
            if size>4*2**30:raise RuntimeError('Paquete superior al tamaño permitido.')
            sha.update(block);f.write(block)
    expected=asset.get('digest','')
    if not expected.startswith('sha256:') or not secrets.compare_digest('sha256:'+sha.hexdigest(),expected):raise RuntimeError('No se pudo verificar el SHA-256 publicado. Instalación cancelada.')
    return target

def unpack(archive,folder):
    folder.mkdir()
    with tarfile.open(archive) as t:
        members=t.getmembers()
        if sum(m.size for m in members)>6*2**30:raise RuntimeError('Paquete expandido demasiado grande.')
        t.extractall(folder,filter='data')

def app_update(s,backup,progress):
    name,repo={'omlx':('oMLX','jundot/omlx'),'exo':('EXO','exo-explore/exo')}[s];current=Path('/Applications')/(name+'.app')
    if any((p.info.get('exe') or '').startswith(str(current)+'/') for p in psutil.process_iter(['exe'])):raise RuntimeError('Cierra '+name+' en el Mac antes de sustituir su aplicación. No se finaliza un proceso ajeno.')
    major=int(run(['/usr/bin/sw_vers','-productVersion']).split('.')[0])
    def accept(n):return n.endswith('.dmg') and (s=='exo' or ('macos26-27' in n if major>=26 else 'macos15' in n))
    release,asset=stable_release(repo,accept)
    present=plistlib.loads((current/'Contents/Info.plist').read_bytes())['CFBundleShortVersionString']
    if release['tag_name'].lstrip('v')==present:return {'message':name+' ya tiene esa versión estable.','changed':False}
    progress('Descargando '+release['tag_name']+' y verificando SHA-256…');archive=download(asset,backup)
    mount=backup/'mounted';mount.mkdir();attached=False
    try:
        run(['/usr/bin/hdiutil','attach','-nobrowse','-readonly','-mountpoint',mount,archive],90);attached=True;incoming=mount/(name+'.app')
        if not incoming.is_dir():raise RuntimeError('La imagen no contiene la aplicación esperada.')
        run(['/usr/bin/codesign','--verify','--deep','--strict',incoming],60)
        def team(path):
            p=subprocess.run(['/usr/bin/codesign','-dv','--verbose=4',str(path)],capture_output=True,text=True);m=re.search(r'^TeamIdentifier=(.+)$',p.stderr,re.M)
            if not m or m[1]=='not set':raise RuntimeError('No hay identidad de firma verificable.')
            return m[1]
        if team(incoming)!=team(current):raise RuntimeError('El equipo de firma no coincide con la aplicación instalada.')
        old=plistlib.loads((current/'Contents/Info.plist').read_bytes());new=plistlib.loads((incoming/'Contents/Info.plist').read_bytes())
        if old['CFBundleIdentifier']!=new['CFBundleIdentifier']:raise RuntimeError('Identificador de aplicación incorrecto.')
        if old['CFBundleShortVersionString']==new['CFBundleShortVersionString']:return {'message':name+' ya tiene esa versión estable.','changed':False}
        run(['/usr/sbin/spctl','--assess','--type','execute',incoming],60)
        stage=current.with_name('.ia-local-'+name+'-'+secrets.token_hex(5)+'.app');shutil.copytree(incoming,stage,symlinks=True)
        saved=backup/(name+'.app');write(backup/'restore.json',{'service':s,'kind':'app','target':str(current),'saved':str(saved)})
        shutil.move(current,saved)
        try:stage.rename(current);run(['/usr/bin/codesign','--verify','--deep','--strict',current],60)
        except Exception:
            if current.exists():shutil.rmtree(current)
            shutil.move(saved,current);raise
        return {'message':name+' actualizado a '+new['CFBundleShortVersionString']+'.','changed':True}
    finally:
        if attached:run(['/usr/bin/hdiutil','detach',mount],60)
        archive.unlink(missing_ok=True)

def replace_llama_runtime(incoming,target):
    # Fresh sibling trees preserve library symlinks and permit atomic renames
    # even when the installation is on a different volume from the backups.
    stage=target.with_name(target.name+'.ia-new-'+secrets.token_hex(5))
    previous=target.with_name(target.name+'.ia-old-'+secrets.token_hex(5))
    try:
        shutil.copytree(incoming,stage,symlinks=True)
        run([stage/'llama-server','--version'],60)
        target.rename(previous)
        try:
            stage.rename(target);run([target/'llama-server','--version'],60)
        except Exception:
            if target.exists():target.rename(stage)
            previous.rename(target);raise
    finally:
        if stage.exists():shutil.rmtree(stage)
    if previous.exists():shutil.rmtree(previous)

def _update(s,progress=lambda _:None):
    if s not in SUPPORTED:raise RuntimeError(REASONS.get(s,'No hay adaptador de actualización.'))
    active=read(ROOT/'active.json',{})
    if active:raise RuntimeError('Libera el modelo residente antes de actualizar. Se conservan las sesiones y no se interrumpe inferencia.')
    if port_open(PORTS[s]):
        process=find(s)
        if not (process and process.get('managed')) and not (s in ('opencode','lmstudio') and probe(s)):raise RuntimeError('Detén '+NAMES[s]+' desde su interfaz antes de actualizar: el proceso no pertenece al gestor.')
        stop(s)
        progress(NAMES[s]+' detenido para instalar la actualización; sus conversaciones se conservan.')
    if s=='hermes' and registered('ai.hermes.gateway'):raise RuntimeError('Detén también el gateway de Hermes.')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3);backup=ROOT/'backups'/('update-'+s+'-'+stamp);backup.mkdir()
    progress('Preparando copia y comprobando el canal de '+NAMES[s]+'…')
    if s in ('omlx','exo'):result=app_update(s,backup,progress)
    elif s=='lmstudio':
        # LMS keeps separately versioned runtime packs. Never removes older packs.
        before=run([HOME/'.lmstudio/bin/lms','runtime','ls'],30);(backup/'runtimes-before.txt').write_text(before,encoding='utf-8')
        write(backup/'restore.json',{'service':s,'kind':'lms-runtime','before':before})
        progress('Actualizando los runtimes compatibles de LM Studio…');run([HOME/'.lmstudio/bin/lms','runtime','update','--all','--yes'],900)
        after=run([HOME/'.lmstudio/bin/lms','runtime','ls'],30);result={'message':'Runtimes de LM Studio comprobados y actualizados. La aplicación de escritorio conserva su canal propio.','diagnostic':{'before':before,'after':after}}
    elif s=='vllm':
        prefix=Path(run(['/opt/homebrew/bin/brew','--prefix','vllm-metal'])).resolve();saved=backup/'runtime';shutil.copytree(prefix,saved,symlinks=True)
        write(backup/'restore.json',{'service':s,'kind':'brew','target':str(prefix),'saved':str(saved)})
        progress('Homebrew: actualizando vLLM Metal sin borrar versiones anteriores…')
        env={**os.environ,'HOMEBREW_NO_INSTALL_CLEANUP':'1','HOMEBREW_NO_AUTO_UPDATE':'1'}
        try:run(['/opt/homebrew/bin/brew','upgrade','vllm-metal'],1800,env);run(['/opt/homebrew/bin/vllm','--help'],90)
        except Exception:restore(backup);raise
        result={'message':'vLLM Metal actualizado y CLI comprobada. El perfil de inferencia debe volver a evaluarse.'}
    elif s=='mlx':
        target=OLD/'.venv';saved=backup/'runtime';shutil.copytree(target,saved,symlinks=True)
        write(backup/'restore.json',{'service':s,'kind':'directory','target':str(target),'saved':str(saved)})
        try:run([target/'bin/python','-m','pip','install','--index-url','https://pypi.org/simple','--upgrade','mlx-lm'],1200);run([target/'bin/python','-c','import mlx_lm; print(mlx_lm.__version__)'],90)
        except Exception:restore(backup);raise
        result={'message':'MLX-LM actualizado en su entorno existente y comprobado.'}
    elif s in ('llama','strata-llama'):
        release,asset=stable_release('ggml-org/llama.cpp',lambda n:bool(re.search(r'(?:macos|mac|apple|darwin).*(?:arm64|silicon)|(?:arm64|silicon).*(?:macos|apple)',n,re.I)) and n.endswith(('.tar.gz','.tar.xz')))
        progress('Descargando '+release['tag_name']+' para Apple Silicon…');archive=download(asset,backup);unpack(archive,backup/'expanded');archive.unlink()
        server=next((backup/'expanded').rglob('llama-server'),None)
        if not server:raise RuntimeError('No se encontró llama-server en el paquete oficial.')
        help_=run([server,'--help'],90)
        if not all(f in help_ for f in ('--models-preset','--models-dir','--models-max')):raise RuntimeError('Esta versión no conserva el router requerido.')
        target=LLAMA.parent if s=='llama' else STRATA/'engines/llama-b11707';saved=backup/'runtime';shutil.copytree(target,saved,symlinks=True)
        write(backup/'restore.json',{'service':s,'kind':'directory','target':str(target),'saved':str(saved)})
        try:
            replace_llama_runtime(server.parent,target)
        except Exception:restore(backup);raise
        result={'message':NAMES[s]+' actualizado a '+release['tag_name']+'. Se conservan modelos, presets y límites; los perfiles de velocidad anteriores necesitan revalidación.'}
    elif s=='freellmapi':
        release=next((r for r in github('tashfeenahmed/freellmapi') if not r.get('prerelease') and not r.get('draft')),None)
        if not release:raise RuntimeError('No hay publicación estable oficial.')
        stage=backup/'source';run(['/usr/bin/git','clone','--depth','1','--branch',release['tag_name'],'https://github.com/tashfeenahmed/freellmapi.git',stage],180)
        node=ROOT/'runtime/bin';env={**os.environ,'PATH':str(node)+':'+os.environ.get('PATH','/usr/bin:/bin')}
        for sub in ('server','client'):
            progress('Compilando FreeLLMAPI: '+sub+'…');run([Path('/opt/homebrew/bin/npm'),'--prefix',stage/sub,'ci'],1200,env);run([Path('/opt/homebrew/bin/npm'),'--prefix',stage/sub,'run','build'],1200,env)
        target=ROOT/'freellmapi';saved=backup/'runtime';write(backup/'restore.json',{'service':s,'kind':'directory','target':str(target),'saved':str(saved)})
        target.rename(saved);stage.rename(target);result={'message':'FreeLLMAPI actualizado. Base de datos, claves y configuración conservadas fuera del programa.'}
    else:
        # Existing official agent adapters, enhanced lifecycle/step-up handled by supervisor/gateway.
        from operations import update_agents
        return update_agents(s)
    event('update',{'service':s,'backup':str(backup),'changed':result.get('changed',True)});return result

def update(s,progress=lambda _:None):
    before=find(s) if s in PORTS else None
    was_running=bool(s in PORTS and port_open(PORTS[s]) and (before and before.get('managed') or s in ('opencode','lmstudio') and probe(s)))
    try:return _update(s,progress)
    finally:
        _version_cache.clear()
        if was_running and not port_open(PORTS[s]):
            try:start(s)
            except Exception:event('update-restart-failed',{'service':s,'message':'La interfaz no se reinició. Usa Arrancar y revisa los registros.'})

def restore(folder):
    record=read(folder/'restore.json',{});s=record.get('service');kind=record.get('kind')
    if s not in SUPPORTED:raise RuntimeError('Copia no válida.')
    expected={'mlx':OLD/'.venv','freellmapi':ROOT/'freellmapi','llama':LLAMA.parent,'strata-llama':STRATA/'engines/llama-b11707','omlx':Path('/Applications/oMLX.app'),'exo':Path('/Applications/EXO.app')}
    if kind=='brew':
        target=Path(record['target']);saved=folder/'runtime'
        if target.parent!=Path('/opt/homebrew/Cellar/vllm-metal'):raise ValueError('Destino de recuperación no válido.')
        # Restore exact prior keg; link only this fixed formula to the retained version.
        if target.exists():shutil.rmtree(target)
        shutil.copytree(saved,target,symlinks=True)
        live=Path(run(['/opt/homebrew/bin/brew','--prefix','vllm-metal'])).resolve()
        run(['/opt/homebrew/bin/brew','unlink','vllm-metal'],90)
        if live!=target and live.is_dir() and live.parent==target.parent:
            live.rename(folder/('replaced-keg-'+live.name+'-'+secrets.token_hex(3)))
        run(['/opt/homebrew/bin/brew','link','vllm-metal'],90)
    elif kind in ('directory','app'):
        target=expected.get(s)
        if not target or str(target)!=record.get('target'):raise ValueError('Destino de recuperación no válido.')
        saved=Path(record['saved'])
        if saved.parent!=folder or not saved.is_dir():raise ValueError('Copia de recuperación incompleta.')
        replaced=folder/('replaced-'+secrets.token_hex(4));target.rename(replaced);shutil.copytree(saved,target,symlinks=True)
    else:raise RuntimeError('Los runtimes antiguos de LM Studio se conservan; elige la versión en su selector oficial Runtime.')
    _version_cache.clear()
    event('rollback-update',{'service':s,'backup':str(folder)});return {'message':'Versión anterior de '+NAMES[s]+' restaurada. Se conserva también la sustituida.'}

def rollback(s):
    if s not in SUPPORTED:raise RuntimeError('No hay adaptador de recuperación.')
    if port_open(PORTS[s]) or read(ROOT/'active.json',{}):raise RuntimeError('Detén el servicio y libera modelos antes de recuperar.')
    folders=[p for p in (ROOT/'backups').glob('update-'+s+'-*') if read(p/'restore.json',{}).get('service')==s]
    if not folders:
        from operations import rollback_update
        return rollback_update(s)
    return restore(sorted(folders)[-1])
