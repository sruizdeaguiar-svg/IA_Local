"""Persistent aggregate inference metrics. Never stores prompts or generated text."""
import datetime, json, time

def summary(connection):
    c=connection
    c.execute('CREATE TABLE IF NOT EXISTS inference (id INTEGER PRIMARY KEY,time REAL,engine TEXT,model TEXT,success INTEGER,input_tokens INTEGER,output_tokens INTEGER,input_rate REAL,generation_rate REAL,ttft_s REAL,total_s REAL,load_s REAL,source TEXT)')
    c.execute('CREATE INDEX IF NOT EXISTS inference_time ON inference(time)')
    c.execute('CREATE TABLE IF NOT EXISTS inference_cursor (id INTEGER PRIMARY KEY CHECK(id=1),value INTEGER)')
    cursor=(c.execute('SELECT value FROM inference_cursor WHERE id=1').fetchone() or [0])[0]
    for rid,ts,kind,encoded in c.execute("SELECT rowid,time,kind,data FROM events WHERE rowid>? ORDER BY rowid LIMIT 5000",(cursor,)).fetchall():
        cursor=rid
        if kind!='request':continue
        d=json.loads(encoded);u=d.get('usage') or {};t=d.get('timings') or {};ttft=d.get('ttft_s')
        # Older records did not capture success explicitly. Preserve unknown status.
        success=int(d['success']) if 'success' in d else None
        c.execute('INSERT OR IGNORE INTO inference VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,ts,d.get('engine'),d.get('model'),success,u.get('prompt_tokens'),u.get('completion_tokens'),t.get('prompt_per_second') or t.get('prefill_tps'),t.get('predicted_per_second') or t.get('decode_tps') or d.get('generation_tok_s'),ttft,d.get('wall_s'),d.get('load_s'),d.get('source','Pasarela')))
    c.execute('INSERT OR REPLACE INTO inference_cursor VALUES(1,?)',(cursor,))
    now=datetime.datetime.now().astimezone();today=now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp();out=[]
    cols=['count','valid','failed','unknown','input_tokens','output_tokens','input_tok_s','input_samples','generation_tok_s','generation_samples','ttft_s','ttft_samples','total_s','load_s']
    for label,start in [('Hoy',today),('7 días',time.time()-7*86400),('30 días',time.time()-30*86400),('Total',0)]:
        row=c.execute('SELECT COUNT(*),SUM(success=1),SUM(success=0),SUM(success IS NULL),SUM(CASE WHEN success=1 THEN input_tokens END),SUM(CASE WHEN success=1 THEN output_tokens END),AVG(CASE WHEN success=1 THEN input_rate END),COUNT(CASE WHEN success=1 THEN input_rate END),AVG(CASE WHEN success=1 THEN generation_rate END),COUNT(CASE WHEN success=1 THEN generation_rate END),AVG(CASE WHEN success=1 THEN ttft_s END),COUNT(CASE WHEN success=1 THEN ttft_s END),AVG(CASE WHEN success=1 THEN total_s END),AVG(CASE WHEN success=1 THEN load_s END) FROM inference WHERE time>=?',(start,)).fetchone()
        out.append({'label':label,**dict(zip(cols,row))})
    cur=c.execute('SELECT * FROM inference ORDER BY time DESC,id DESC LIMIT 1');last=cur.fetchone();last=dict(zip([d[0] for d in cur.description],last)) if last else None
    return {'last':last,'periods':out,'basis':'Media aritmética por consulta completada; cada métrica usa solo valores medidos. Fallos y registros antiguos de estado desconocido no entran en las medias.','coverage':'Solicitudes que atraviesan la pasarela IA Local o las interfaces de inferencia HTTPS del panel. Las conexiones directas a otros puertos no se observan; los benchmarks se contabilizan aparte. Las medias generales mezclan modelos y motores y no son una comparación de calidad.'}

class Capture:
    """Incrementally inspects response metadata; retains no conversation content."""
    def __init__(self):
        self.start=time.monotonic();self.first=None;self.usage={};self.timings={};self.buffer=b'';self.chunks=0
    def item(self,d):
        if not isinstance(d,dict):return
        self.usage=d.get('usage') or self.usage;self.timings=d.get('timings') or self.timings
        delta=(d.get('choices') or [{}])[0].get('delta',{})
        if delta.get('content') or delta.get('reasoning_content'):
            self.first=self.first or time.monotonic();self.chunks+=1
    def feed(self,b):
        self.buffer+=b
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            if line.startswith(b'data:'):
                try:self.item(json.loads(line[5:].strip()))
                except (ValueError,IndexError):pass
        if len(self.buffer)>2**20:self.buffer=b''
    def finish(self):
        if self.buffer:
            try:self.item(json.loads(self.buffer))
            except (ValueError,IndexError):pass
        rate=self.timings.get('predicted_per_second') or self.timings.get('decode_tps')
        if rate is None and self.first and self.usage.get('completion_tokens',0)>1:rate=(self.usage['completion_tokens']-1)/max(.001,time.monotonic()-self.first)
        return {'generation_tok_s':rate,'usage':self.usage,'timings':self.timings,'ttft_s':self.first-self.start if self.first else None,'wall_s':time.monotonic()-self.start,'output_tokens_or_chunks':self.usage.get('completion_tokens',self.chunks),'counter_type':'tokens' if 'completion_tokens'in self.usage else 'chunks'}
