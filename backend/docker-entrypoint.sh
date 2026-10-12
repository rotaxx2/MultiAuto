#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-false}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

if [ "$#" -eq 1 ]; then
  exec /bin/sh -c "$1"
fi

exec "$@"
