import {errorText} from './helpers.js';
export async function requestJSON(path, options={}, {fetchImpl=globalThis.fetch, csrf='', onBusy=()=>{}}={}){
  onBusy(true);
  try {
    let response;
    try {response=await fetchImpl(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(csrf?{'X-CSRFToken':csrf}:{}),...options.headers}});}
    catch(err){if(err.name==='AbortError')throw err;throw Error('Немає зв’язку із сервером. Перевір підключення та спробуй ще раз.');}
    if(response.status===204)return null;
    let data;try{data=await response.json();}catch{throw Error('Сервер повернув неочікувану відповідь. Спробуй ще раз пізніше.');}
    if(!response.ok){
      const known={403:'Доступ заборонено або сесія завершилася. Перевір свої права чи увійди знову.',404:'Запис більше не існує або недоступний. Онови список.',429:`Забагато запитів. Повтори через ${response.headers.get('Retry-After')||'кілька'} секунд.`};
      throw Error(known[response.status]||(response.status>=500?'Помилка сервера. Спробуй ще раз пізніше.':errorText(data)));
    }
    return data;
  } finally {onBusy(false);}
}
