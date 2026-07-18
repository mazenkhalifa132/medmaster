FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python core/manage.py collectstatic --noinput

CMD ["sh", "-c", "python core/manage.py migrate --noinput && gunicorn --chdir core core.wsgi:application --bind 0.0.0.0:${PORT:-8080}"]
