web: python core/manage.py migrate --noinput && gunicorn --chdir core core.wsgi:application --bind 0.0.0.0:$PORT
