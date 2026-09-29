import {escapeHTML as e, money, isOverdue, searchParams, errorText} from './helpers.js';
const $ = id => document.getElementById(id);
let view='orders', session, currentPage=1, lastResult, currentOrder;
const titles={orders:['Замовлення','Нове замовлення'],customers:['Клієнти','Новий клієнт'],vehicles:['Автомобілі','Новий автомобіль']};
const csrf=()=>document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1];
async function api(path, options={}){
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-CSRFToken':csrf(),...options.headers}});
  if(response.status===204)return null;
  let data;try{data=await response.json();}catch{throw Error('Не вдалося прочитати відповідь сервера. Онови сторінку.');}
  if(!response.ok)throw Error(response.status===403?'Доступ заборонено або сесія завершилася. Перевір свої права чи увійди знову.':errorText(data));
  return data;
}
const send=(url,data,method='POST')=>api(url,{method,body:JSON.stringify(data)});
function notice(text){$('notice').textContent=text;}
async function load(){
  $('content').innerHTML='<p class="empty">Завантаження…</p>';
  const p=searchParams(view,$('search').value,$('status-filter').value,$('overdue').checked);p.set('page',currentPage);
  try{lastResult=await api(`/api/${view}/?${p}`);render(lastResult.results);$('count').textContent=`${lastResult.count} записів · сторінка ${currentPage}`;$('prev').disabled=!lastResult.previous;$('next').disabled=!lastResult.next;}
  catch(err){$('content').innerHTML=`<p class="empty error">${e(err.message)}</p>`;$('stats').innerHTML='';}
}
const dateToday=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Kyiv'});
function render(rows){
  $('stats').hidden=view!=='orders';
  if(view==='orders')$('stats').innerHTML=[['Замовлень у вибірці',lastResult.count],['Активних на сторінці',rows.filter(o=>!['ready','delivered'].includes(o.status)).length],['Прострочених на сторінці',rows.filter(o=>isOverdue(o,dateToday())).length]].map(([label,n])=>`<div class="stat"><small>${label}</small><strong>${n}</strong></div>`).join('');
  if(!rows.length){$('content').innerHTML='<p class="empty">Записів немає. Зміни фільтри або додай перший запис.</p>';return;}
  let heads,body;
  if(view==='orders'){
    heads=['Замовлення / клієнт','Автомобіль','Статус','Строк','Кошторис',''];
    body=rows.map(o=>`<tr><td><strong>${e(o.number)}</strong><small>${e(o.customer_name)}</small></td><td><strong>${e(o.vehicle_label)}</strong><small>${e(o.vin)}</small></td><td><span class="badge ${e(o.status)}">${e(o.status_label)}</span></td><td class="${isOverdue(o,dateToday())?'late':''}">${e(o.due_date)}<small>${e(o.mechanic_name)}</small></td><td>${money(o.total)}</td><td><button data-open="${o.id}">Відкрити ↗</button></td></tr>`).join('');
  }else if(view==='customers'){
    heads=['Клієнт','Телефон','Email',''];
    body=rows.map(c=>`<tr><td><strong>${e(c.name)}</strong><small>${e(c.notes)}</small></td><td>${e(c.phone)}</td><td>${e(c.email)||'—'}</td><td>${session.manager?`<button data-edit="${c.id}">Редагувати</button> <button data-delete="${c.id}">Видалити</button>`:''}</td></tr>`).join('');
  }else{
    heads=['Автомобіль','VIN','Клієнт','Пробіг',''];
    body=rows.map(v=>`<tr><td><strong>${e(v.model)} · ${e(v.year)}</strong><small>${e(v.plate)}</small></td><td>${e(v.vin)}</td><td>${e(v.customer_name)}</td><td>${Number(v.mileage).toLocaleString('uk-UA')} км</td><td><button data-vehicle-history="${v.id}">Історія</button> ${session.manager?`<button data-edit="${v.id}">Редагувати</button> <button data-delete="${v.id}">Видалити</button>`:''}</td></tr>`).join('');
  }
  $('content').innerHTML=`<div class="table-scroll"><table><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></div>`;
}
async function allOptions(resource){let result=[],url=`/api/${resource}/`;while(url){const d=await api(url);result.push(...d.results);url=d.next;}return result;}
function input(name,label,value='',type='text',required=true,extra=''){return `<label>${e(label)}<input name="${name}" type="${type}" value="${e(value)}" ${required?'required':''} ${extra}></label>`;}
function area(name,label,value='',required=false){return `<label class="wide">${e(label)}<textarea name="${name}" ${required?'required':''}>${e(value)}</textarea></label>`;}
function select(name,label,options,value='',optional=false){return `<label>${e(label)}<select name="${name}" ${optional?'':'required'}>${optional?'<option value="">Не призначено</option>':'<option value="">Обери…</option>'}${options.map(o=>`<option value="${e(o.id)}" ${String(o.id)===String(value)?'selected':''}>${e(o.label)}</option>`).join('')}</select></label>`;}
async function edit(record=null,kind=view){
  $('form-error').textContent='';$('dialog-title').textContent=record?'Редагування':kind==='items'?'Додати роботу або запчастину':titles[kind][1];
  const r=record||{};
  try{
    if(kind==='customers')$('fields').innerHTML=input('name','Ім’я / назва',r.name,'text',true,'maxlength="120"')+input('phone','Телефон',r.phone,'tel',true,'maxlength="30"')+input('email','Email',r.email,'email',false)+area('notes','Примітки',r.notes);
    if(kind==='vehicles'){
      const customers=await allOptions('customers');
      $('fields').innerHTML=select('customer','Клієнт',customers.map(c=>({id:c.id,label:c.name})),r.customer)+select('model','Модель',['Model S','Model 3','Model X','Model Y','Cybertruck','Roadster'].map(x=>({id:x,label:x})),r.model)+input('year','Рік',r.year||2023,'number',true,'min="2008" max="2100"')+input('vin','VIN',r.vin,'text',true,'minlength="17" maxlength="17" pattern="[A-HJ-NPR-Za-hj-npr-z0-9]{17}"')+input('plate','Державний номер',r.plate,'text',false)+input('mileage','Пробіг, км',r.mileage||0,'number',true,'min="0" max="3000000"');
    }
    if(kind==='orders'){
      const vehicles=await allOptions('vehicles');
      $('fields').innerHTML=(session.manager?select('vehicle','Автомобіль',vehicles.map(v=>({id:v.id,label:`${v.model} · ${v.plate||v.vin} · ${v.customer_name}`})),r.vehicle)+select('mechanic','Механік',session.mechanics.map(m=>({id:m.id,label:m.username})),r.mechanic,true)+input('due_date','Плановий строк',r.due_date||dateToday(),'date')+area('complaint','Звернення клієнта',r.complaint,true):'')+area('diagnosis','Результат діагностики',r.diagnosis)+input('fault_codes','Коди помилок (вручну)',r.fault_codes,'text',false);
    }
    if(kind==='items')$('fields').innerHTML=select('kind','Тип',[{id:'labor',label:'Робота'},{id:'part',label:'Запчастина'}],r.kind)+input('name','Назва',r.name)+input('quantity','Кількість',r.quantity||1,'number',true,'min="0.01" step="0.01"')+input('unit_price','Ціна, грн',r.unit_price||0,'number',true,'min="0" step="0.01"');
    $('editor').showModal();
    $('edit-form').onsubmit=async event=>{
      event.preventDefault(); const button=event.submitter; button.disabled=true;
      const data=Object.fromEntries(new FormData(event.target));
      if('mechanic' in data && !data.mechanic)data.mechanic=null;
      if(data.vin)data.vin=data.vin.toUpperCase();
      if(kind==='items')data.order=currentOrder.id;
      try{await send(`/api/${kind}/${r.id?r.id+'/':''}`,data,r.id?'PATCH':'POST');$('editor').close();notice('Зміни збережено.');if($('detail').open)await showOrder(currentOrder.id);await load();}
      catch(err){$('form-error').textContent=err.message;}finally{button.disabled=false;}
    };
  }catch(err){notice(err.message);}
}
async function showOrder(id){
  try{
    currentOrder=await api(`/api/orders/${id}/`);const o=currentOrder;const events=await api(`/api/orders/${id}/history/`);
    $('detail-title').textContent=`${o.number} · ${o.vehicle_label}`;
    $('detail-content').innerHTML=`<div class="detail-meta"><p><small>Клієнт</small>${e(o.customer_name)}</p><p><small>Статус</small>${e(o.status_label)}</p><p><small>Плановий строк</small>${e(o.due_date)}</p><p><small>Механік</small>${e(o.mechanic_name)}</p></div><h3>Звернення</h3><p>${e(o.complaint)}</p><h3>Діагностика та коди помилок</h3><p>${e(o.diagnosis)||'Поки немає запису'}</p><p>${e(o.fault_codes)}</p><div class="detail-actions">${o.status!=='delivered'?'<button id="edit-order">Редагувати</button>':''}${o.transitions.filter(s=>s.value!=='delivered'||session.manager).map(s=>`<button data-transition="${e(s.value)}">→ ${e(s.label)}</button>`).join('')}</div><h3>Попередній кошторис · ${money(o.total)}</h3><div class="table-scroll"><table><thead><tr><th>Позиція</th><th>Кількість × ціна</th><th></th></tr></thead><tbody>${o.items.map(i=>`<tr><td>${e(i.name)}<small>${i.kind==='labor'?'Робота':'Запчастина'}</small></td><td>${e(i.quantity)} × ${money(i.unit_price)}</td><td>${session.manager&&o.status!=='delivered'?`<button data-item-edit="${i.id}">Змінити</button> <button data-item-delete="${i.id}">Видалити</button>`:''}</td></tr>`).join('')||'<tr><td colspan="3">Позицій поки немає</td></tr>'}</tbody></table></div>${session.manager&&o.status!=='delivered'?'<p><button id="add-item">+ Додати позицію</button></p>':''}<h3>Історія та коментарі</h3>${events.map(h=>`<div class="event">${e(h.text)}<small>${e(h.author_name)} · ${new Date(h.created_at).toLocaleString('uk-UA')}</small></div>`).join('')}<form id="comment-form" class="comment-form"><input name="text" aria-label="Новий коментар" placeholder="Додати коментар…" maxlength="4000" required><button>Додати</button></form><p id="detail-error" class="error" role="alert"></p>`;
    if(!$('detail').open)$('detail').showModal();
    $('edit-order')?.addEventListener('click',()=>edit(o,'orders'));$('add-item')?.addEventListener('click',()=>edit(null,'items'));
    $('comment-form').onsubmit=async ev=>{ev.preventDefault();try{await send(`/api/orders/${id}/comment/`,Object.fromEntries(new FormData(ev.target)));await showOrder(id);}catch(err){$('detail-error').textContent=err.message;}};
  }catch(err){notice(err.message);}
}
$('detail-content').addEventListener('click',async ev=>{const t=ev.target;try{
  if(t.dataset.transition){t.disabled=true;await send(`/api/orders/${currentOrder.id}/transition/`,{status:t.dataset.transition});await showOrder(currentOrder.id);await load();}
  if(t.dataset.itemEdit)await edit(currentOrder.items.find(i=>i.id===Number(t.dataset.itemEdit)),'items');
  if(t.dataset.itemDelete&&confirm('Видалити цю позицію кошторису?')){await api(`/api/items/${t.dataset.itemDelete}/`,{method:'DELETE'});await showOrder(currentOrder.id);await load();}
}catch(err){$('detail-error').textContent=err.message;t.disabled=false;}});
$('content').addEventListener('click',async ev=>{const t=ev.target;try{
  if(t.dataset.open)await showOrder(t.dataset.open);
  if(t.dataset.edit)await edit(lastResult.results.find(x=>x.id===Number(t.dataset.edit)));
  if(t.dataset.delete&&confirm('Видалити запис? Запис із пов’язаними даними видалити неможливо.')){await api(`/api/${view}/${t.dataset.delete}/`,{method:'DELETE'});currentPage=1;await load();}
  if(t.dataset.vehicleHistory){const d=await api(`/api/orders/?vehicle=${t.dataset.vehicleHistory}`);$('detail-title').textContent='Історія обслуговування';$('detail-content').innerHTML=d.results.map(o=>`<p><button data-history-order="${o.id}">${e(o.number)} · ${e(o.status_label)}</button> ${e(o.complaint)}</p>`).join('')||'<p>Замовлень поки немає.</p>';$('detail').showModal();for(const b of $('detail-content').querySelectorAll('[data-history-order]'))b.onclick=()=>showOrder(b.dataset.historyOrder);}
}catch(err){notice(err.message);}});
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{view=b.dataset.view;currentPage=1;for(const n of document.querySelectorAll('[data-view]'))n.classList.toggle('active',n===b);$('page-title').textContent=titles[view][0];$('create').textContent='+ '+titles[view][1];$('search').value='';$('status-filter').hidden=view!=='orders';$('overdue').parentElement.hidden=view!=='orders';$('page-description').textContent=view==='orders'?'Від першого звернення до видачі автомобіля.':view==='customers'?'Контакти та примітки про клієнтів майстерні.':'Автомобілі та історія їхнього обслуговування.';notice('');load();};
$('create').onclick=()=>edit();$('filters').onsubmit=ev=>{ev.preventDefault();currentPage=1;load();};$('prev').onclick=()=>{currentPage--;load();};$('next').onclick=()=>{currentPage++;load();};$('close-dialog').onclick=$('cancel').onclick=()=>$('editor').close();$('close-detail').onclick=()=>$('detail').close();
try{session=await api('/api/session/');$('status-filter').innerHTML+=session.statuses.map(s=>`<option value="${e(s.value)}">${e(s.label)}</option>`).join('');await load();}catch(err){notice(err.message);}
