#!/bin/bash
set -e

export FLASK_APP=fitbit2influx.factory
export FLASK_ENV=production
export FB2I_PORT=${FB2I_PORT:-5000}

source venv/bin/activate

if [ "$1" = 'fb2i' ]; then
  exec gunicorn -k gevent -b :${FB2I_PORT} --access-logfile - --error-logfile - fitbit2influx.wsgi:app
fi

exec "$@"
