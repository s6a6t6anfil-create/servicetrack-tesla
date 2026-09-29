# Технічна документація ServiceTrack Tesla
Практичні заняття 14 і 29. Версія 0.1. Філатов Олександр Юрійович, КН-42.

## Огляд і архітектура
ServiceTrack — локальний Django-моноліт із REST API та браузерним інтерфейсом. models.py визначає дані, serializers.py перевіряє введення, services.py виконує переходи статусів, views.py застосовує права й маршрути. app.js керує екранами, form-fields.js — полями, helpers.js — чистими функціями. Обґрунтування архітектури: один процес і одна БД спрощують запуск малої майстерні; логічні межі дозволяють перейти на PostgreSQL без зміни API.

![Рис. 1. Компоненти застосунку](images/architecture.png)

## Налаштування середовища
1. Установи Python 3.12 та Git з офіційних джерел; для клієнтських тестів потрібен Node.js 22 або новіший.
2. Отримай каталог проєкту та перейди до нього.
3. Створи середовище: python3 -m venv .venv. Активуй source .venv/bin/activate; у Windows — .venv\Scripts\activate.
4. Установи залежності: pip install -r requirements.txt.
5. Створи таблиці: python manage.py migrate.
6. Для порожньої демонстраційної БД задай DEMO_PASSWORD довжиною від 12 символів та виконай python manage.py seed_demo. Для робочої БД створи власного superuser й групи ролей через admin.
7. Запусти python manage.py runserver 127.0.0.1:8943. Відкрий цю адресу у браузері.
Локальний SECRET_KEY створюється автоматично у .local-secret з правами 600. Паролі, .env та база не входять до Git. seed_demo відмовляється працювати з непорожньою БД.

## Автентифікація і протокол
Базова адреса API: http://127.0.0.1:8943/api/. Формат — JSON, кодування UTF-8. Вхід: GET /accounts/login/ для форми та CSRF, потім POST форми username/password/csrfmiddlewaretoken. Успіх створює sessionid cookie. Вихід — POST /accounts/logout/ із CSRF. Самореєстрації та JWT немає.
У кожному POST/PUT/PATCH/DELETE API передавай cookie сесії та X-CSRFToken з csrftoken cookie. Відсутній доступ дає 403. Механіку повертаються лише призначені замовлення й пов’язані з ними клієнти/авто. Спроба відкрити недоступний об’єкт дає 404, щоб не розкривати його існування.
Списки мають count, next, previous, results; параметр page — додатне ціле, 50 записів на сторінку. search — необов’язковий рядок. Обмеження 600 запитів/хв на користувача діє через DRF throttle й локальний cache; це не захист від DDoS або перебору паролів.

## Маршрути
У таблиці {id} — додатний ідентифікатор об’єкта в URL. Для GET/DELETE тіло не потрібне; для POST/PUT — JSON відповідної сутності; PATCH містить лише змінювані поля.

| URL після /api/ | Методи | Призначення і права |
|---|---|---|
| session/ | GET | Ім’я, роль, дозволені механіки, довідник статусів |
| customers/ | GET POST | Список видимих клієнтів; створення — адміністратор |
| customers/{id}/ | GET PUT PATCH DELETE | Читання; зміни — адміністратор; PROTECT при авто |
| vehicles/ | GET POST | Список авто; створення — адміністратор |
| vehicles/{id}/ | GET PUT PATCH DELETE | Картка авто; зміни — адміністратор; PROTECT при замовленнях |
| orders/ | GET POST | Видимі замовлення; створення — адміністратор |
| orders/{id}/ | GET PATCH | Деталі; механік змінює лише diagnosis/fault_codes |
| orders/{id}/transition/ | POST | Перехід стану; видача тільки адміністратором |
| orders/{id}/history/ | GET | Події з автором і часом, від нових до старих |
| orders/{id}/comment/ | POST | Додати коментар від поточного користувача |
| items/ | GET POST | Видимі позиції кошторису; створення — адміністратор |
| items/{id}/ | GET PUT PATCH DELETE | Позиція; зміни — адміністратор до видачі |
| schema/ | GET | OpenAPI контракт із типами та полями |
| docs/ | GET | Swagger UI; бібліотека інтерфейсу з CDN |

## Поля запитів
Усі id у JSON — цілі числа. Ідентифікатор самого запису й часові мітки створює сервер. Обов’язковість нижче стосується POST; PUT вимагає повного набору обов’язкових полів, PATCH — тільки надісланих.

| Сутність | Обов’язкові поля | Необов’язкові поля |
|---|---|---|
| Customer | name:string ≤120; phone:string ≤30 | email:email; notes:string ≤4000 |
| Vehicle | customer:int FK; model:enum; year:int 2008..2100; vin:string 17 unique | plate:string ≤20; mileage:int 0..3000000 |
| Order | vehicle:int FK; complaint:string ≤4000; due_date:YYYY-MM-DD | mechanic:int або null; diagnosis:string ≤8000; fault_codes:string ≤1000 |
| OrderItem | order:int FK; kind:labor/part; name:string ≤200; quantity:decimal >0; unit_price:decimal ≥0 | Немає |
| Transition | status:enum дозволеного переходу | Немає |
| Comment | text:string ≤4000, непорожній | Немає |

Моделі авто: Model S, Model 3, Model X, Model Y, Cybertruck, Roadster. Статуси API: received, diagnosis, approval, parts, repair, ready, delivered. quantity — до 8 цифр загалом і 2 після крапки; unit_price — до 10 і 2. Decimal у відповіді — рядки. Сервер нормалізує VIN до верхнього регістру та перевіряє його унікальність після нормалізації.
Параметри query: orders приймає status:string, overdue=true, vehicle:int, number:string (ST-0005 або 5), search:string, page:int. vehicles — customer:int, search, page. customers — search, page. items — page. Невалідний vehicle/customer/number дає 400. Невідома сторінка — 404.

## Приклади запитів і відповідей
POST customers/: {"name":"Демо клієнт","phone":"000","email":"demo@example.invalid"}. Успіх 201: {"id":5,"name":"Демо клієнт","phone":"000","email":"demo@example.invalid","notes":"","created_at":"2026-09-29T12:00:00+03:00"}. Час та id наведені як приклад формату, а не фактичний журнал.
POST vehicles/: {"customer":5,"model":"Model Y","year":2023,"vin":"TEST0000000000099","mileage":12000}. Успіх 201 повертає ці поля, id, customer_name та plate. Помилка 400: {"vin":["Повідомлення про неправильний формат або дублікат."]}.
POST orders/: {"vehicle":5,"mechanic":2,"complaint":"Огляд підвіски","due_date":"2026-10-01"}. Успіх 201 повертає id, number, status:"received", status_label, total:"0.00", items:[], transitions і решту полів Order. PATCH orders/5/: {"diagnosis":"Огляд завершено","fault_codes":"DEMO_CODE"} → 200 з оновленою карткою.
POST items/: {"order":5,"kind":"labor","name":"Огляд","quantity":"1.50","unit_price":"1000.00"} → 201 з id та надісланими полями. PATCH items/5/: {"quantity":"2.00"} → 200. DELETE items/5/ → 204 без тіла, якщо замовлення відкрите.
POST orders/5/transition/: {"status":"diagnosis"} → 200 з Order. Недозволений перехід: 400 {"status":"Недозволений перехід статусу."}. POST orders/5/comment/: {"text":"Погодження очікується"} → 201 {"id":10,"kind":"comment","text":"Погодження очікується","author_name":"admin","created_at":"..."}. GET history/ → масив таких Event.
GET customers/?page=1 → 200 {"count":1,"next":null,"previous":null,"results":[...]}. Така сама оболонка використовується vehicles/orders/items. GET {resource}/{id}/ → 200 з одним об’єктом; неіснуючий або недоступний id → 404 {"detail":"..."}. PUT/PATCH customers чи vehicles повертають 200 з повним об’єктом; DELETE повертає 204 або 400 за наявності зв’язків.
GET session/ → 200 {"username":"admin","manager":true,"mechanics":[{"id":2,"username":"mechanic"}],"statuses":[{"value":"received","label":"Прийнято"},...]}. Схеми повних успішних відповідей усіх маршрутів містяться в openapi.yaml поруч із цим документом.

## Коди стану й помилки
200 — читання/оновлення; 201 — створення; 204 — видалення; 400 — некоректні поля, статус або пов’язані записи; 403 — немає сесії/прав/CSRF; 404 — об’єкт чи сторінку не знайдено; 405 — метод не підтримується; 429 — перевищено throttle; 500 — неочікувана помилка сервера. Помилки полів — об’єкт із назвами полів та повідомленнями; загальні — detail. Текст може залежати від локалізації, тому інтеграція має перевіряти код і ключі, а не повне речення.

## Тести та резервування
python manage.py test workshop перевіряє сервер; node --test tests/*.test.js — клієнтські функції. Для схеми: python manage.py spectacular --file docs/openapi.yaml --validate. Для цілісної копії SQLite використовуй sqlite3.Connection.backup; не копіюй активний файл бази довільно. Відновлення перевіряй на окремому екземплярі.

## Розгортання
1. Підготуй сервер із Python, залежностями, окремим обліковим записом процесу й резервуванням.
2. Задай DEBUG=0, SECRET_KEY і ALLOWED_HOSTS; встанови й налаштуй production WSGI-сервер.
3. Виконай migrate та collectstatic, налаштуй обслуговування STATIC_ROOT.
4. Налаштуй HTTPS reverse proxy та коректний захищений зв’язок із застосунком. Заголовки довіреного proxy дозволяй лише для контрольованого proxy.
5. Запусти manage.py check --deploy, перевір login/CSRF, доступ ролей, резервування і відновлення.
6. Перед відкриттям реальних даних додай обмеження спроб входу, моніторинг і тест конкурентних записів; для кількох активних працівників розглянь PostgreSQL.
Production-розгортання цієї версії ще не перевірене; інструкція описує необхідні кроки, а не факт введення в експлуатацію.
