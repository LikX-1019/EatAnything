# Eat Anything Backend

FastAPI backend for the “今天吃什么” mini app. It connects directly to the existing local PostgreSQL and MinIO services and does not require Docker.

## Local setup

1. Keep local credentials in the repository root `.env`.
2. Apply the additive migration:

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend').Path
alembic -c backend\alembic.ini upgrade head
```

3. Create an administrator when management APIs are needed:

```powershell
D:\develop\anaconda3\python.exe backend\scripts\create_admin.py admin --display-name "Local Admin"
```

4. Start the API:

```powershell
backend\scripts\run_local.ps1 -Reload
```

The API is available at `http://127.0.0.1:8000`, Swagger UI at `/docs`, and readiness at `/health/ready`.

For local mini-app development, set `DEV_AUTH_ENABLED=true` and call `POST /api/v1/auth/dev-login` with `{"externalId":"demo-user"}`. Never enable development login in production.

## Verification

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend').Path
python -m compileall -q backend\app
pytest backend\tests -q
```
