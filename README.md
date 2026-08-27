# 今天吃什么（EatAnything）

面向校园餐饮场景的微信小程序与管理平台。用户可以按学校浏览店铺、随机选店、收藏、打卡和评价；平台管理员可管理全部学校，学校管理员只能处理被授权学校内的店铺、用户与内容。

## 项目组成

| 目录 | 技术栈 | 用途 |
| --- | --- | --- |
| `frontend/` | uni-app、Vue 3、Pinia | 微信小程序与 H5 用户端 |
| `admin-web/` | Vue 3、Vite、TypeScript、Element Plus | 独立桌面 Web 管理后台 |
| `backend/` | FastAPI、SQLAlchemy、Alembic | API、鉴权、学校数据隔离与内容治理 |
| `deploy/` | Docker Compose、Caddy | PostgreSQL、MinIO、API、管理后台与 HTTPS 编排 |
| `docs/` | Markdown、OpenAPI | 配置、使用、发布和接口说明 |

生产数据保存在 PostgreSQL 与 MinIO 命名卷中。用户打卡照片等媒体进入私有 bucket，只能通过鉴权接口读取；店铺公开图片位于只读公开 bucket。

## 权限模型

- `platform_admin`：查看并管理全部学校，可创建管理员和分配学校权限。
- `school_admin`：只能查看和操作 `admin_user_schools` 中绑定的学校。
- 用户、店铺、评论、打卡照片和审计日志均按学校过滤。
- 评论和打卡照片采用可恢复的软隐藏；用户可分别被禁止评论或禁止上传图片。
- 管理操作记录操作者、学校、目标、原因、IP 和时间，不允许由后台修改或删除。

## 本地开发

环境要求：Python 3.12、Node.js 22、npm、PostgreSQL 16 和 MinIO。密钥只写入被 Git 忽略的根目录 `.env`。

```powershell
Copy-Item .env.example .env
$env:PYTHONPATH=(Resolve-Path 'backend').Path
python -m pip install -e "backend[dev]"
alembic -c backend\alembic.ini upgrade head
python backend\scripts\create_admin.py admin --role platform_admin --display-name "本地管理员"
backend\scripts\run_local.ps1 -Reload
```

另开终端启动管理后台：

```powershell
Set-Location admin-web
Copy-Item .env.example .env.development
npm ci
npm run dev
```

管理后台默认访问 `http://127.0.0.1:5174/admin/`，API 文档默认访问 `http://127.0.0.1:8000/docs`。小程序启动方式见 [frontend/README.md](frontend/README.md)。

## 质量检查

提交代码前至少执行：

```powershell
$env:PYTHONPATH=(Resolve-Path 'backend').Path
python -m compileall -q backend\app
ruff check backend\app backend\tests
pytest backend\tests -q

Set-Location admin-web
npm ci
npm run build

Set-Location ..\frontend
npm ci
npm run type-check
npm test
npm run build:mp-weixin
npm run build:h5
npm run verify:production
```

GitHub Actions 会重复执行后端测试、两个前端的类型检查与生产构建、Docker 镜像构建、Compose 解析、Shell 语法和敏感文件检查。

## 生产部署

生产环境统一使用 `deploy/.env`，不要复用本机开发 `.env`：

```bash
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
# 填写真实 Secret、微信配置、域名和唯一的 Compose 资源名称
DRY_RUN=1 ./deploy/scripts/deploy.sh
./deploy/scripts/deploy.sh
./deploy/scripts/smoke-test.sh https://你的域名
```

如由本项目管理域名和 HTTPS，在 `deploy/.env` 设置 `ENABLE_CADDY=1` 与 `APP_DOMAIN`。Caddy 会自动申请证书，并将 `/admin/`、`/api/`、`/health/` 和 `/media/` 路由到对应容器。服务器必须先完成 DNS 解析并开放 TCP 80、TCP/UDP 443。

首次正式发布前必须完成备份、配置预检、数据库迁移、就绪检查和业务冒烟测试。完整步骤见 [部署说明](deploy/README.md) 与 [发布检查清单](docs/release-checklist.md)。

## 文档导航

- [环境变量与配置说明](docs/configuration.md)
- [Web 管理后台使用手册](docs/admin-guide.md)
- [生产发布检查清单](docs/release-checklist.md)
- [后端本地开发说明](backend/README.md)
- [Web 管理后台开发说明](admin-web/README.md)
- [小程序开发说明](frontend/README.md)
- [店铺批量导入规范](docs/store-import-spec.md)
- [API 契约](docs/openapi-v1.yaml)
- [安全策略](SECURITY.md)
- [变更记录](CHANGELOG.md)

## 配置与安全原则

- `.env`、密码、Token、数据库备份和私有媒体不得提交到 Git、工单或聊天记录。
- `VITE_*` 会进入客户端产物，只能保存公开地址和公开功能开关。
- 生产环境必须设置 `APP_ENV=production`、关闭 `DEV_AUTH_ENABLED`，并使用随机 Secret。
- PostgreSQL、MinIO API 和管理后台容器默认仅绑定 `127.0.0.1`；公网入口只开放 Caddy。
- 普通升级禁止执行 `docker compose down -v`，它会删除数据库和媒体数据卷。
