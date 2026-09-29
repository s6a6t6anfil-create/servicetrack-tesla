export function escapeHTML(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
export function money(value) { const n = Number(value); if (!Number.isFinite(n)) return '—'; return n.toLocaleString('uk-UA',{minimumFractionDigits:2,maximumFractionDigits:2}) + ' ₴'; }
export function isOverdue(order, today) { return order.due_date < today && !['ready','delivered'].includes(order.status); }
export function searchParams(view, search, status, overdue) { const p = new URLSearchParams(); if(search.trim()){ if(view==='orders' && /^ST-\d+$/i.test(search.trim())) p.set('number',search.trim()); else p.set('search',search.trim()); } if(view==='orders'){ if(status)p.set('status',status); if(overdue)p.set('overdue','true'); } return p; }
export function errorText(data) { if(typeof data==='string')return data; if(Array.isArray(data))return data.map(errorText).join(' '); if(data&&typeof data==='object')return Object.entries(data).map(([k,v])=>`${k}: ${errorText(v)}`).join(' · '); return 'Не вдалося виконати дію.'; }

export function recordCount(n) {
  const last=n%10, lastTwo=n%100;
  const word=lastTwo>=11&&lastTwo<=14?'записів':last===1?'запис':last>=2&&last<=4?'записи':'записів';
  return `${n} ${word}`;
}
