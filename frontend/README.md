# 今天吃什么

基于 uni-app、Vue 3、Vite 和 Pinia 的微信小程序前端。用户、学校、店铺列表、搜索和随机抽取已接入 FastAPI 后端；评价、历史等后续模块暂时保留 Mock 数据。

## 运行

```bash
npm install
npm run dev:mp-weixin
```

开发环境默认请求 `http://127.0.0.1:8000/api/v1`。本地使用开发登录前，需要同时在后端开启 `DEV_AUTH_ENABLED=true`。环境配置集中在 `.env.development`、`.env.test` 和 `.env.production`；部署前必须将 `.env.production` 中的占位地址替换为已在微信公众平台登记的 HTTPS API 域名。

前端的 `VITE_*` 配置会进入客户端产物，只能存放 API 地址、功能开关等公开值，不能存放微信 App Secret、JWT Secret 或数据库密码。

编译结果位于 `dist/dev/mp-weixin`，可直接导入微信开发者工具。生产构建使用：

```bash
npm run build:mp-weixin
```

## 图片来源

- 火锅图片：[Unsplash Images](https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43)
- 美食碗图片：[Unsplash Images](https://images.unsplash.com/photo-1569718212165-3a8278d5f624)

图片已下载至 `src/static/images/foods`，页面运行时不请求外部图片。
