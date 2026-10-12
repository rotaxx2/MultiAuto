# Deploy to Render

This document describes the supported Render deployment path for MultiAuto.

Do not commit real tokens, passwords, private keys, or production URLs. Fill secrets in the Render dashboard.

## Cost checkpoint

As of 2026-10-12, Render free instances are available for web services, static sites, Render Postgres, and Render Key Value. Background Workers do not support the Free instance type. That means a fully working production deployment with Telegram polling, Celery Worker, and Celery Beat requires paid worker services, or an owner-approved alternative outside Render.

The checked-in `render.yaml` intentionally creates only the free-compatible core:

- `multiauto-backend` - Django API web service, Docker runtime.
- `multiauto-mini-app` - static Vite Mini App.
- `multiauto-postgres` - Render Postgres.
- `multiauto-redis` - Render Key Value for Celery/Redis-compatible broker.

Do not create paid worker services until the project owner explicitly approves the cost.

## Why workers are not in render.yaml

MultiAuto needs three continuous non-HTTP processes for full production behavior:

- Telegram bot polling: `python manage.py run_telegram_bot`
- Celery Worker: `celery -A config worker -l info`
- Celery Beat: `celery -A config beat -l info --pidfile=`

Render Background Workers are the right service type for these commands, but they are not available on the free instance type. Putting them in `render.yaml` with a paid plan would create billable services during Blueprint apply, so the active Blueprint does not include them.

## Blueprint behavior

Docker services use `dockerCommand`, not `startCommand`, because Render rejects `startCommand` for `runtime: docker`.

The backend uses:

```yaml
dockerCommand: /bin/sh -c "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"
```

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

- `ALLOWED_HOSTS`: backend host, for example `multiauto-backend.onrender.com`.
- `CORS_ALLOWED_ORIGINS`: frontend HTTPS origin, for example `https://multiauto-mini-app.onrender.com`.
- `CSRF_TRUSTED_ORIGINS`: same HTTPS frontend origin.
- `TELEGRAM_BOT_TOKEN`: BotFather token. Required by worker services and notification tasks.
- `TELEGRAM_BOT_USERNAME`: bot username.
- `TELEGRAM_MINI_APP_URL`: frontend HTTPS URL opened from Telegram.
- `TELEGRAM_DEFAULT_ORGANIZATION_SLUG`: active organization slug, for example `clean-auto`.
- `VITE_API_URL`: backend HTTPS origin, for example `https://multiauto-backend.onrender.com`.

Render generates `SECRET_KEY`. `DATABASE_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` are wired from Render Postgres and Render Key Value.

`VITE_API_URL` is a build-time Vite variable. If the backend URL changes, redeploy the static Mini App so the bundle is rebuilt.

## Paid worker services after approval

After the owner approves paid Background Workers, create exactly these services manually or add them to `render.yaml` in a separate approved change.

Use the same repository, branch, Dockerfile path, and context for all three:

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

Telegram bot worker:

- Service type: Background Worker
- Instances: exactly 1
- Docker command: `python manage.py run_telegram_bot`
- Additional variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_MINI_APP_URL`, `TELEGRAM_DEFAULT_ORGANIZATION_SLUG`

Celery Worker:

- Service type: Background Worker
- Docker command: `celery -A config worker -l info`
- Additional variables: `TELEGRAM_BOT_TOKEN`, `CELERY_BOOKING_REMINDER_RETRY_COUNTDOWN`, `CELERY_BOOKING_REMINDER_MAX_RETRIES`, `CELERY_WORKER_PREFETCH_MULTIPLIER`

Celery Beat:

- Service type: Background Worker
- Instances: exactly 1
- Docker command: `celery -A config beat -l info --pidfile=`
- Additional variables: `BOOKING_REMINDER_POLL_SECONDS`, `BOOKING_STATUS_SWEEP_SECONDS`

Do not scale Telegram polling or Celery Beat above one instance.

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

7. Only after paid worker approval, create Telegram bot, Celery Worker, and Celery Beat services.
8. In BotFather, set the Mini App URL to the Render static site URL.
9. Send `/start org_<slug>` to the bot and test Telegram Mini App auth, booking creation, cancellation, and reminders.

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

- Blueprint rejects Docker command: check that Docker services use `dockerCommand`, not `startCommand`.
- Blueprint rejects pre-deploy command: free compute does not support `preDeployCommand`; use backend entrypoint migration or upgrade backend to paid and add `preDeployCommand`.
- `DisallowedHost`: add the backend host to `ALLOWED_HOSTS`.
- CORS/CSRF errors: check exact `https://` origins in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
- Mini App calls localhost: set `VITE_API_URL` on the static site and redeploy it.
- Bot does not answer: verify the paid Telegram Background Worker exists, has one instance, and has `TELEGRAM_BOT_TOKEN`.
- Reminders are not sent: verify paid Celery Worker and Celery Beat exist, and Redis/Key Value URLs are set.
- Data disappears: confirm production uses Render Postgres via `DATABASE_URL`, not SQLite or container local files.
