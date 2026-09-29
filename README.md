# ServiceTrack Tesla

Навчальний MVP вебзастосунку для однієї незалежної майстерні Tesla. Клієнти, автомобілі, замовлення, сім статусів, діагностика й ручні коди помилок, кошторис, історія та коментарі. Проєкт не підключається до автомобілів і не є діагностичним приладом.

## Зафіксований навчальний реліз

Версія [v1.0.0](https://github.com/s6a6t6anfil-create/servicetrack-tesla/releases/tag/v1.0.0), стабільна гілка `release-v1.0.0`. Для перевірки всіх накопичених робіт використовуйте цей тег; попередні тематичні PR збережені як історія. [Release notes](RELEASE_NOTES.md), [підсумок ПЗ36](docs/36-release.md).

```sh
git clone --branch v1.0.0 https://github.com/s6a6t6anfil-create/servicetrack-tesla.git
cd servicetrack-tesla
```

## Локальний запуск
Python 3.12, Node.js 22+ потрібен лише для тестів JavaScript.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
export DEMO_PASSWORD='your-own-long-demo-password'
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8943
```

Демонстраційні облікові записи: admin та mechanic; пароль задається DEMO_PASSWORD. Команда seed_demo працює тільки з порожньою базою, щоб не змінювати існуючі записи. Усі демонстраційні особи та VIN вигадані. Для наявної бази створити адміністратора `python manage.py createsuperuser`, групи «Адміністратор» і «Механік» через /admin/ та призначити ролі.

Відкрити http://127.0.0.1:8943/.
API: /api/; схема /api/schema/; інтерактивний опис /api/docs/ (Swagger UI потребує доступу до CDN).

## Перевірка
```sh
python manage.py check
python manage.py test workshop --verbosity 2
node --test tests/*.test.js
python manage.py spectacular --file docs/openapi.yaml --validate
```

## Права й дані
Адміністратор створює клієнтів, авто, замовлення й позиції, призначає майстра та підтверджує видачу. Механік бачить лише призначені замовлення і пов’язаних клієнтів/авто, редагує діагностику та коди, додає коментарі, змінює дозволені статуси, крім «Видано». Закритий кошторис не редагується; пов’язані клієнти/авто захищені від видалення. Коментарі дозволені й після видачі для післяремонтних уточнень.

## Git
GitHub Flow: main для перевіреної версії; feature/* для задач; pull request і перевірка перед злиттям. Локальна історія реальна, без заднім числом створених комітів. Репозиторій: https://github.com/s6a6t6anfil-create/servicetrack-tesla (публічний на період практики). Інструкція для нового учасника, оновлення гілок, конфліктів та PR — [CONTRIBUTING.md](CONTRIBUTING.md). Незалежне людське review ще не проведене. Конфігурація CI передбачає перевірки push у main і pull request; успішний запуск GitHub Actions ще не підтверджений. Захист main на сервері не налаштований.

## Межі поточної версії
МVP локальний. Перед розміщенням із реальними даними потрібні HTTPS, production WSGI, резервні копії, захист входу від перебору, перевірка розгортання і прав. SQLite призначений для малого локального навантаження. Немає складу, онлайн-оплати, Tesla API/Toolbox, автоматичної діагностики. UAT із людьми і публічний захист ще не проведені. Зовнішній performance-аудит виконано в ПЗ25 на тимчасовому штучному демо; production-навантаження не перевірене.

## Документація API

Повний контракт, параметри й приклади всіх бізнес-операцій: [ПЗ14 — API](docs/14-api.md). Машиночитана схема: [OpenAPI](docs/openapi.yaml).

## Реалізація Back-end

[Звіт ПЗ15 та результати перевірки](docs/15-backend.md).
