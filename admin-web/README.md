# 校园吃什么 Web 管理后台

这是独立于 uni-app 小程序的桌面浏览器管理站，使用 Vue 3、Vite、TypeScript、Pinia 和 Element Plus。页面采用与小程序一致的日系手账贴纸风，并通过 FastAPI 的 `/api/v1/admin/*` 接口管理学校、店铺、用户、评论、打卡照片、管理员和审计日志。

## 本地运行

```powershell
cd admin-web
Copy-Item .env.example .env.development
npm install
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

先执行数据库迁移，再使用后端脚本创建管理员。现有 `store_admin` 兼容为平台管理员；新建管理员时建议显式选择 `platform_admin` 或 `school_admin`。

```powershell
$env:PYTHONPATH=(Resolve-Path '..\backend').Path
alembic -c ..\backend\alembic.ini upgrade head
python ..\backend\scripts\create_admin.py admin --display-name "平台管理员"
```

生产环境不得在前端环境变量中保存密码、JWT Secret、数据库密码或 MinIO Secret。
