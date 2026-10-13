# Deploy to Render

This document describes the supported Render deployment path for MultiAuto.

Do not commit real tokens, passwords, private keys, or production URLs. Fill secrets in the Render dashboard.

## Cost checkpoint

As of 2026-10-12, Render free instances are available for web services, static sites, Render Postgres, and Render Key Value. Background Workers do not support the Free instance type. That means a fully working production deployment with Telegram polling, Celery Worker, and Celery Beat requires paid worker services, or an owner-approved alternative outside Render.

The checked-in `render.yaml` includes the core services and the Telegram polling worker:

- `multiauto-backend` - Django API web service, Docker runtime.
- `multiauto-mini-app` - static Vite Mini App.
- `multiauto-telegram-bot` - Background Worker for Telegram long polling.
- `multiauto-postgres` - Render Postgres.
- `multiauto-redis` - Render Key Value for Celery/Redis-compatible broker.

Do not apply or create paid worker services until the project owner explicitly approves the cost. If you need a no-cost Blueprint apply, remove or skip the worker service in Render before applying.

## Worker model

MultiAuto needs three continuous non-HTTP processes for full production behavior:

- Telegram bot polling: `python manage.py run_telegram_bot`
- Celery Worker: `celery -A config worker -l info`
- Celery Beat: `celery -A config beat -l info --pidfile=`

Render Background Workers are the right service type for these commands, but they are not available on the free instance type. The active Blueprint includes only the Telegram worker because `/start` requires a running polling process. Celery Worker and Celery Beat still require separate paid Background Workers before reminders and scheduled status sweeps are fully production-ready.

## Blueprint behavior

The backend Docker service does not set `dockerCommand` in the Blueprint. Render uses the Docker image `CMD`, which points to `backend/start-web.sh`.

The backend Dockerfile uses:

```dockerfile
ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
CMD ["/app/backend/start-web.sh"]
```

`backend/docker-entrypoint.sh` runs migrations and collectstatic first. `backend/start-web.sh` then validates `PORT` and `WEB_CONCURRENCY` and starts Gunicorn.

On the free backend plan, Render does not support `preDeployCommand`. The current free-plan fallback is:

```yaml
RUN_MIGRATIONS=true
RUN_COLLECTSTATIC=true
```

The backend Docker entrypoint runs:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

before starting Gunicorn. This avoids running migrations in Telegram/Celery processes and keeps database data intact. The tradeoff is that this is not as clean as Render's paid `preDeployCommand` because it runs inside the web service startup path.

If the backend is upgraded to a paid compute plan, prefer:

```yaml
preDeployCommand: python manage.py migrate --noinput
RUN_MIGRATIONS=false
```

## Required Blueprint variables

Set these when Render prompts for variables marked `sync: false`:

- `ALLOWED_HOSTS`: backend host without scheme. The Blueprint default is `multiauto-backend.onrender.com`; replace it if Render creates a different backend hostname.
- `CORS_ALLOWED_ORIGINS`: frontend HTTPS origin, for example `https://multiauto-mini-app.onrender.com`.
- `CSRF_TRUSTED_ORIGINS`: same HTTPS frontend origin.
- `TELEGRAM_BOT_TOKEN`: BotFather token. Required by worker services and notification tasks.
- `TELEGRAM_BOT_USERNAME`: bot username.
- `TELEGRAM_MINI_APP_URL`: frontend HTTPS URL opened from Telegram.
- `TELEGRAM_DEFAULT_ORGANIZATION_SLUG`: active organization slug, for example `clean-auto`.
- `VITE_API_URL`: backend HTTPS origin, for example `https://multiauto-backend.onrender.com`.

Render generates `SECRET_KEY`. `DATABASE_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` are wired from Render Postgres and Render Key Value.

`VITE_API_URL` is a build-time Vite variable. If the backend URL changes, redeploy the static Mini App so the bundle is rebuilt.

## Telegram polling worker

The Telegram bot uses long polling, not webhook. Django does not expose a Telegram webhook route. The worker must run exactly one process with:

```bash
python manage.py run_telegram_bot
```

The command removes any active webhook with `drop_pending_updates=False`, then starts aiogram polling. Pending Telegram updates are intentionally preserved across deploys and restarts.

The `multiauto-telegram-bot` service in `render.yaml` uses:

- Runtime: Docker
- Service type: Background Worker
- Plan: `starter` or another owner-approved paid worker plan
- Dockerfile path: `./backend/Dockerfile`
- Docker context: `.`
- Docker command: `python manage.py run_telegram_bot`
- Instances: exactly 1

Required variables:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `SECRET_KEY`: same value as backend
- `DEBUG=False`
- `ALLOWED_HOSTS`: same backend host value
- `DATABASE_URL`: same Render Postgres connection string as backend
- `TELEGRAM_BOT_TOKEN`: BotFather token
- `TELEGRAM_BOT_USERNAME`: bot username
- `TELEGRAM_MINI_APP_URL`: public HTTPS Mini App URL
- `TELEGRAM_DEFAULT_ORGANIZATION_SLUG`: active organization slug, for example `clean-auto`
- `RUN_MIGRATIONS=false`
- `RUN_COLLECTSTATIC=false`

Redis is not required by the polling process itself. Do not set `CELERY_BROKER_URL` or `CELERY_RESULT_BACKEND` on the Telegram worker unless another imported code path starts using Redis.

Check the worker logs after deploy. A healthy startup includes `Starting Telegram bot polling.`. On shutdown, the command logs that the Telegram HTTP session was closed. Logs must not include the bot token.

Do not scale Telegram polling above one instance. Multiple pollers using one bot token compete for updates and can produce unstable behavior.

## Celery worker services after approval

After the owner approves additional paid Background Workers, create exactly these Celery services manually or add them to `render.yaml` in a separate approved change.

Use the same repository, branch, Dockerfile path, and context:

- Runtime: Docker
- Dockerfile path: `./backend/Dockerfile`
- Docker context: `.`
- Environment:
  - `DJANGO_SETTINGS_MODULE=config.settings.production`
  - `SECRET_KEY`: same value as backend
  - `DEBUG=False`
  - `ALLOWED_HOSTS`: same value as backend
  - `DATABASE_URL`: same Render Postgres connection string
  - `CELERY_BROKER_URL`: same Render Key Value connection string
  - `CELERY_RESULT_BACKEND`: same Render Key Value connection string
  - `RUN_MIGRATIONS=false`
  - `RUN_COLLECTSTATIC=false`

Celery Worker:

- Service type: Background Worker
- Docker command: `celery -A config worker -l info`
- Additional variables: `TELEGRAM_BOT_TOKEN`, `CELERY_BOOKING_REMINDER_RETRY_COUNTDOWN`, `CELERY_BOOKING_REMINDER_MAX_RETRIES`, `CELERY_WORKER_PREFETCH_MULTIPLIER`

Celery Beat:

- Service type: Background Worker
- Instances: exactly 1
- Docker command: `celery -A config beat -l info --pidfile=`
- Additional variables: `BOOKING_REMINDER_POLL_SECONDS`, `BOOKING_STATUS_SWEEP_SECONDS`

Do not scale Celery Beat above one instance.

## Deployment order

1. Apply the Blueprint for Postgres, Key Value, backend, and static Mini App.
2. Fill all required environment variables.
3. Deploy backend and confirm logs show migrations completed before Gunicorn starts.
4. Deploy Mini App after `VITE_API_URL` points to the backend HTTPS origin.
5. Check backend health:

   ```powershell
   Invoke-WebRequest https://YOUR_BACKEND_HOST/health/
   ```

6. Check Mini App shell:

   ```powershell
   Invoke-WebRequest https://YOUR_FRONTEND_HOST/
   ```

7. Only after paid worker approval, create or apply the Telegram bot worker.
8. In BotFather, set the Mini App URL to the Render static site URL.
9. Check the Telegram worker logs for `Starting Telegram bot polling.`.
10. Send `/start org_<slug>` to the bot and test Telegram Mini App auth.
11. Only after separate paid worker approval, create Celery Worker and Celery Beat, then test booking reminders.

## Manual data/setup commands

Do not run `createsuperuser` automatically. If needed, run it manually from a backend shell on a paid plan or another controlled environment:

```bash
python manage.py createsuperuser
```

Use demo seed data only for test/staging:

```bash
python manage.py seed_demo_data --slug clean-auto
```

## Troubleshooting

- Backend still starts an old Gunicorn command: clear any manual Docker Command override in the Render service settings and sync the Blueprint again. The checked-in Blueprint intentionally omits `dockerCommand` for the backend.
- Blueprint rejects pre-deploy command: free compute does not support `preDeployCommand`; use backend entrypoint migration or upgrade backend to paid and add `preDeployCommand`.
- `DisallowedHost`: add the backend host to `ALLOWED_HOSTS`.
- CORS/CSRF errors: check exact `https://` origins in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
- Mini App calls localhost: set `VITE_API_URL` on the static site and redeploy it.
- Bot does not answer: verify the paid Telegram Background Worker exists, has one instance, has `TELEGRAM_BOT_TOKEN`, and logs `Starting Telegram bot polling.`.
- Telegram reports pending updates: verify `getWebhookInfo` has `url: ""`, then verify the worker is running. The polling command preserves pending updates and does not call `drop_pending_updates=True`.
- aiogram/Pydantic import fails: capture the first traceback line with the final exception type from the Telegram worker logs. The web backend should not import `apps.telegram_bot.bot` during URLconf loading; notification delivery imports it only when a Telegram message is actually sent.
- Reminders are not sent: verify paid Celery Worker and Celery Beat exist, and Redis/Key Value URLs are set.
- Data disappears: confirm production uses Render Postgres via `DATABASE_URL`, not SQLite or container local files.
