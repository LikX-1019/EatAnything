# EatAnything 后端部署说明

本文档描述后端在服务器上的 Docker Compose 部署方式，覆盖服务编排、环境变量、数据库初始化与日常运维命令。所有命令默认在仓库根目录执行。

> 本阶段只标准化后端部署方式，不包含 HTTPS、CI/CD、监控、备份与前端发布；这些属于后续阶段，部署时请不要假定它们已经存在。

## 1. 环境要求

- Linux 服务器（或本机 Docker Desktop），已安装 Docker Engine 24+ 与 Docker Compose v2（v2.17+，`docker compose` 子命令）。
- 可访问外网以下载镜像：`python:3.12-slim`、`postgres:16-alpine`、`minio/minio:RELEASE.2025-04-22T22-12-26Z`、`minio/mc:RELEASE.2025-04-16T18-13-26Z`（镜像标签可通过 `deploy/.env` 覆盖）。
- 默认占用宿主机端口：
  - `8000`：API（默认只绑定 `127.0.0.1`，通过 `API_BIND_HOST` / `API_PORT` 调整）
  - `9000`：MinIO API（默认只绑定 `127.0.0.1`，通过 `MINIO_BIND_HOST` / `MINIO_PORT` 调整）
- PostgreSQL 与 MinIO Console 默认不暴露到宿主机公网。

## 2. 复制环境变量文件

```bash
cp deploy/.env.example deploy/.env
```

然后编辑 `deploy/.env` 填写真实值。`deploy/.env` 已被 `.gitignore` 忽略，不会进入 Git；`deploy/.env.example` 会进入 Git，只允许包含变量名和安全占位符。

本文件与仓库根目录 `.env`（本机开发用）相互独立。Compose 网络内的服务通过服务名互相访问：

- `POSTGRES_HOST=postgres`、`POSTGRES_PORT=5432`
- `MINIO_ENDPOINT=minio:9000`

## 3. 生成安全 Secret

生产环境必须替换以下占位值，建议使用随机数生成：

```bash
# JWT 签名密钥（用于替换 JWT_SECRET）
openssl rand -base64 48

# PostgreSQL / MinIO 凭据（用于替换 POSTGRES_PASSWORD、MINIO_ACCESS_KEY、MINIO_SECRET_KEY）
openssl rand -hex 24
```

`WECHAT_APP_ID` 与 `WECHAT_APP_SECRET` 填写微信小程序后台的真实值。

注意事项：

- 将 `APP_ENV` 改为 `production` 后，应用会强制校验：`JWT_SECRET` 必须非默认值、`WECHAT_APP_ID` / `WECHAT_APP_SECRET` 必须填写、`DEV_AUTH_ENABLED` 必须为 `false`。
- 密码或 Secret 中含 `$` 时，在 `.env` 中写成 `$$`，避免 Docker Compose 插值把它当作变量。
- 服务器上建议对 `deploy/.env` 执行 `chmod 600 deploy/.env`。
- `MINIO_PUBLIC_URL` 是客户端最终访问图片的地址。当前阶段为占位值；配置 HTTPS/域名后改为正式地址（属于后续阶段）。
- 升级中间件镜像（PostgreSQL/MinIO）必须显式修改 `deploy/.env` 中的版本 tag 并重新验证，不要退回 `latest`。

## 4. 校验配置

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env.example config
```

该命令只解析并渲染最终编排配置，不会启动任何服务。看到完整渲染结果（服务、卷、网络、环境变量）即表示语法正确。本机无 Docker daemon 时此命令仍可运行。

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
4. `api` 在数据库就绪、初始化完成后启动。

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

- `backend/database/001_schema.sql` 是完整的全量 baseline，当前等于 Alembic head 状态（含 `admin_users` 等全部表）；`002_seed.sql` 初始化跨学校复用的基础分类。
- PostgreSQL 官方镜像会在数据卷第一次初始化时自动执行挂载到 `docker-entrypoint-initdb.d/` 的这两个 SQL 文件。
- `db-init` 检测到没有 `alembic_version` 表时，先校验 baseline 的关键 schema 特征（`admin_users`、`school_areas`、`check_ins` 表存在，`stores.store_code` / `stores.area_id` 存在，`stores.slug` / `stores.area` 不存在，`idx_media_objects_owner_purpose` 索引存在）。校验失败则 fail closed：返回非 0 且不执行任何 stamp/upgrade。
- 校验通过后，`db-init` 执行 `alembic stamp 0005_store_catalog`，然后继续 `alembic upgrade head`。

**baseline revision 设计**

`001_schema.sql` 对应的明确 Alembic revision 是 `0005_store_catalog`（脚本中以 `BASELINE_REVISION = "0005_store_catalog"` 命名）。不用「把版本动态标记为最新」的方式初始化全新库：如果未来新增 `0006`/`0007` 迁移而 baseline 仍停留在 0005，动态标记会把全新库错误置为最新、跳过后续迁移。固定 stamp 到 `0005_store_catalog` 后，未来 `0006` 会在全新库上被 `alembic upgrade head` 真正执行。

**已有数据库（旧版 Alembic 链升级）**

- 如果数据库已有 `alembic_version` 表，`db-init` 直接执行 `alembic upgrade head`（幂等，无新迁移时为空操作）。
- 旧版迁移链（`0001` ~ `0005`）只适用于旧版 schema（如 `stores.slug`、无 `school_areas` 的库）；它不能直接跑在 baseline 新库上，二者互斥。

手动执行迁移（例如临时检查版本）：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm db-init alembic -c /app/alembic.ini current
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm db-init alembic -c /app/alembic.ini upgrade head
```

在 `db-init` 完成 stamp 之前，不要在全新 baseline 库上手工执行 `alembic upgrade head`（会与 baseline 冲突而失败）；stamp 之后 `upgrade head` 即为安全的增量空操作。

## 11. MinIO 初始化

- `minio-init` 使用 `minio/mc` 客户端创建配置的存储桶，`mc mb --ignore-existing` 保证幂等；bucket 已存在时同样正常退出。
- 创建后执行 `mc anonymous set download` 幂等配置 bucket 访问策略。
- `minio-init` 成功退出（`Exited (0)`）是正常状态，不是故障。
- MinIO Console（`9001`）默认不暴露端口。需要本地管理时，取消 `deploy/compose.yml` 中 `minio` 服务的注释端口块并重启，或在容器网络内执行 mc 命令：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm minio-init sh -c 'mc alias set local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" && mc ls local/'
```

**bucket 访问策略（本阶段）**

- 当前 bucket 为**公开读取**（download 策略），保持现有「前端直接访问图片 URL」的架构。
- bucket **不允许匿名写入**：只有具备 `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` 的 API 服务可以上传。
- 用户敏感媒体（如打卡照片、头像）未来应拆分为 private bucket 或改用 presigned URL，本阶段**不重构媒体架构**。

## 12. PostgreSQL 数据卷语义

- `postgres` 使用命名卷 `postgres_data`，`minio` 使用命名卷 `minio_data`，数据保存在 Docker 卷中，不随容器删除而丢失。
- `docker-entrypoint-initdb.d/` 中的 SQL 只在数据卷**第一次初始化（空目录）**时执行。之后修改 `001_schema.sql` / `002_seed.sql` 不会在已有卷上重放。
- 因此，对已有部署的 schema 变更必须走 Alembic 增量迁移（见第 10 节），不要依赖修改 baseline。

## 13. 更新部署流程

```bash
git pull
docker compose -f deploy/compose.yml --env-file deploy/.env build
docker compose -f deploy/compose.yml --env-file deploy/.env up -d
```

`db-init` 会在每次启动时自动把数据库升级到迁移链最新 head，因此升级顺序为“先更新代码镜像，再重启服务”。升级前建议先备份数据库（备份能力属于后续阶段，当前请自行确认）。

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

## 服务清单

| 服务 | 镜像 | 用途 |
| --- | --- | --- |
| `postgres` | `postgres:16-alpine` | PostgreSQL 数据库，执行 baseline 初始化 |
| `db-init` | 与 `api` 同镜像 | 一次性：数据库版本 stamp/upgrade |
| `minio` | `minio/minio` | 对象存储服务 |
| `minio-init` | `minio/mc` | 一次性：幂等创建存储桶 |
| `api` | 本项目构建 | FastAPI（uvicorn `app.main:app`） |

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
├── .env.example        # 环境变量模板（提交 Git）
├── .env                # 真实配置（不提交 Git）
└── README.md           # 本文档
```
