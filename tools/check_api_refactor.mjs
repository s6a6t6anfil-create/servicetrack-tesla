import {execFileSync} from 'node:child_process';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
const root=fileURLToPath(new URL('../', import.meta.url));
const helper=pathToFileURL(resolve(root,'static/helpers.js')).href;
const source=execFileSync('git',['show','bb273ec:static/api.js'],{cwd:root,encoding:'utf8'}).replace("'./helpers.js'",JSON.stringify(helper));
const old=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).requestJSON;
const current=(await import(pathToFileURL(resolve(root,'static/api.js')).href)).requestJSON;
const cases=[];
for(const status of [200,201,204,400,401,403,404,405,429,500,503]) {
  cases.push({status,body:JSON.stringify({vin:['Неправильний VIN']})});
  if(status!==204)cases.push({status,body:'<html>not json</html>'});
}
cases.push({status:429,body:'{}',retry:'12'},{error:'offline'},{error:'abort'});
async function observe(fn,scenario,custom){
  let sent,states=[];
  const options=custom?{method:'PATCH',body:'{"x":1}',credentials:'omit',headers:{'Content-Type':'custom','X-CSRFToken':'override'}}:{};
  try{
    const result=await fn('/api/example/',options,{csrf:custom?'csrf-token':'',onBusy:busy=>states.push(busy),fetchImpl:async(path,options)=>{
      sent={path,options};
      if(scenario.error==='abort')throw new DOMException('Cancelled','AbortError');
      if(scenario.error)throw TypeError('offline');
      return new Response(scenario.status===204?null:scenario.body,{status:scenario.status,headers:scenario.retry?{'Retry-After':scenario.retry}:{}});
    }});
    return {result,sent,states};
  }catch(error){return {error:{name:error.name,message:error.message},sent,states};}
}
let count=0;
for(const scenario of cases)for(const custom of [false,true]){
  assert.deepEqual(await observe(current,scenario,custom),await observe(old,scenario,custom)); count++;
}
console.log(`PASS: ${count} before/after comparisons: result, exact errors, request headers/options, loading sequence. Baseline bb273ec.`);
for(const fn of [old,current]){
  let release,states=[];
  const body=new Promise(resolve=>{release=resolve;});
  const request=fn('/slow-body',{}, {onBusy:v=>states.push(v),fetchImpl:async()=>({status:200,ok:true,json:()=>body})});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(states,[true]);
  release({done:true});assert.deepEqual(await request,{done:true});assert.deepEqual(states,[true,false]);
}
console.log('PASS: both versions keep loading active until delayed JSON parsing completes.');
