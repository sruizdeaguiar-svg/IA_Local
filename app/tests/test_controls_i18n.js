// Pure state/translation tests for the same code embedded in native and web UI.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const controls=html.match(/^function reconcileControls\(d\).*$/m)[0],nodes=new Map();
const elem=id=>{if(!nodes.has(id))nodes.set(id,{value:'',disabled:false,hidden:false,dataset:{}});return nodes.get(id);};
const start={dataset:{service:'hermes',operation:'start'}},stop={dataset:{service:'hermes',operation:'stop'}},cancel={dataset:{action:'cancel'}},recover={dataset:{action:'unload'}},open={disabled:false};
const doc={querySelectorAll:selector=>selector==='[data-service]'?[start,stop]:selector==='[data-action]'?[cancel,recover]:selector==='[data-engine]'?[{dataset:{engine:'hermes'},querySelectorAll:()=>[open]}]:[]};
const model={id:'model',context:65536,engines:['llama']};elem('modelSelect').value='model';elem('engineSelect').value='llama';elem('detailEngine').value='hermes';
let d={services:[{id:'hermes',kind:'agent',running:true,ready:true,can_stop:true,state:'Interfaz disponible'}],jobs:[],active:{},optimizations:[],updates:[],helper:{installed:false},lan:{enabled:false}};
const ctx=vm.createContext({document:doc,$:elem,selected:()=>model,data:d});vm.runInContext(controls,ctx);ctx.d=d;vm.runInContext('reconcileControls(d)',ctx);
assert.equal(start.hidden,true);assert.equal(stop.hidden,false);assert.equal(cancel.disabled,true);assert.equal(recover.disabled,true);assert.equal(open.disabled,false);
for(const b of [start,stop,cancel,recover])b.disabled=false;d.services[0].running=false;d.services[0].ready=false;d.services[0].state='Detenido';vm.runInContext('reconcileControls(d)',ctx);assert.equal(start.hidden,false);assert.equal(stop.hidden,true);assert.equal(open.disabled,true);
for(const b of [start,stop,cancel,recover])b.disabled=false;d.jobs=[{state:'running',action:'benchmark',independent:false}];vm.runInContext('reconcileControls(d)',ctx);assert.equal(cancel.disabled,false);assert.equal(recover.disabled,true);
console.log('Controles: inicio/parada coherentes; web sin salud bloqueada; cancelar y recuperar memoria según estado.');
const en=JSON.parse(fs.readFileSync(path.join(__dirname,'../i18n-en.json'),'utf8'));const translate=html.match(/^function translateText\(text\).*$/m)[0];const tr=vm.createContext({EN:en,appLanguage:'en',dynamicPhrases:Object.keys(en).filter(k=>k.length>3).sort((a,b)=>b.length-a.length)});vm.runInContext(translate,tr);
for(const [text,expected] of [['Configuración de la aplicación','Application settings'],['Arrancar todos','Start all'],['Modelo cargado','Model loaded'],['APIs externas','External APIs'],['Qwen3.5-4B','Qwen3.5-4B']]){tr.input=text;assert.equal(vm.runInContext('translateText(input)',tr),expected);}
tr.appLanguage='es';tr.input='Modelo cargado';assert.equal(vm.runInContext('translateText(input)',tr),'Modelo cargado');
assert.match(html,/id="manualES"[^>]*data-no-translate/);assert.match(html,/id="manualEN"[^>]*data-no-translate/);
console.log('Idiomas: navegación y estados ES/EN, nombres de modelo intactos y manuales en ambos idiomas.');

// A weightless waiting service can cancel its queued start without a PID.
for(const b of [start,stop])b.disabled=false;d.services[0].state='En espera de modelo';d.services[0].can_stop=false;d.services[0].running=false;d.jobs=[];vm.runInContext('reconcileControls(d)',ctx);assert.equal(stop.disabled,false);assert.equal(stop.hidden,false);
