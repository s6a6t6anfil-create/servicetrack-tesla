import {errorText} from './helpers.js';

function buildRequestOptions(options, csrf) {
  return {
    credentials: 'same-origin',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(csrf ? {'X-CSRFToken': csrf} : {}),
      ...options.headers,
    },
  };
}

async function fetchResponse(path, options, fetchImpl, csrf) {
  try {
    return await fetchImpl(path, buildRequestOptions(options, csrf));
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw Error('Немає зв’язку із сервером. Перевір підключення та спробуй ще раз.');
  }
}

async function readResponse(response) {
  if (response.status === 204) return null;

  let data;
  try {
    data = await response.json();
  } catch {
    throw Error('Сервер повернув неочікувану відповідь. Спробуй ще раз пізніше.');
  }

  if (!response.ok) {
    const messagesByStatus = {
      403: 'Доступ заборонено або сесія завершилася. Перевір свої права чи увійди знову.',
      404: 'Запис більше не існує або недоступний. Онови список.',
      429: `Забагато запитів. Повтори через ${response.headers.get('Retry-After') || 'кілька'} секунд.`,
    };
    const message = messagesByStatus[response.status] || (
      response.status >= 500
        ? 'Помилка сервера. Спробуй ще раз пізніше.'
        : errorText(data)
    );
    throw Error(message);
  }
  return data;
}

export async function requestJSON(
  path,
  options = {},
  {fetchImpl = globalThis.fetch, csrf = '', onBusy = () => {}} = {},
) {
  onBusy(true);
  try {
    const response = await fetchResponse(path, options, fetchImpl, csrf);
    // Await inside try so loading remains active until body parsing completes.
    return await readResponse(response);
  } finally {
    onBusy(false);
  }
}
