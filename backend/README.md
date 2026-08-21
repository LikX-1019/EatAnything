# “今天吃什么”后端

这是“今天吃什么”小程序的 FastAPI 后端。后端直接连接已有的 PostgreSQL 和 MinIO 服务，本机运行 API 时不要求同时运行 Docker。

## 本地运行

1. 将本地凭据保存在仓库根目录的 `.env` 中。
2. 执行增量数据库迁移：

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend').Path
alembic -c backend\alembic.ini upgrade head
```

3. 需要调用管理接口时，创建管理员：

```powershell
D:\develop\anaconda3\python.exe backend\scripts\create_admin.py admin --display-name "本地管理员"
```

4. 启动 API：

```powershell
backend\scripts\run_local.ps1 -Reload
```

API 地址为 `http://127.0.0.1:8000`，Swagger 文档地址为 `/docs`，就绪检查地址为 `/health/ready`。

本地开发小程序时，将 `DEV_AUTH_ENABLED` 设置为 `true`，并使用 `{"externalId":"demo-user"}` 调用 `POST /api/v1/auth/dev-login`。生产环境严禁启用开发登录。

## 通过 SSH 连接服务器服务

PostgreSQL 和 MinIO 保持不对公网开放。运行本地 API 前，先同步服务器连接配置并启动 SSH 隧道：

```powershell
backend\scripts\sync_server_service_env.ps1
backend\scripts\server_tunnel.ps1 Start
backend\scripts\run_local.ps1 -Reload
```

首次使用以及服务器凭据变化后，需要执行一次同步命令。该命令只更新本地 `.env` 中的 PostgreSQL 和 MinIO 配置项，不会输出密钥；`.env` 已被 Git 忽略。

检查或停止隧道：

```powershell
backend\scripts\server_tunnel.ps1 Status
backend\scripts\server_tunnel.ps1 Stop
```

隧道会将本机 PostgreSQL 地址 `127.0.0.1:5433` 和 MinIO 地址 `127.0.0.1:9000` 转发到服务器。凭据只保存在仓库根目录的 `.env` 中，不会出现在 SSH 命令行参数里。

## 生产部署

服务器端使用 Docker Compose 部署（PostgreSQL、MinIO、MinIO 初始化、API），完整步骤见仓库根目录的 [deploy/README.md](../deploy/README.md)。部署环境变量使用 `deploy/.env`，与本机开发的仓库根目录 `.env` 相互独立。

## 验证

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend').Path
python -m compileall -q backend\app
pytest backend\tests -q
```
