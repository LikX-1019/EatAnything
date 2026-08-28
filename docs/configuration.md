# 环境变量与配置说明

项目有三类配置文件，作用域不能混用。

| 文件 | 是否提交 | 用途 |
| --- | --- | --- |
| 根目录 `.env.example` | 是 | 后端本机开发模板 |
| 根目录 `.env` | 否 | 后端本机开发真实配置 |
| `deploy/.env.example` | 是 | Docker 生产部署模板 |
| `deploy/.env` | 否 | 服务器真实配置与 Compose 资源名 |
| `frontend/.env.*` | 是，仅公开值 | 小程序/H5 API 地址与公开开关 |
| `admin-web/.env.example` | 是，仅公开值 | 管理后台开发代理地址 |

`.env` 使用纯 `KEY=value` 格式。不要在其中执行命令，也不要把它当 Shell 脚本 `source`。生产服务器建议设置 `chmod 600 deploy/.env`。

## 后端运行配置

| 变量 | 说明 | 生产要求 |
| --- | --- | --- |
| `APP_ENV` | 运行环境 | 必须为 `production` |
| `APP_TIMEZONE` | 业务时区 | 默认 `Asia/Shanghai` |
| `JWT_SECRET` | JWT 签名密钥 | 随机值，至少 32 字符 |
| `JWT_EXPIRE_SECONDS` | 登录有效期秒数 | 必须为正整数 |
| `DEV_AUTH_ENABLED` | 开发登录开关 | 必须为 `false` |
| `WECHAT_APP_ID` | 微信小程序 AppID | 必填 |
| `WECHAT_APP_SECRET` | 微信小程序 AppSecret | 必填且只存服务器 |
| `WECHAT_SUBSCRIBE_ENABLED` | 是否启用微信订阅消息 Worker | 启用时两套模板配置必须完整 |
| `WECHAT_NOTIFICATION_*` | 通知模板 ID 及标题、内容、时间字段 key | 与微信公众平台模板严格一致 |
| `WECHAT_ANNOUNCEMENT_*` | 公告模板 ID 及标题、内容、时间字段 key | 与微信公众平台模板严格一致 |
| `POSTGRES_*` | PostgreSQL 连接信息 | 密码至少 16 字符 |
| `MINIO_*` | MinIO 连接、bucket 与公网地址 | 公开/私有 bucket 必须不同 |
| `MAX_UPLOAD_BYTES` | 单文件上传上限 | 默认 5 MiB |
| `CORS_ORIGINS` | 允许的浏览器来源，逗号分隔 | 只填正式 HTTPS 来源 |
| `METRICS_ENABLED` | Prometheus 指标开关 | 开启时必须配置 Token |
| `METRICS_TOKEN` | `/health/metrics` 访问 Token | 随机值，至少 16 字符 |
| `TRUSTED_PROXY_IPS` | 可被信任的反向代理 IP | 按实际网络填写，可留空 |
| `SEED_ADMIN_PASSWORD` | 示例数据脚本密码 | 生产环境建议留空 |

生成随机值示例：

```bash
openssl rand -base64 48
openssl rand -hex 24
```

配置 `APP_ENV=production` 后，后端会拒绝默认 Secret、占位域名、本地地址、开发登录；启用 `WECHAT_SUBSCRIBE_ENABLED` 时也会拒绝不完整的双模板配置。模板 ID 不是 Secret，但只在配置模板中保留空占位，真实 AppSecret、Token 和数据库密码不得提交。可在启动服务前执行不泄露 Secret 的预检：

```bash
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm --no-deps db-init \
  python /app/scripts/validate_production_config.py
```

## Compose 与域名配置

| 变量 | 说明 |
| --- | --- |
| `COMPOSE_PROJECT_NAME` | 环境唯一项目名，例如 `eatanything-prod` |
| `API_IMAGE` / `ADMIN_WEB_IMAGE` | 本次发布的镜像名和版本标签 |
| `POSTGRES_IMAGE` / `MINIO_IMAGE` / `MINIO_MC_IMAGE` | 固定版本的中间件镜像 |
| `*_BIND_HOST` / `*_PORT` | 宿主机绑定地址和端口 |
| `POSTGRES_VOLUME` / `MINIO_VOLUME` / `NETWORK_NAME` | 环境唯一资源名 |
| `ENABLE_CADDY` | `1` 时加载 HTTPS 生产叠加编排 |
| `APP_DOMAIN` | 不带协议和路径的正式域名 |
| `CADDY_IMAGE` | 固定版本的 Caddy 镜像 |
| `CADDY_DATA_VOLUME` / `CADDY_CONFIG_VOLUME` | Caddy 证书与配置数据卷 |

启用 Caddy 时，`MINIO_PUBLIC_URL` 应是 `https://你的域名/media`，`CORS_ORIGINS` 应包含 `https://你的域名`。DNS 必须先指向服务器，80/443 端口必须可从公网访问。

## 前端公开配置

`frontend` 和 `admin-web` 的 `VITE_*` 变量会被打包进 JavaScript，任何访问者都能看到。这里不得放 `WECHAT_APP_SECRET`、`JWT_SECRET`、数据库密码、MinIO Secret、管理员密码或 Metrics Token。

生产小程序的 `VITE_API_BASE_URL` 使用正式 HTTPS API 地址。开发登录只可在非生产后端使用，微信体验版和正式版不得依赖 `DEV_AUTH_ENABLED`。

## 提交前检查

```bash
git status --short
git ls-files | grep -E '(^|/)\.env$|\.pem$|\.key$' && exit 1 || true
```

如果 Secret 曾经进入 Git，即使随后删除也应视为已经泄露：立即轮换对应凭据，并检查 Git 历史与远端缓存。
