# MultiAuto

MultiAuto - multi-tenant платформа для записи клиентов на автомойку через Telegram Bot и Telegram Mini App с отдельной защищенной административной частью для администраторов и владельцев автомоек.

Текущий этап проекта: Backend Foundation на Django. Telegram Bot, Mini App, booking engine, уведомления и frontend будут добавляться следующими этапами.

## Цель

Создать коммерчески ориентированную систему, которую можно развивать после MVP и подключать к нескольким автомойкам.

Основная структура продукта:

```text
Organization
  -> Branch
  -> Services
  -> Workstations
  -> Working Schedule
  -> Administrators
  -> Customers
  -> Cars
  -> Bookings
```

## Роли

В системе есть только три роли:

- `CLIENT` - клиент автомойки, работает через Telegram Mini App.
- `ADMIN` - администратор организации, управляет операционной частью.
- `OWNER` - владелец организации, управляет администраторами, филиалами и настройками.

Роли обычных сотрудников, мойщиков или staff-аккаунтов не используются.

## Документация

- [01_PRODUCT_REQUIREMENTS.md](docs/01_PRODUCT_REQUIREMENTS.md) - продуктовые требования и границы MVP.
- [02_SYSTEM_ARCHITECTURE.md](docs/02_SYSTEM_ARCHITECTURE.md) - системная архитектура и целевые модули.
- [03_USER_ROLES_AND_PERMISSIONS.md](docs/03_USER_ROLES_AND_PERMISSIONS.md) - роли, RBAC и матрица permissions.
- [04_DATABASE_DESIGN.md](docs/04_DATABASE_DESIGN.md) - сущности, поля, связи, индексы и tenant isolation.
- [05_BOOKING_LOGIC.md](docs/05_BOOKING_LOGIC.md) - расчет слотов, статусы, переносы и защита от double booking.
- [06_API_PLAN.md](docs/06_API_PLAN.md) - предварительный план Client API, Admin API и внутренних задач.
- [07_TELEGRAM_FLOW.md](docs/07_TELEGRAM_FLOW.md) - `/start`, Telegram identification, Mini App auth и уведомления.
- [08_MINI_APP_FLOW.md](docs/08_MINI_APP_FLOW.md) - клиентский путь в Telegram Mini App.
- [09_ADMIN_FLOW.md](docs/09_ADMIN_FLOW.md) - путь администратора и владельца.
- [10_SECURITY.md](docs/10_SECURITY.md) - authentication, authorization, RBAC, tenant isolation и API security.
- [11_ROADMAP.md](docs/11_ROADMAP.md) - этапы разработки после архитектурной фазы.

## Текущий стек

- Python 3.12+
- Django 5.1
- Django REST Framework 3.15
- PostgreSQL
- psycopg 3
- python-dotenv
- dj-database-url
- pytest / pytest-django для будущего расширения тестов

## Структура проекта

```text
MultiAuto/
  docs/
  backend/
    manage.py
    config/
      settings/
        base.py
        development.py
        production.py
        test.py
    apps/
      accounts/
      organizations/
      branches/
  requirements/
    base.txt
    development.txt
    production.txt
  .env.example
  README.md
```

## Локальный запуск backend

Создать виртуальное окружение:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```powershell
pip install -r ..\requirements\development.txt
```

Создать локальный `.env` на основе `.env.example`:

```powershell
Copy-Item ..\.env.example ..\.env
```

Заполнить переменные окружения:

```env
SECRET_KEY=local-development-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=multiauto
POSTGRES_USER=multiauto
POSTGRES_PASSWORD=multiauto
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Основная база данных проекта - PostgreSQL. Можно использовать `DATABASE_URL` вместо отдельных `POSTGRES_*` переменных.

Выполнить проверки и миграции:

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
```

Запустить Django:

```powershell
python manage.py runserver
```

Запустить тесты:

```powershell
python manage.py test --settings=config.settings.test
```

`config.settings.test` использует локальную SQLite-базу только для быстрых model tests, когда PostgreSQL-сервер не поднят. Development и production settings используют PostgreSQL.

## Что намеренно не входит в MVP

- система лояльности;
- бонусные баллы;
- VIP-уровни;
- учетные записи обычных сотрудников;
- онлайн-оплата;
- промокоды;
- маркетинговые рассылки;
- подписки для автомоек.

Некоторые из этих модулей могут быть добавлены позже, но они не являются частью текущей реализации.
