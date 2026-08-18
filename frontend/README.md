# 今天吃什么

基于 uni-app、Vue 3、Vite 和 Pinia 的微信小程序前端演示。项目不使用后端、云函数、云数据库或本地持久化。

## 运行

```bash
npm install
npm run dev:mp-weixin
```

编译结果位于 `dist/dev/mp-weixin`，可直接导入微信开发者工具。生产构建使用：

```bash
npm run build:mp-weixin
```

## 图片来源

- 火锅图片：[Unsplash Images](https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43)
- 美食碗图片：[Unsplash Images](https://images.unsplash.com/photo-1569718212165-3a8278d5f624)

图片已下载至 `src/static/images/foods`，页面运行时不请求外部图片。
