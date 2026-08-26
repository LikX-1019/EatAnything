# 今天吃什么（EatAnything）

“今天吃什么”是一款围绕校园食堂与周边餐饮的微信小程序：用户可以浏览校园店铺、随机推荐、打卡、写评价和收藏。项目分为四个主要部分：

- `frontend/`：uni-app（Vue 3）小程序前端
- `admin-web/`：独立 Vue 3 桌面 Web 管理后台
- `backend/`：FastAPI 后端（PostgreSQL + MinIO）
- `deploy/`：后端 Docker Compose 部署定义

用户端核心闭环和独立 Web 管理后台已经接入后端。Web 管理后台覆盖学校、店铺、批量导入、用户限制、评论与打卡照片治理、管理员分权和审计日志。生产工程还需由部署人员填写真实 Secret，并在外部完成正式域名、HTTPS/TLS 和微信平台合法域名登记。

## 后端部署

生产/服务器部署方式见 [deploy/README.md](deploy/README.md)，包含环境变量、Docker 镜像构建、服务编排、数据库初始化与 Alembic 迁移说明。

本机开发运行后端见 [backend/README.md](backend/README.md)。
