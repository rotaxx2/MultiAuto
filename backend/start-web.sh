#!/bin/sh
set -e

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"

case "$PORT" in
  ''|*[!0-9]*)
    PORT=8000
    ;;
esac

case "$WEB_CONCURRENCY" in
  ''|*[!0-9]*)
    WEB_CONCURRENCY=2
    ;;
esac

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}" --workers "${WEB_CONCURRENCY}"
