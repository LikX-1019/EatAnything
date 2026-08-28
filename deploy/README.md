# EatAnything 后端部署说明

本文档描述完整服务在服务器上的 Docker Compose 部署方式，覆盖 PostgreSQL、MinIO、API、通知 Worker、Web 管理后台、可选 Caddy HTTPS、数据库初始化与日常运维命令。手工命令默认在仓库根目录执行；`deploy/scripts/deploy.sh` 可从任意目录调用。

> 本仓库可通过 Caddy 自动申请和续期 HTTPS 证书。DNS、服务器防火墙、ICP备案和微信平台合法域名登记仍需在对应外部平台完成。

## 1. 环境要求

- Linux 服务器（或本机 Docker Desktop），已安装 Docker Engine 24+、Docker Compose v2（v2.17+，`docker compose` 子命令）与 GNU coreutils `timeout`。
- 可访问外网以下载镜像：`python:3.12-slim`、`postgres:16-alpine`、`minio/minio:RELEASE.2025-04-22T22-12-26Z`、`minio/mc:RELEASE.2025-04-16T18-13-26Z`（镜像标签可通过 `deploy/.env` 覆盖）。
- 默认占用宿主机端口：
  - `8000`：API（默认只绑定 `127.0.0.1`，通过 `API_BIND_HOST` / `API_PORT` 调整）；
  - `8080`：Web 管理后台（默认只绑定 `127.0.0.1`，通过 `ADMIN_WEB_BIND_HOST` / `ADMIN_WEB_PORT` 调整）；
  - `9000`：MinIO API（默认只绑定 `127.0.0.1`，通过 `MINIO_BIND_HOST` / `MINIO_PORT` 调整）；
  - `80`、`443/tcp`、`443/udp`：仅在 `ENABLE_CADDY=1` 时开放。
- PostgreSQL 与 MinIO Console 默认不暴露到宿主机公网。

## 2. 复制环境变量文件

```bash
cp deploy/.env.example deploy/.env
```

然后编辑 `deploy/.env` 填写真实值。`deploy/.env` 已被 `.gitignore` 忽略，不会进入 Git；`deploy/.env.example` 会进入 Git，只允许包含变量名和安全占位符。

模板默认使用 `COMPOSE_PROJECT_NAME=eatanything-prod`，仍需确认它在服务器上是当前环境的唯一名称；测试环境应改为 `eatanything-test`。该名称是 Compose 资源隔离的重要边界，脚本不会根据目录名推导，也没有隐式默认值。进程显式设置的 `COMPOSE_PROJECT_NAME` 优先于 `deploy/.env`。`POSTGRES_VOLUME`、`MINIO_VOLUME`、`NETWORK_NAME` 和 Caddy volume 名称也必须与目标部署保持一致。

本文件与仓库根目录 `.env`（本机开发用）相互独立。Compose 网络内的服务通过服务名互相访问：

- `POSTGRES_HOST=postgres`、`POSTGRES_PORT=5432`
- `MINIO_ENDPOINT=minio:9000`

`API_WORKERS` 控制同一 API 容器内的 Uvicorn worker 数量。当前 4 核服务器默认使用 `4`；每个 worker 都有独立的应用内缓存、限流计数和数据库连接池。现有连接池单 worker 最多使用 15 个连接，因此 4 个 worker 理论上最多占用 60 个 PostgreSQL 连接，调整 worker 数量时必须为迁移、管理任务和健康检查保留连接余量。

## 3. 生成安全 Secret

生产环境必须替换以下占位值，建议使用随机数生成：

```bash
# JWT 签名密钥（用于替换 JWT_SECRET）
openssl rand -base64 48

# PostgreSQL / MinIO 凭据（用于替换 POSTGRES_PASSWORD、MINIO_ACCESS_KEY、MINIO_SECRET_KEY）
openssl rand -hex 24
```

`WECHAT_APP_ID` 与 `WECHAT_APP_SECRET` 填写微信小程序后台的真实值。

需要微信订阅消息时设置 `WECHAT_SUBSCRIBE_ENABLED=true`，并分别填写通知、公告模板的 ID 与标题、内容、时间字段 key。模板字段必须与微信公众平台选定模板一致；未启用时这些字段保持空值，站内消息仍正常工作。

注意事项：

- 将 `APP_ENV` 改为 `production` 后，应用会强制校验：`JWT_SECRET` 必须非默认值、`WECHAT_APP_ID` / `WECHAT_APP_SECRET` 必须填写、`DEV_AUTH_ENABLED` 必须为 `false`。
- 密码或 Secret 中含 `$` 时，需要按 Docker Compose 的 `.env` 插值规则转义。更稳妥的方式是重新生成不含 `$` 的随机值，不要通过 `source deploy/.env` 加载配置。
- 服务器上建议对 `deploy/.env` 执行 `chmod 600 deploy/.env`。
- `MINIO_PUBLIC_URL` 是客户端最终访问图片的地址。启用本仓库 Caddy 时使用 `https://你的域名/media`。
- 升级中间件镜像（PostgreSQL/MinIO）必须显式修改 `deploy/.env` 中的版本 tag 并重新验证，不要退回 `latest`。

## 4. 校验配置

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env.example config
```

该命令只解析并渲染最终编排配置，不会启动任何服务。看到完整渲染结果（服务、卷、网络、环境变量）即表示语法正确。本机无 Docker daemon 时此命令仍可运行。

生产环境启动前可在 API 镜像中执行配置预检；命令只输出通过/失败，不会输出 Secret：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm --no-deps db-init python /app/scripts/validate_production_config.py
```

`COMPOSE_PROJECT_NAME` 必须由当前进程或 `deploy/.env` 显式提供；缺失时 `compose.yml` 和部署脚本都会 fail closed。部署脚本通过 `--project-name` 显式传入最终值，确保无论从哪个目录执行，始终操作指定的一组容器、volume 与网络。变更 project 名称相当于切换到另一套 Compose 资源，生产环境不要随意修改。

启用 Caddy 时同时校验生产叠加层：

```bash
docker compose -f deploy/compose.yml -f deploy/compose.production.yml \
  --env-file deploy/.env config --quiet
```

## 5. 构建镜像

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env build
```

会构建 `api` 镜像（`backend/Dockerfile`，Python 3.12-slim，仅安装运行时依赖）。`db-init` 与 `api` 使用同一个镜像。

## 6. 启动服务

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env up -d
```

启动顺序由依赖关系保证：

1. `postgres` 先启动并通过健康检查（首次启动时自动执行数据库 baseline，见第 10、12 节）；
2. `db-init` 一次性服务完成数据库版本标记/迁移（成功退出码 0）；
3. `minio` 启动后由 `minio-init` 幂等创建存储桶；
4. `api` 在数据库就绪、初始化完成后启动；
5. `admin-web` 在 API 健康后启动；
6. `ENABLE_CADDY=1` 时，Caddy 最后启动并提供公网 HTTPS。

### 6.1 正式域名与自动 HTTPS

在 `deploy/.env` 中设置：

```dotenv
ENABLE_CADDY=1
APP_DOMAIN=eat.example.com
MINIO_PUBLIC_URL=https://eat.example.com/media
CORS_ORIGINS=https://eat.example.com
```

随后使用 `deploy.sh`，脚本会自动叠加 `deploy/compose.production.yml`。Caddy 使用 `deploy/Caddyfile` 将 `/admin/` 转发到管理站、`/api/` 和 `/health/` 转发到 API、`/media/` 转发到公开 MinIO bucket，并持久化证书数据。

启用前必须满足：域名 A/AAAA 记录指向服务器；TCP 80、TCP/UDP 443 可访问；同一宿主机没有其他进程占用这些端口。不要同时启动另一套占用 80/443 的 Caddy 或 Nginx。

## 7. 查看状态

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env ps
```

`db-init` 与 `minio-init` 显示为 `Exited (0)` 属于正常状态——它们是初始化一次性任务，成功退出即完成任务。

## 8. 查看日志

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env logs -f api
docker compose -f deploy/compose.yml --env-file deploy/.env logs db-init
```

## 9. 就绪检查

API 提供两个健康检查端点：

- `GET /health/live`：进程存活。
- `GET /health/ready`：依赖就绪，同时检查 PostgreSQL 与 MinIO 存储桶。

Compose 中 `api` 服务配置了健康检查，容器内使用 Python 标准库请求 `GET /health/ready`（`API_CONTAINER_PORT` 指定的容器端口），不额外安装 curl。

```bash
curl -s http://127.0.0.1:8000/health/ready
```

正常响应：

```json
{"data":{"status":"ready","postgres":"ok","minio":"ok"}}
```

## 10. Alembic 迁移与数据库初始化策略

当前项目采用 **baseline SQL + Alembic** 的组合，由 `db-init` 服务（`backend/scripts/alembic_stamp_if_fresh.py`）统一处理，两条路径的分工如下：

**全新数据库（Compose 默认路径）**

- `backend/database/001_schema.sql` 是对应 `0006_admin_governance` 的全量 baseline（含 `admin_users` 等全部表）；`002_seed.sql` 初始化跨学校复用的基础分类。当前 `0007_draw_performance_indexes` 由后续 Alembic 增量迁移创建抽取热路径索引。
- PostgreSQL 官方镜像会在数据卷第一次初始化时自动执行挂载到 `docker-entrypoint-initdb.d/` 的这两个 SQL 文件。
- `db-init` 检测到没有 `alembic_version` 表时，先校验 baseline 的关键 schema 特征（`admin_users`、`school_areas`、`check_ins` 表存在，`stores.store_code` / `stores.area_id` 存在，`stores.slug` / `stores.area` 不存在，`idx_media_objects_owner_purpose` 索引存在）。校验失败则 fail closed：返回非 0 且不执行任何 stamp/upgrade。
- 校验通过后，`db-init` 执行 `alembic stamp 0006_admin_governance`，然后继续 `alembic upgrade head`。

**baseline revision 设计**

`001_schema.sql` 对应的明确 Alembic revision 是 `0006_admin_governance`（脚本中以 `BASELINE_REVISION = "0006_admin_governance"` 命名）。不用「把版本动态标记为最新」的方式初始化全新库；`db-init` 在 stamp 后继续执行 `0007_draw_performance_indexes` 及后续迁移。未来同步 baseline 时，必须同时更新 SQL、固定 revision 和校验脚本。

**已有数据库（旧版 Alembic 链升级）**

- 如果数据库已有 `alembic_version` 表，`db-init` 直接执行 `alembic upgrade head`（幂等，无新迁移时为空操作）。
- 旧版迁移链（`0001` ~ `0005`）只适用于旧版 schema（如 `stores.slug`、无 `school_areas` 的库）；它不能直接跑在 baseline 新库上，二者互斥。

手动执行迁移（例如临时检查版本）：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm db-init alembic -c /app/alembic.ini current
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm db-init alembic -c /app/alembic.ini upgrade head
```

在 `db-init` 完成 stamp 之前，不要在全新 baseline 库上手工执行 `alembic upgrade head`（会与 baseline 冲突而失败）；stamp 之后 `upgrade head` 会安全执行 `0007` 及后续增量迁移。

## 11. MinIO 初始化

- `minio-init` 使用 `minio/mc` 客户端创建配置的存储桶，`mc mb --ignore-existing` 保证幂等；bucket 已存在时同样正常退出。
- 创建后执行 `mc anonymous set download` 幂等配置 bucket 访问策略。
- `minio-init` 成功退出（`Exited (0)`）是正常状态，不是故障。
- MinIO Console（`9001`）默认不暴露端口。需要本地管理时，取消 `deploy/compose.yml` 中 `minio` 服务的注释端口块并重启，或在容器网络内执行 mc 命令：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm minio-init sh -c 'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && mc ls local/'
```

**bucket 访问策略**

- `MINIO_BUCKET` 为店铺公开素材 bucket，允许匿名读取但不允许匿名写入。
- `MINIO_PRIVATE_BUCKET` 为用户打卡照片、头像等敏感媒体 bucket，禁止匿名读取和写入。
- 私有媒体只能通过带用户鉴权的 API 读取；后续如改用 presigned URL，必须保持短时有效期和权限校验。

已有部署在切换到私有媒体前，先使用 API 镜像执行一次迁移检查；确认备份完成后再加 `--apply`：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm --no-deps db-init python /app/scripts/migrate_private_media.py
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm --no-deps db-init python /app/scripts/migrate_private_media.py --apply
```

## 12. PostgreSQL 数据卷语义

- `postgres` 使用命名卷 `postgres_data`，`minio` 使用命名卷 `minio_data`，数据保存在 Docker 卷中，不随容器删除而丢失。
- `docker-entrypoint-initdb.d/` 中的 SQL 只在数据卷**第一次初始化（空目录）**时执行。之后修改 `001_schema.sql` / `002_seed.sql` 不会在已有卷上重放。
- 因此，对已有部署的 schema 变更必须走 Alembic 增量迁移（见第 10 节），不要依赖修改 baseline。

## 13. 首次部署与日常升级

**首次部署**需要人工复制并填写生产配置：

```bash
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
chmod +x deploy/scripts/deploy.sh
# 编辑 deploy/.env，替换全部生产 Secret 和环境配置
# 必须把 COMPOSE_PROJECT_NAME 改为当前部署环境的唯一名称
./deploy/scripts/deploy.sh
```

**日常升级**直接执行：

```bash
./deploy/scripts/deploy.sh
```

脚本根据自身位置解析仓库根目录，不依赖当前工作目录。默认只允许部署 `main`；服务器使用其他明确分支时，必须显式指定，例如：

```bash
DEPLOY_BRANCH=release ./deploy/scripts/deploy.sh
```

脚本执行流程：

1. 检查 `deploy/.env`、显式 `COMPOSE_PROJECT_NAME`、文件权限、`git`、`docker`、`docker compose`、`curl`、`timeout` 与 Docker daemon；
2. 拒绝 dirty worktree、detached HEAD、当前分支与 `DEPLOY_BRANCH` 不一致等不安全状态；
3. 在更新代码前执行第一次 `docker compose config --quiet`，无效配置立即停止；
4. 执行 `git fetch --prune origin`，确认远端分支存在，再通过 `git merge --ff-only` 更新，并要求最终 `HEAD` 与远端提交完全一致；分叉或本地领先都会停止，绝不 force/reset；
5. 更新后再次执行 `docker compose config --quiet`，构建 `api` 与 `admin-web` 镜像（`db-init` 共用 API 镜像），正常利用 Docker layer cache；
6. 只启动或更新 `postgres`、`minio`，等待 `postgres` healthy、`minio` running，不触碰当前 `api`；
7. 通过 `docker compose run --rm --no-deps minio-init` 显式执行本次 MinIO 初始化，命令在 120 秒内退出码为 0 才继续；
8. 通过 `docker compose run --rm --no-deps db-init` 显式执行本次数据库迁移，复用 `backend/scripts/alembic_stamp_if_fresh.py`；命令在 120 秒内退出码为 0 才继续；
9. migration 成功后才更新 `api`，等待 API healthy 后再更新 `admin-web`，并等待管理站 healthy；
10. `ENABLE_CADDY=1` 时更新 Caddy，并要求配置校验健康检查通过；
11. 通过 `docker compose port api ${API_CONTAINER_PORT}` 获取实际宿主机发布地址，请求 `/health/ready`，确认 HTTP 200 且 `status=ready` 后才报告成功。

`minio-init` 和 `db-init` 使用 `run --rm`，命令成功退出就是本次部署的 one-shot PASS，不依赖历史 `Exited (0)` 容器。若 `db-init` 失败，脚本立即返回非 0，不会更新或主动停止已有 `api`，也不会自动回滚数据库、停止基础服务或重置 Git。

默认健康等待超时为 120 秒，readiness 等待超时为 30 秒；必要时可显式调整：

```bash
HEALTH_TIMEOUT=180 READINESS_TIMEOUT=60 ./deploy/scripts/deploy.sh
```

正常构建使用 Docker layer cache。仅在人工确认确有需要时禁用缓存：

```bash
NO_CACHE=1 ./deploy/scripts/deploy.sh
```

部署前可执行 dry-run。它会完成依赖、环境文件、Git 状态和 Compose 配置检查，但不会 fetch/merge、build、up 或触发 migration：

```bash
DRY_RUN=1 ./deploy/scripts/deploy.sh
```

脚本明确不会：

- 创建或输出 Secret；
- 删除 volume 或把 `down` 作为升级步骤；
- 自动回滚数据库；
- 自动 checkout、stash、force reset 或清理 Git 工作区；
- 在失败后自动恢复旧提交或停止现有服务。

迁移可能已经在失败前完成，因此脚本失败时保留现场，输出 `compose ps -a` 和日志命令，由运维人员判断后续操作。

## 14. 正常停止服务

```bash
# 停止所有容器（保留数据卷与容器状态）
docker compose -f deploy/compose.yml --env-file deploy/.env stop

# 再次启动
docker compose -f deploy/compose.yml --env-file deploy/.env start

# 移除容器（保留数据卷；之后 up -d 会重新创建容器）
docker compose -f deploy/compose.yml --env-file deploy/.env down
```

## 15. 禁止随意 down -v

`docker compose down -v` 会**删除 PostgreSQL 与 MinIO 的命名数据卷**，属于不可恢复操作，严禁加入普通部署/更新流程。只有确认要彻底销毁本地测试数据（且已经做好备份）时才允许执行。

## 16. 部署失败诊断

部署脚本会在构建或启动后的失败路径输出当前服务状态。也可以人工执行：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env ps -a
docker compose -f deploy/compose.yml --env-file deploy/.env logs api --tail=200
docker compose -f deploy/compose.yml --env-file deploy/.env logs postgres --tail=200
docker compose -f deploy/compose.yml --env-file deploy/.env logs minio --tail=200
```

`minio-init`、`db-init` 由部署脚本使用 `run --rm` 执行，不保留 one-shot 容器；其本次输出直接保留在部署终端中。

检查 Git 状态和当前版本：

```bash
git status --short --branch
git log -1 --oneline
```

## 17. 备份与恢复

备份脚本会导出 PostgreSQL custom dump，并将公开、私有 MinIO bucket 镜像到带 UTC 时间戳的目录；不会输出密码：

```bash
./deploy/scripts/backup.sh /srv/eatanything/backups
```

恢复 PostgreSQL 前必须先确认目标环境，并设置明确的保护变量：

```bash
CONFIRM_RESTORE=YES ./deploy/scripts/restore-postgres.sh /srv/eatanything/backups/20260825T000000Z/postgres.dump
```

恢复后必须检查 `/health/ready`、店铺列表、登录、图片读取和用户数据。MinIO 文件恢复应在维护窗口内使用 `mc mirror --overwrite` 将对应备份目录恢复到目标 bucket。备份目录应限制为运维账号可读，并按组织策略异地保存、定期清理和演练恢复。

## 18. 监控与质量门禁

- `/health/live` 只检查进程存活，`/health/ready` 检查 PostgreSQL 和公开/私有 MinIO bucket。
- `/health/metrics` 在 `METRICS_ENABLED=true` 时提供 Prometheus 文本指标；生产环境必须配置 `METRICS_TOKEN` 并通过 `X-Metrics-Token` 访问。
- 指标只包含受控路径、方法和状态码，不包含用户 ID、Token 或请求正文。
- 登录、随机抽取、上传和写操作使用应用层限流；当前 Compose 使用进程内窗口计数，每个 Uvicorn worker 都独立计数，因此配置多个 worker 后限额不是全局总额。若需要跨 worker 或跨副本的全局限流，必须迁移到 Redis 等共享限流存储。
- `.github/workflows/ci.yml` 会执行后端测试、前端类型检查和生产构建、Compose 校验及敏感文件检查。
- 建议监控 ready 失败、5xx 比例、请求延迟、磁盘空间、备份任务失败和容器重启次数。

## 19. 前端发布检查

```bash
cd frontend
npm ci
npm run type-check
npm run build:mp-weixin
npm run build:h5
npm run verify:production
```

将 `dist/build/mp-weixin` 导入微信开发者工具，完成登录、店铺浏览、随机抽取、收藏、打卡、评价、历史和管理端 H5 冒烟测试后，再由账号所有者执行体验版和正式版发布。正式 API 和图片域名、HTTPS/TLS 及微信合法域名登记需要在外部平台完成。

正式域名部署后执行公网冒烟测试：

```bash
./deploy/scripts/smoke-test.sh https://你的域名
```

脚本检查进程存活、PostgreSQL/MinIO 就绪、管理后台访问和基础安全响应头。更完整的人工验收见 [生产发布检查清单](../docs/release-checklist.md)。

## 服务清单

| 服务 | 镜像 | 用途 |
| --- | --- | --- |
| `postgres` | `postgres:16-alpine` | PostgreSQL 数据库，执行 baseline 初始化 |
| `db-init` | 与 `api` 同镜像 | 一次性：数据库版本 stamp/upgrade |
| `minio` | `minio/minio` | 对象存储服务 |
| `notification-worker` | 与 `api` 相同 | 展开 PostgreSQL 发送队列、发送微信订阅消息并重试 |
| `weather-worker` | 与 `api` 相同 | 每天 06:00 按学校坐标更新当天及次日天气缓存，缺失时每 30 分钟补抓 |
| `minio-init` | `minio/mc` | 一次性：幂等创建存储桶 |
| `api` | 本项目构建 | FastAPI（uvicorn `app.main:app`） |
| `admin-web` | 本项目构建 | 独立 Vue 3 管理站及 `/api/` 反向代理 |
| `caddy` | `caddy:2.10.2-alpine` | 可选：正式域名、自动 HTTPS 与公网反向代理 |

## 目录结构

```text
backend/
├── Dockerfile          # API 生产镜像
├── .dockerignore       # 排除测试/缓存/密钥等
├── app/                # 应用代码
├── alembic/            # Alembic 迁移
├── alembic.ini
├── database/           # baseline SQL 与种子数据
└── scripts/            # 运维辅助脚本
deploy/
├── compose.yml         # 编排定义
├── compose.production.yml # 可选 Caddy 生产叠加层
├── Caddyfile           # 正式域名路由与安全响应头
├── .env.example        # 环境变量模板（提交 Git）
├── .env                # 真实配置（不提交 Git）
├── scripts/
│   ├── deploy.sh       # 安全的一键部署/升级脚本
│   ├── backup.sh       # PostgreSQL 与 MinIO 备份
│   ├── restore-postgres.sh # 受保护的 PostgreSQL 恢复
│   └── smoke-test.sh   # 正式域名公网冒烟测试
└── README.md           # 本文档
```
