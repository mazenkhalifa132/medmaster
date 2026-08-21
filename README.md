# MedMaster

Django application prepared for deployment to Railway or any Docker-compatible host.

## Upload and deploy

1. Upload this folder to a Git repository. Do not upload `.venv`, `.env`, or `staticfiles`.
2. Create a PostgreSQL database on the hosting provider and connect it to the app.
3. Add the variables from `.env.example` in the provider's environment-variable settings.
4. Deploy. Railway automatically uses `railway.toml`; Docker hosts use the included `Dockerfile`. On a Procfile-compatible host, configure `bash build.sh` as the build command.

The deploy process installs `requirements.txt`, collects static files, runs migrations, and starts Gunicorn.

## Required environment variables

- `SECRET_KEY` — a long, random Django secret.
- `DEBUG=False`
- `ALLOWED_HOSTS` — comma-separated public hostnames, with no protocol.
- `CSRF_TRUSTED_ORIGINS` — comma-separated HTTPS origins, such as `https://app.example.com`.
- `DATABASE_URL` — PostgreSQL connection URL supplied by the host.

`ADMIN_USERNAME` is optional. Set it only after that user has been created; a deploy with an unknown username deliberately fails instead of creating an unintended account.

## Included deployment files

- `requirements.txt` — exact production Python dependencies.
- `railway.toml` — Railway build, migration, and start commands.
- `Dockerfile` — container deployment configuration.
- `Procfile` — process command for Procfile-compatible hosts.
- `build.sh` — dependency installation and static-file build script.
- `.env.example` — safe environment-variable template.
