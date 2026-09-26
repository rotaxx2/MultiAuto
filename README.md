# MultiAuto

MultiAuto - multi-tenant платформа для записи клиентов на автомойку через Telegram Bot и Telegram Mini App с отдельной защищенной административной частью для администраторов и владельцев автомоек.

Текущий этап проекта: Django backend, Telegram Bot integration и базовый Telegram Mini App на React.

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
- aiogram 3
- React
- TypeScript
- Vite
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
      telegram_bot/
      cars/
      services/
      workstations/
      schedules/
  frontend/
    src/
      api/
      components/
      hooks/
      layouts/
      pages/
      types/
      utils/
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
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_MINI_APP_URL=http://localhost:5173
TELEGRAM_DEFAULT_ORGANIZATION_SLUG=clean-auto
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Основная база данных проекта - PostgreSQL. Можно использовать `DATABASE_URL` вместо отдельных `POSTGRES_*` переменных.

Где брать значения:

- `SECRET_KEY` - локально можно сгенерировать любой длинный случайный ключ; в production хранится в secret manager.
- `POSTGRES_*` - значения вашей локальной или production PostgreSQL базы.
- `DATABASE_URL` - альтернатива `POSTGRES_*`, обычно дает hosting provider или администратор базы.
- `TELEGRAM_BOT_TOKEN` - выдает BotFather после создания бота.
- `TELEGRAM_BOT_USERNAME` - username созданного Telegram-бота.
- `TELEGRAM_MINI_APP_URL` - URL Vite dev server локально или HTTPS URL production Mini App.
- `TELEGRAM_DEFAULT_ORGANIZATION_SLUG` - slug организации из таблицы `organizations`, нужен для локального запуска без deep link.
- `CORS_ALLOWED_ORIGINS` и `CSRF_TRUSTED_ORIGINS` - frontend origins, которым разрешено обращаться к backend.

`.env.example` хранит только шаблон и безопасные примеры. Реальные пароли, токены и production hosts пишутся в локальный `.env`, который уже исключен в `.gitignore`.

Выполнить проверки и миграции:

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
```

Создать демо-данные, чтобы Mini App показывал филиал, услуги, боксы и доступные слоты:

```powershell
python manage.py seed_demo_data
```

Команда создает/обновляет:

- `Organization` со slug `clean-auto`;
- один активный филиал;
- услуги `Кузов`, `Салон`, `Комплексная мойка`, `Воск`, `Химчистка`;
- три активных бокса;
- расписание 09:00-21:00 с понедельника по субботу, воскресенье закрыто.

Для запуска без PostgreSQL во время локального просмотра можно использовать тестовую SQLite-конфигурацию:

```powershell
python manage.py migrate --settings=config.settings.test
python manage.py seed_demo_data --settings=config.settings.test
python manage.py runserver --settings=config.settings.test
```

Запустить Django:

```powershell
python manage.py runserver
```

Запустить Telegram Bot polling:

```powershell
python manage.py run_telegram_bot
```

Запустить тесты:

```powershell
python manage.py test --settings=config.settings.test
```

`config.settings.test` использует локальную SQLite-базу только для быстрых model tests, когда PostgreSQL-сервер не поднят. Development и production settings используют PostgreSQL.

## Локальный запуск frontend

```powershell
cd frontend
npm install
npm run dev
```

Создать `frontend/.env` на основе `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

Сборка:

```powershell
npm run build
```

## Telegram client auth

Mini App отправляет Telegram `initData` на:

```text
POST /api/v1/client/auth/telegram
```

Backend проверяет подпись Telegram, создает или находит `CLIENT` и возвращает DRF token. Дальше клиентские API вызываются с заголовком:

```text
Authorization: Token <token>
```

Базовые endpoint'ы текущего этапа:

- `GET /api/me/`
- `GET /api/my-profile/`
- `GET /api/my-cars/`
- `GET /api/my-bookings/`
- `GET /api/services/`
- `GET /api/branches/`
- `GET /api/branches/{id}/services/`
- `GET /api/branches/{id}/schedule/`
- `GET /api/branches/{id}/availability/?date=YYYY-MM-DD&service_id={id}`
- `POST /api/bookings/`
- `GET /api/my-bookings/{id}/`
- `POST /api/my-bookings/{id}/cancel/`
- `GET /api/admin/bookings/`
- `GET /api/admin/bookings/{id}/`
- `PATCH /api/admin/bookings/{id}/`

`/api/my-cars/` поддерживает `GET`, `POST`, `GET/PATCH/DELETE` по `id`. Все операции используют текущего пользователя из token auth.

Booking Engine на backend рассчитывает `end_at`, назначает свободный `Workstation`, сохраняет snapshot цены из `Service.price` и проверяет пересечения в транзакции. Frontend не передает `organization_id`, `client_id`, `workstation_id`, `end_at`, `status` или `price`.

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
