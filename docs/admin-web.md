# Web 管理后台功能与接口说明

## 1. 入口与权限

独立管理站位于 `admin-web/`，生产构建以 `/admin/` 为基础路径，不依赖 uni-app 或微信运行环境。管理接口统一使用 `/api/v1/admin/` 前缀和管理员 Bearer Token。

管理员角色：

- `platform_admin`：可以访问所有学校，并管理管理员账号。
- `school_admin`：只能访问 `admin_user_schools` 中绑定的学校。
- `store_admin`：为了兼容已有账号，暂按平台管理员处理。

学校范围由后端依赖和查询条件强制执行，前端菜单或学校选择器不作为权限边界。

## 2. 页面

| 页面 | 路径 | 主要能力 |
| --- | --- | --- |
| 登录 | `/admin/login` | 管理员账号密码登录 |
| 数据总览 | `/admin/dashboard` | 学校、店铺、用户、评论、打卡和隐藏内容统计 |
| 学校管理 | `/admin/schools` | 学校与区域新增、编辑、启停用 |
| 店铺管理 | `/admin/stores` | 店铺查询、新增、编辑、批量状态维护和图片上传 |
| 批量导入 | `/admin/imports` | CSV/XLSX 店铺原子导入与逐行错误反馈 |
| 用户管理 | `/admin/users` | 用户档案、账号状态、评论和图片上传限制 |
| 评论管理 | `/admin/reviews` | 评论查询、批量隐藏和恢复 |
| 打卡照片 | `/admin/check-ins` | 私有照片鉴权预览、批量隐藏和恢复 |
| 管理员管理 | `/admin/admins` | 角色、学校范围、状态和密码维护 |
| 审计日志 | `/admin/audit-logs` | 操作记录查询和当前页 CSV 导出 |

## 3. 新增接口

```text
GET    /api/v1/admin/me
GET    /api/v1/admin/dashboard/summary
GET    /api/v1/admin/schools
POST   /api/v1/admin/schools
PATCH  /api/v1/admin/schools/{schoolId}
POST   /api/v1/admin/schools/{schoolId}/areas
PATCH  /api/v1/admin/school-areas/{areaId}
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{userId}
PATCH  /api/v1/admin/users/{userId}
POST   /api/v1/admin/users/{userId}/restrictions
POST   /api/v1/admin/users/batch-action
GET    /api/v1/admin/reviews
POST   /api/v1/admin/reviews/batch-action
GET    /api/v1/admin/check-ins
GET    /api/v1/admin/check-ins/{checkInId}/photo
POST   /api/v1/admin/check-ins/batch-action
GET    /api/v1/admin/admin-users
POST   /api/v1/admin/admin-users
PATCH  /api/v1/admin/admin-users/{adminId}
GET    /api/v1/admin/audit-logs
```

批量用户和内容治理每次最多处理 100 条。限制或内容状态操作必须提供非空原因。

用户、评论和打卡页面都支持按 `schoolId` 固定学校范围。评论和打卡接口另外支持 `userId`（后端字段 `user_id`）固定到某一位用户；从用户档案卡进入评论或打卡页面时会自动带入该筛选条件。平台管理员可以选择全部学校或指定学校，学校管理员只能使用后端授权的学校范围。

## 4. 内容治理规则

- 评论和打卡照片只使用 `published`、`hidden` 状态，后台治理不物理删除内容或媒体文件。
- `hidden` 评论不在店铺评论列表中展示，也不参与评分与评论数聚合。
- `hidden` 打卡不在用户打卡、吃过状态和相关统计中展示。
- 管理员隐藏的评论不会因为用户再次编辑而自动恢复。
- 被禁止评论的用户调用评价写接口返回 `403 COMMENT_BLOCKED`。
- 被禁止上传图片的用户新增或替换打卡照片时返回 `403 IMAGE_UPLOAD_BLOCKED`。
- 有截止时间的限制到期后自动失效，不需要定时任务修改记录。
- 用户账号被禁用后无法通过用户鉴权依赖访问业务接口。

## 5. 私有照片

用户打卡照片继续保存在 MinIO 私有 bucket。Web 管理站通过 `GET /api/v1/admin/check-ins/{checkInId}/photo` 携带管理员 Token 获取图片 Blob，再生成浏览器临时对象地址。接口会先检查管理员学校范围，不返回 MinIO 私有对象地址。

## 6. 数据库迁移

`0006_admin_governance` 新增管理员学校绑定、用户限制和审计日志表，并为评论与打卡增加治理字段。已有打卡的 `school_id` 根据关联店铺回填后设为非空。
