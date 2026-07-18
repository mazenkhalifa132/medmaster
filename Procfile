web: python core/manage.py migrate --noinput && python core/manage.py ensure_admin && gunicorn --chdir core core.wsgi:application --bind 0.0.0.0:$PORT
