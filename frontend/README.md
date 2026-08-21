# 今天吃什么

基于 uni-app、Vue 3、Vite 和 Pinia 的微信小程序前端。用户、学校、店铺列表、搜索和随机抽取已接入 FastAPI 后端；评价、历史等后续模块暂时保留 Mock 数据。

## 运行

```bash
npm install
npm run dev:mp-weixin
```

开发构建通过 `http://121.43.97.186/api/v1` 访问测试服务器，生产构建仍保留 `https://eat.unilinkcore.cn/api/v1`。本地使用开发登录前，需要同时在后端开启 `DEV_AUTH_ENABLED=true`。环境配置集中在 `.env.development`、`.env.test` 和 `.env.production`；在微信开发者工具中使用公网 IP 调试时，需要在“本地设置”中开启“不校验合法域名、WebView（业务域名）、TLS 版本以及 HTTPS 证书”。

公网 IP 调试只用于开发版自测，不能用于体验版或正式版。完成域名接入备案后，应将开发环境切回 HTTPS 域名，并关闭“不校验合法域名”。

前端的 `VITE_*` 配置会进入客户端产物，只能存放 API 地址、功能开关等公开值，不能存放微信 App Secret、JWT Secret 或数据库密码。

编译结果位于 `dist/dev/mp-weixin`，可直接导入微信开发者工具。生产构建使用：

```bash
npm run build:mp-weixin
```

## 图片处理

店铺图片地址由后端 API 返回，实际文件保存在服务器 MinIO 中。前端不再包含餐品图片，缺图时使用极小的内联透明占位，避免静态图片进入小程序主包。

仅用于服务器初始化和灾备恢复的种子素材保存在 `backend/seed_assets`，不会进入前端构建产物；来源、许可证和 MinIO 对象键记录在 `backend/database/seed_assets.json` 中。
