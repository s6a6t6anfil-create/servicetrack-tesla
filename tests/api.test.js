import test from 'node:test';
import assert from 'node:assert/strict';
import {requestJSON} from '../static/api.js';
test('JSON success sends CSRF and balances loading',async()=>{let seen,states=[];const data=await requestJSON('/api/',{method:'POST',body:'{}'},{csrf:'test-token',onBusy:v=>states.push(v),fetchImpl:async(u,o)=>{seen=o;return new Response('{"id":1}',{status:201})}});assert.deepEqual(data,{id:1});assert.equal(seen.headers['X-CSRFToken'],'test-token');assert.equal(seen.credentials,'same-origin');assert.deepEqual(states,[true,false]);});
test('204 needs no JSON',async()=>assert.equal(await requestJSON('/api/',{}, {fetchImpl:async()=>new Response(null,{status:204})}),null));
test('validation and status errors are human readable',async()=>{for(const [status,body,pattern] of [[400,{vin:['Неправильний VIN']},/vin/],[403,{},/сесія/],[404,{},/недоступний/],[429,{},/12 секунд/],[503,{},/Помилка сервера/]])await assert.rejects(requestJSON('/api/',{}, {fetchImpl:async()=>new Response(JSON.stringify(body),{status,headers:{'Retry-After':'12'}})}),pattern);});
test('offline and invalid JSON reset loading',async()=>{for(const fetchImpl of [async()=>{throw TypeError('offline')},async()=>new Response('<html>error</html>')]){let states=[];await assert.rejects(requestJSON('/api/',{}, {fetchImpl,onBusy:v=>states.push(v)}));assert.deepEqual(states,[true,false]);}});
test('abort preserves cancellation',async()=>{await assert.rejects(requestJSON('/api/',{}, {fetchImpl:async()=>{throw new DOMException('Cancelled','AbortError')}}),{name:'AbortError'});});
