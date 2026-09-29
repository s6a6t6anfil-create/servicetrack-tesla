import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Execute the actual detail loader with controlled API timing and a minimal DOM.
const source=readFileSync(new URL('../static/app.js',import.meta.url),'utf8');
const start=source.indexOf('async function showOrder(id){');
const end=source.indexOf("$('detail-content').addEventListener",start);
function setup(){
  const requests=new Map(),nodes=new Map(),notices=[];
  const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',innerHTML:'',open:false,addEventListener(){},showModal(){this.open=true;}});return nodes.get(id);};
  const ctx=vm.createContext({$:node,session:{manager:true},e:String,money:String,notice:m=>notices.push(m),api:url=>new Promise((resolve,reject)=>requests.set(url,{resolve,reject})),currentOrder:null,detailVersion:0});
  vm.runInContext(source.slice(start,end),ctx);
  return {ctx,node,requests,notices};
}
const order=id=>({id,number:`ST-${id}`,vehicle_label:`Car ${id}`,items:[],transitions:[],status:'received'});
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('late detail response cannot replace the latest order or mutation target',async()=>{
  const {ctx,node,requests}=setup();
  const first=ctx.showOrder(1);requests.get('/api/orders/1/').resolve(order(1));await tick();
  const second=ctx.showOrder(2);requests.get('/api/orders/2/').resolve(order(2));await tick();
  requests.get('/api/orders/2/history/').resolve([]);await second;
  requests.get('/api/orders/1/history/').resolve([]);await first;
  assert.equal(node('detail-title').textContent,'ST-2 · Car 2');
  assert.equal(ctx.currentOrder.id,2);
});
test('failed replacement preserves the visible order and its mutation target',async()=>{
  const {ctx,node,requests}=setup();
  const first=ctx.showOrder(1);requests.get('/api/orders/1/').resolve(order(1));await tick();requests.get('/api/orders/1/history/').resolve([]);await first;
  const second=ctx.showOrder(2);requests.get('/api/orders/2/').resolve(order(2));await tick();requests.get('/api/orders/2/history/').reject(Error('history failed'));await second;
  assert.equal(node('detail-title').textContent,'ST-1 · Car 1');
  assert.equal(ctx.currentOrder.id,1);
});

test('closing detail invalidates a pending response before it can reopen',async()=>{
 const {ctx,node,requests}=setup();
 vm.runInContext(source.slice(source.indexOf('function invalidateDetail'),source.indexOf('async function load')),ctx);
 const work=ctx.showOrder(1);requests.get('/api/orders/1/').resolve(order(1));await tick();
 ctx.invalidateDetail();node('detail').open=false;
 requests.get('/api/orders/1/history/').resolve([]);await work;
 assert.equal(node('detail').open,false);assert.equal(ctx.currentOrder,null);
});

test('a failed read from an open dialog reports inside that dialog',async()=>{
 const {ctx,node,requests}=setup();
 vm.runInContext(source.slice(source.indexOf('function notice'),source.indexOf('async function load')),ctx);
 node('detail').open=true;
 const work=ctx.showOrder(2);requests.get('/api/orders/2/').reject(Error('network unavailable'));await work;
 assert.equal(node('detail-notice').textContent,'network unavailable');assert.equal(node('notice').textContent,'');
});
