#!/usr/bin/env sh
set -eu

# Managed databases can take a short time to accept connections after a
# deployment or restart. Retry migrations before starting the web process.
attempt=1
max_attempts=24

while ! python core/manage.py migrate --noinput; do
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "Database did not become available after $max_attempts attempts."
        exit 1
    fi

    echo "Database is not ready (attempt $attempt/$max_attempts); retrying in 5 seconds..."
    attempt=$((attempt + 1))
    sleep 5
done

python core/manage.py ensure_admin
exec gunicorn --chdir core core.wsgi:application --bind "0.0.0.0:${PORT:-8080}"
