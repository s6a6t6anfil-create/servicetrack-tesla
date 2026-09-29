# Технічна документація ServiceTrack Tesla
Практичне заняття 29. Версія документа 1.0 від 29.09.2026.
Філатов Олександр Юрійович, КН-42.

Документ призначено розробнику, який має запустити та підтримувати ServiceTrack Tesla. Описано поточний Django MVP, його API, структуру даних, локальне середовище та підготовку до серверного розгортання. Базова версія коду — 25324a7; зміни ПЗ29 стосуються документації. Реальний UAT і production-розгортання ще не завершені.

## Огляд і архітектура
ServiceTrack — локальний Django-моноліт із REST API та браузерним інтерфейсом. models.py визначає дані, serializers.py перевіряє введення, services.py виконує переходи статусів, views.py застосовує права й маршрути. app.js керує екранами, api.js — HTTP-запитами та помилками, form-fields.js — полями, helpers.js — чистими функціями. Обґрунтування архітектури: один процес і одна БД спрощують запуск малої майстерні; логічні межі дозволяють зберегти контракт API під час майбутнього переходу на PostgreSQL. Сам перехід потребуватиме зміни DATABASES, драйвера, перенесення даних і перевірки конкурентних операцій; зараз він не реалізований.

![Рис. 1. Компоненти застосунку](images/architecture.png)

## Компоненти та дані

config/urls.py реєструє маршрути; config/settings.py визначає середовище. workshop/models.py містить Customer, Vehicle, Order, OrderItem та Event. workshop/serializers.py визначає JSON і валідації, workshop/views.py — операції та фільтрацію доступу, workshop/services.py — роль адміністратора й переходи станів. workshop/schema.py доповнює OpenAPI. templates/app.html і static/ утворюють браузерний клієнт без збирача; tests/ містить JavaScript-тести, workshop/tests.py — серверні.

Зв’язки: Customer 1 → N Vehicle 1 → N Order; Order 1 → N OrderItem та Event; User 1 → N Order через mechanic, User 1 → N Event через author. Видалення клієнта/авто/користувача з залежностями захищене PROTECT; дочірні позиції/події мають CASCADE на рівні моделі. API видалення замовлення не надає. Номер ST-0001 формується з первинного ключа. Кошторис обчислюється з Decimal, а не з float.

Обробка зміни: браузер надсилає JSON із cookie та CSRF → DRF перевіряє сесію/права → serializer перевіряє поля → view або service змінює ORM-об’єкти → повертається JSON → інтерфейс оновлює список. Створення замовлення з подією і перехід статусу виконуються в транзакції. select_for_update є в сервісі, проте SQLite не забезпечує блокування рядків як PostgreSQL: надійність паралельних змін потребує окремих тестів.

Обрана структура — моноліт із розділенням представлення, API, правил і даних. Django надає ORM, міграції, сесії та admin; DRF — серіалізацію і REST. Vanilla JavaScript не потребує npm-збирання. SQLite спрощує локальне демо, але обмежує конкурентний запис. Мікросервіси й окремий SPA-сервер для цього обсягу збільшили б налаштування та кількість точок відмови. Зовнішньої Tesla API/Toolbox інтеграції немає.

## Налаштування середовища
Використай Python 3.12 і Git. Node.js 22+ потрібен лише для JavaScript-тестів. Зафіксовані залежності: Django 5.2.17, DRF 3.16.1, drf-spectacular 0.29.0; повний список — requirements.txt. Наведені нижче команди призначені для macOS/Linux. У Windows активуй середовище командою .venv\Scripts\activate.bat у cmd.

1. Завантаж гілку цієї документації та перейди до кореня проєкту. Гілки попередніх практичних робіт ще проходять через PR, тому main не слід вважати поточною повною версією.

```sh
git clone --branch docs/pz29-technical \
  https://github.com/s6a6t6anfil-create/servicetrack-tesla.git
cd servicetrack-tesla
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
```

2. Лише для порожньої демонстраційної бази встанови власний DEMO_PASSWORD довжиною щонайменше 12 символів у середовищі процесу, потім виконай seed_demo. Пароль не зберігай у файлах репозиторію. Команда створить admin, mechanic, групи «Адміністратор»/«Механік» і чотири штучні замовлення; за наявності користувачів або клієнтів вона відмовиться працювати.

```sh
python manage.py seed_demo
unset DEMO_PASSWORD
python manage.py check
python manage.py runserver 127.0.0.1:8943
```

3. Відкрий http://127.0.0.1:8943/ і ввійди з виданими демоданими. Для наявної бази пропусти seed_demo, створи адміністратора через python manage.py createsuperuser, потім групи та користувачів через /admin/. Механік має бути активним і належати групі «Механік»; staff потрібен для входу в Django admin, а не для звичайного механіка.

4. Зупинка сервера — Ctrl+C. Якщо обраний порт зайнятий, запусти на іншому вільному порту й використовуй ту саму адресу в браузері. runserver — лише для розробки.

SECRET_KEY для DEBUG=1 автоматично зберігається у .local-secret з правами 600. .env не завантажується автоматично: змінні передаються оболонкою або керівником процесу. DEBUG приймає «1» для розробки, «0» для production; ALLOWED_HOSTS — список хостів через кому без пробілів. Шлях SQLite задано в config/settings.py, окремої DB_PATH у поточній конфігурації немає. Паролі, .env та база виключені з Git.

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

Моделі авто: Model S, Model 3, Model X, Model Y, Cybertruck, Roadster. Статуси API: received, diagnosis, approval, parts, repair, ready, delivered. quantity — від 0.01, до 8 цифр загалом і 2 після крапки; unit_price — до 10 і 2. Decimal у відповіді — рядки. VIN має 17 латинських літер або цифр без I, O, Q; email за наявності має коректний формат і довжину до 254 символів. Порожній plate і текстові примітки дозволені. Сервер нормалізує VIN до верхнього регістру та перевіряє його унікальність після нормалізації.
Параметри query: orders приймає status:string, overdue=true, vehicle:int, number:string (ST-0005 або 5), search:string, page:int. vehicles — customer:int, search, page. customers — search, page. items — page. Пошук номера ST у клієнті використовує number, а не search. vehicle/customer/number приймають невід’ємні ASCII-цілі до 9223372036854775807; 0 означає порожню вибірку. Невалідний vehicle/customer/number дає 400. Невідомий status повертає порожню вибірку, а overdue застосовується лише для точного значення true. Невідома сторінка — 404.

## Приклади запитів і відповідей

Нижче id та часові мітки ілюстративні; FK мають посилатися на існуючі доступні записи. Повний машинозчитуваний набір прикладів — docs/api-examples.json.

POST /api/customers/ з Content-Type: application/json

```json
{"name":"Демо клієнт","phone":"000"}
```

Відповідь 201

```json
{
  "id":5, "name":"Демо клієнт", "phone":"000",
  "email":"", "notes":"",
  "created_at":"2026-09-29T12:00:00+03:00"
}
```

POST /api/orders/5/transition/

```json
{"status":"delivered"}
```

Якщо замовлення у стані received, відповідь 400

```json
{"status":"Недозволений перехід статусу."}
```

Створення авто POST /api/vehicles/

```json
{
  "customer":5, "model":"Model Y", "year":2023,
  "vin":"TEST0000000000099", "mileage":12000
}
```

Відповідь 201 містить ці поля, id, customer_name і plate. Неправильний VIN або дублікат дає 400 з ключем vin і масивом пояснень.

Створення замовлення POST /api/orders/

```json
{
  "vehicle":5, "mechanic":2,
  "complaint":"Огляд підвіски", "due_date":"2026-10-01"
}
```

Відповідь 201 — повний Order із number, status received, status_label, total «0.00», порожнім items і transitions. PATCH /api/orders/5/ повертає ту саму форму об’єкта після зміни.

Приклад зміни діагностики PATCH /api/orders/5/

```json
{"diagnosis":"Огляд завершено", "fault_codes":""}
```

Кошторис POST /api/items/

```json
{
  "order":5, "kind":"labor", "name":"Огляд",
  "quantity":"1.50", "unit_price":"1000.00"
}
```

Відповідь 201

```json
{
  "id":5, "order":5, "kind":"labor", "name":"Огляд",
  "quantity":"1.50", "unit_price":"1000.00"
}
```

PATCH /api/items/5/ із quantity «2.00» повертає 200 з оновленим об’єктом. DELETE /api/items/5/ повертає 204 без тіла, якщо замовлення відкрите.

Коментар POST /api/orders/5/comment/

```json
{"text":"Погодження очікується"}
```

Відповідь 201

```json
{
  "id":10, "kind":"comment", "text":"Погодження очікується",
  "author_name":"admin",
  "created_at":"2026-09-29T12:00:00+03:00"
}
```

GET /api/orders/5/history/ повертає масив Event без пагінації. Звичайні списки customers/vehicles/orders/items мають оболонку пагінації. Наприклад, GET /api/customers/?search=NO-MATCH повертає 200:

```json
{"count":0, "next":null, "previous":null, "results":[]}
```

GET ресурсу за id повертає 200 з об’єктом або 404 з detail. PUT/PATCH customers і vehicles повертають 200; DELETE — 204 або 400 за наявності залежностей. GET /api/session/ повертає username, manager, mechanics та statuses; для механіка mechanics порожній. Повні схеми всіх відповідей і приклади операцій зберігаються у docs/openapi.yaml та docs/api-examples.json у репозиторії.

## Коди стану й помилки
200 — читання/оновлення; 201 — створення; 204 — видалення; 400 — некоректні поля, статус або пов’язані записи; 403 — немає сесії/прав/CSRF; 404 — об’єкт чи сторінку не знайдено; 405 — метод не підтримується; 429 — перевищено throttle; 500 — неочікувана помилка сервера. Помилки полів — об’єкт із назвами полів та повідомленнями; загальні — detail. Текст може залежати від локалізації, тому інтеграція має перевіряти код і ключі, а не повне речення.

## Правила статусів

received → diagnosis; diagnosis → approval/parts/repair; approval → diagnosis/parts/repair; parts → diagnosis/repair; repair → diagnosis/parts/ready; ready → repair/delivered; delivered не має вихідних переходів. Видача механіком повертає 400 за бізнес-правилом. Масив transitions описує граф, а не гарантує право поточного користувача на кожну дію: остаточна перевірка на сервері. Після delivered поля й кошторис закриті, коментарі дозволені. Історія містить створення, статуси й коментарі, але не повний аудит редагування полів.

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


### Налаштування серверного процесу

Для Linux обери підтримуваний WSGI-сервер, наприклад Gunicorn, установи його окремо та зафіксуй версію в deployment-залежностях. Його немає у поточному requirements.txt. Запуск із активного venv після встановлення: gunicorn config.wsgi:application --bind 127.0.0.1:8000. Кількість процесів і таймаути визначаються за навантаженням; SQLite не слід масштабувати простим збільшенням workers.

Перед запуском передай DEBUG=0, випадковий SECRET_KEY та ALLOWED_HOSTS з реальним доменом. Обліковий запис процесу повинен мати доступ до каталогу БД для журналів SQLite. Запусти migrate, collectstatic --noinput і check --deploy з цим самим середовищем. Налаштуй керівник процесу з автоперезапуском, журналами та обмеженими правами; статику віддавай із staticfiles/ через reverse proxy.

Для TLS-термінації на контрольованому reverse proxy у окремому production settings-модулі додай SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https"). Proxy має перезаписувати цей заголовок, а backend бути недоступним напряму з інтернету. Інакше можливі недовірені заголовки або циклічне HTTPS-перенаправлення. За потреби окремого origin явно налаштуй CSRF_TRUSTED_ORIGINS з https://; для одного origin зайві дозволи не потрібні. HSTS увімкни після перевірки HTTPS. Ці параметри зараз не читаються з однойменних env автоматично; потрібен production settings-модуль і DJANGO_SETTINGS_MODULE.

Після розгортання перевір статичні файли, login/logout, CSRF, ролі, створення тестового замовлення, кошторис та видачу. Лише після цього відкривай доступ користувачам. Під час оновлення зроби узгоджену резервну копію, застосуй міграції, збери статику й повтори перевірки. План відкату має враховувати сумісність схеми: не запускай старий код поверх несумісної міграції, відновлюй перевірену пару коду і бази.

### Перевірка відновлення

Створи резервну копію через sqlite3.Connection.backup у закритому каталозі поза Git. На окремому екземплярі перевір PRAGMA integrity_check, кількість основних сутностей, авторизацію, історію й контрольну суму кошторису. Не замінюй активну робочу БД під час перевірки. Автоматизованої production-процедури резервування в цьому MVP поки немає.

## Підтримка документації

Зміни моделі супроводжуй міграцією; зміни API — оновленням docs/openapi.yaml, docs/api-examples.json та цього документа. Контракт генерується командою python manage.py spectacular --file docs/openapi.yaml --validate. У static/api.js зберігай централізовану обробку JSON/204, CSRF та помилок. Pull request має містити опис і перевірки; незалежне review та реальний UAT залишаються відкритими.

Відомі проблеми: старі demo VIN, відкладене повторне відкриття діалогу, повідомлення помилки поза діалогом, відмінювання лічильника. Вони зареєстровані в Issues 9, 10, 11 і 15; ПЗ29 не є їхнім виправленням. Зовнішній аудит швидкодії виконано в ПЗ25 на тимчасовому штучному демо; це не підтверджує production-готовність.

Репозиторій і вихідні контракти

https://github.com/s6a6t6anfil-create/servicetrack-tesla/tree/docs/pz29-technical

У гілці: docs/14-api.md — докладний контракт, docs/openapi.yaml — схема, docs/api-examples.json — приклади, CONTRIBUTING.md — порядок роботи з Git. /api/ також надає корінь DRF router; HEAD/OPTIONS — службові методи, де дозволені DRF. /admin/ — службове адміністрування, /accounts/ — Django auth, / — захищений інтерфейс; це не бізнес-ендпоїнти JSON.
