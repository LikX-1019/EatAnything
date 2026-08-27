# 校园吃什么 Web 管理后台

这是独立于 uni-app 小程序的桌面浏览器管理站，使用 Vue 3、Vite、TypeScript、Pinia 和 Element Plus。页面采用与小程序一致的日系手账贴纸风，并通过 FastAPI 的 `/api/v1/admin/*` 接口管理学校、店铺、用户、评论、打卡照片、管理员和审计日志。

## 本地运行

```powershell
cd admin-web
Copy-Item .env.example .env.development
npm ci
npm run dev
```

默认访问 `http://127.0.0.1:5174/admin/`。开发代理通过 `VITE_API_PROXY_TARGET` 转发 `/api` 请求，后端默认地址为 `http://127.0.0.1:8000`。

## 生产构建

```powershell
npm ci
npm run build
```

构建结果位于 `admin-web/dist/`，所有资源路径以 `/admin/` 为前缀。部署时必须将 `/admin/` 的 SPA 路由回退到 `admin/index.html`，并把 `/api/` 反向代理到 FastAPI。

## 首次使用

先执行数据库迁移，再使用后端脚本创建管理员。现有 `store_admin` 仅用于兼容旧数据；新账号必须使用 `platform_admin` 或 `school_admin`。

```powershell
$env:PYTHONPATH=(Resolve-Path '..\backend').Path
alembic -c ..\backend\alembic.ini upgrade head
python ..\backend\scripts\create_admin.py admin --role platform_admin --display-name "平台管理员"
```

生产环境不得在前端环境变量中保存密码、JWT Secret、数据库密码或 MinIO Secret。

## 权限与功能

- `platform_admin` 可管理所有学校及管理员账号。
- `school_admin` 只能访问后端授权的学校，前端筛选器不能绕过接口权限。
- 用户、店铺、评论和打卡照片均按学校筛选；用户档案可查看该用户的账号、评论与打卡并直接治理。
- 店铺批量导入先选择学校，模板使用中文标题，只接受图片 URL，不接受嵌入图片。

完整操作说明见 [Web 管理后台使用手册](../docs/admin-guide.md)。

## 发布验证

```powershell
npm ci
npm run type-check
npm run build
docker build -t eat-anything-admin-web:local .
```

生产镜像已配置 SPA 回退、gzip、上传大小限制和常用安全响应头。正式域名反向代理见 [部署说明](../deploy/README.md)。
