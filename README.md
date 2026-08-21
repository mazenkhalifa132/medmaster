# MedMaster

Django application prepared for deployment to RunSite, Railway, or any Docker-compatible host.

## Upload and deploy

1. Upload this folder to a Git repository. Do not upload `.venv`, `.env`, or `staticfiles`.
2. Create a PostgreSQL database on the hosting provider and connect it to the app.
3. Add the variables from `.env.example` in the provider's environment-variable settings.
4. Deploy. RunSite and Docker hosts use the included `Dockerfile`. Railway automatically uses `railway.toml`. On a Procfile-compatible host, configure `bash build.sh` as the build command.

The deploy process installs `requirements.txt`, collects static files, runs migrations, and starts Gunicorn.

## Required environment variables

- `SECRET_KEY` — a long, random Django secret.
- `DEBUG=False`
- `ALLOWED_HOSTS` — comma-separated public hostnames, with no protocol.
- `CSRF_TRUSTED_ORIGINS` — comma-separated HTTPS origins, such as `https://app.example.com`.
- `DATABASE_URL` — PostgreSQL connection URL supplied by the host.

For RunSite, provision PostgreSQL in the **same project** as the web service, then copy its **internal connection URL** directly into the web service's `DATABASE_URL` variable. Do not use an IP address or construct the URL manually.

`ADMIN_USERNAME` is optional. Set it only after that user has been created; a deploy with an unknown username deliberately fails instead of creating an unintended account.

## Included deployment files

- `requirements.txt` — exact production Python dependencies.
- `railway.toml` — Railway build, migration, and start commands.
- `Dockerfile` — container deployment configuration.
- `Procfile` — process command for Procfile-compatible hosts.
- `build.sh` — dependency installation and static-file build script.
- `start.sh` — waits for PostgreSQL, applies migrations, then starts Gunicorn.
- `.env.example` — safe environment-variable template.
