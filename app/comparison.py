"""Measured per-model/per-engine comparisons. No inference, ranking or invented rates."""
import statistics

def build(catalog,results,optimizations):
    out={}
    for m in catalog:
        rows=[]
        for engine in m['engines']:
            entries=[dict(r['data'],_source=r['id']) for r in results if r['model']==m['id'] and r['data'].get('engine')==engine]
            for opt in optimizations:
                if opt.get('model')!=m['id'] or opt.get('engine')!=engine:continue
                selected=next((c for c in opt.get('candidates',[]) if c.get('parameters')==opt.get('selected') and c.get('status')=='passed'),None)
                entries.append({**opt,**(selected or {}),'status':opt.get('status'),'_source':opt.get('id'),'method':opt.get('method')})
            entries.sort(key=lambda e:e.get('finished',e.get('started',0)),reverse=True)
            valid=next((e for e in entries if e.get('status')=='passed'),None)
            row={'engine':engine,'configured_context':m['context'],'native_context':m.get('max_context'),'status':'Sin mediciones','same_context':False}
            if valid:
                fs=valid.get('functional',[]);fs=[fs] if isinstance(fs,dict) else fs;f=next(iter(fs),{})
                raw=valid.get('raw',[]);raw=raw if isinstance(raw,list) else []
                pp=next((r.get('avg_ts') for r in raw if r.get('n_prompt')==512 and not r.get('n_gen')),None)
                tg=next((r.get('avg_ts') for r in raw if r.get('n_gen')==128 and not r.get('n_prompt')),None)
                ctx=valid.get('context',valid.get('parameters',{}).get('context'))
                row.update(status='Medido',context=ctx,same_context=ctx==m['context'],prompt_tok_s=pp,generation_tok_s=tg,functional_generation_tok_s=f.get('generation_tok_s'),ttft_s=f.get('ttft_s'),ttft_basis=f.get('ttft_basis','Primer contenido visible; protocolo anterior'),load_s=valid.get('load_s'),min_available_gib=valid.get('min_available_gib',valid.get('memory_system_observed',{}).get('min_available_gib')),peak_rss_gib=valid.get('peak_rss_gib'),method=valid.get('method'),time=valid.get('finished',valid.get('started')),parameters=valid.get('parameters'),engine_version=valid.get('engine_version') or next((r.get('build_commit') for r in raw),None),source=valid['_source'])
                if entries and entries[0].get('status')!='passed':row['last_failure']=entries[0].get('error','Último ensayo no válido.')
            elif entries:row.update(status='Última prueba fallida',last_failure=entries[0].get('error','Sin resultado válido'))
            rows.append(row)
        out[m['id']]=rows
    return out
