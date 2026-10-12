# MultiAuto

MultiAuto - multi-tenant платформа для записи клиентов на автомойку через Telegram Bot и Telegram Mini App с отдельной защищенной административной частью для администраторов и владельцев автомоек.

Текущий этап проекта: Django backend, Telegram Bot integration и базовый Telegram Mini App на React.

## Цель

Создать коммерчески ориентированную систему, которую можно развивать после MVP и подключать к нескольким автомойкам.

## Architecture

```text
Telegram Bot / Telegram Mini App
  -> Django REST API
  -> PostgreSQL
  -> Redis
  -> Celery Worker / Celery Beat
  -> Telegram Notifications
```

Backend отвечает за API, tenant isolation, booking engine, availability, admin endpoints и health checks. Frontend Mini App собирается отдельно через Vite. Redis используется как broker/result backend для Celery reminders.

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
- [DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) - подготовка и проверка деплоя на Render.

## Текущий стек

- Python 3.12+
- Django 5.1
- Django REST Framework 3.15
- aiogram 3
- React
- TypeScript
- Vite
- PostgreSQL
- Redis
- Celery
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
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO
POSTGRES_DB=multiauto
POSTGRES_USER=multiauto
POSTGRES_PASSWORD=multiauto
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_MINI_APP_URL=http://localhost:5173
TELEGRAM_DEFAULT_ORGANIZATION_SLUG=clean-auto
BOOKING_REMINDER_POLL_SECONDS=300
BOOKING_STATUS_SWEEP_SECONDS=300
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_BOOKING_REMINDER_RETRY_COUNTDOWN=60
CELERY_BOOKING_REMINDER_MAX_RETRIES=3
CELERY_WORKER_PREFETCH_MULTIPLIER=1
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
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
- `CELERY_BROKER_URL` и `CELERY_RESULT_BACKEND` - Redis URL для Celery worker, beat и результатов задач.
- `BOOKING_STATUS_SWEEP_SECONDS` - интервал Celery Beat для автоматического перевода просроченных `PENDING`/`CONFIRMED` записей в `NO_SHOW`.
- `CELERY_BOOKING_REMINDER_*` - retry-настройки отправки reminder-уведомлений.
- `SECURE_*` - production HTTPS/HSTS настройки; локально обычно выключены.
- `LOG_LEVEL` и `DJANGO_LOG_LEVEL` - уровень логирования приложения и Django.
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

Запустить Celery worker для фоновых задач:

```powershell
celery -A config worker -l info --pool=solo
```

Запустить Celery Beat для периодической проверки due reminders:

```powershell
celery -A config beat -l info
```

Локально Redis должен быть доступен по `CELERY_BROKER_URL`, например `redis://localhost:6379/0`. На Windows Redis обычно запускают через Docker или WSL.

Compatibility-команды reminders оставлены для ручной проверки:

```powershell
python manage.py send_booking_reminders
python manage.py run_booking_reminder_worker
```

Запустить тесты:

```powershell
python manage.py test --settings=config.settings.test
```

`config.settings.test` использует локальную SQLite-базу только для быстрых model tests, когда PostgreSQL-сервер не поднят. Development и production settings используют PostgreSQL.

## Health checks

Backend предоставляет:

```text
GET /health/
GET /health/celery/
```

`/health/` проверяет Django process, database и Redis. `/health/celery/` проверяет Redis и наличие ответа от Celery worker через inspect ping. Ответы не содержат секретов, connection strings или токенов.

## Локальный запуск frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

Создать `frontend/.env` на основе `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:8000
```

Сборка:

```powershell
pnpm build
```

Если Windows запрещает создание pnpm symlink'ов, можно локально поставить зависимости без изменения lockfile:

```powershell
pnpm install --frozen-lockfile --config.node-linker=hoisted
```

## Docker

Compose-стек предназначен для production-like локального запуска:

```powershell
docker compose build
docker compose up -d
```

Контейнер `backend` по умолчанию выполняет `python manage.py migrate --noinput` и `python manage.py collectstatic --noinput` перед запуском Gunicorn. Celery worker и Celery Beat запускаются отдельными контейнерами и не выполняют миграции. Если миграции или collectstatic нужно отключить для конкретного deployment flow, задайте `RUN_MIGRATIONS=false` или `RUN_COLLECTSTATIC=false`.

Сервисы:

- `backend` - Django API через Gunicorn.
- `postgres` - PostgreSQL с volume `postgres_data`.
- `redis` - Redis broker/result backend для Celery.
- `celery_worker` - обработка background tasks.
- `celery_beat` - периодический запуск reminder scan.

PostgreSQL и Redis доступны контейнерам по service names `postgres` и `redis`; внутри compose не используется `localhost` для межконтейнерных подключений. Для настоящего production deployment задайте реальные `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, Telegram-переменные и HTTPS/HSTS настройки через environment/secret manager. `.env` не должен попадать в Git или Docker image.

## Render

В корне есть `render.yaml` для Render Blueprint. Он описывает отдельные сервисы:

- `multiauto-backend` - Django API web service.
- `multiauto-mini-app` - static Vite Mini App.
- `multiauto-telegram-bot` - один Background Worker для Telegram polling.
- `multiauto-celery-worker` - Celery Worker.
- `multiauto-celery-beat` - один Background Worker для расписания Celery Beat.
- `multiauto-postgres` - PostgreSQL.
- `multiauto-redis` - Redis-compatible Render Key Value.

Перед созданием ресурсов проверьте актуальные тарифы Render: PostgreSQL, Key Value и фоновые workers могут оплачиваться отдельно, а production persistence и always-on процессы обычно требуют осознанного выбора плана. Секреты заполняются в Render environment settings, не в `render.yaml`.

Подробная инструкция: [DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md).

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
