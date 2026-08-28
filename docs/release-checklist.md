# 生产发布检查清单

每次正式发布按本清单逐项确认。数据库迁移、Secret 变更和数据恢复必须由有权限的运维人员执行。

## 一、发布前

- [ ] 发布提交已经过代码评审，Git 工作区干净，服务器分支与 `DEPLOY_BRANCH` 一致。
- [ ] GitHub Actions 的后端、用户端、管理后台和部署检查全部通过。
- [ ] `deploy/.env` 权限为 `600`，没有占位值，没有复制本机开发配置。
- [ ] `APP_ENV=production`、`DEV_AUTH_ENABLED=false`，微信配置和随机 Secret 已填写。
- [ ] 若启用微信订阅消息，两套模板 ID 与标题、内容、时间字段 key 已核对，未把 AppSecret 写入仓库或日志。
- [ ] `COMPOSE_PROJECT_NAME`、数据卷和网络名称与目标环境完全一致。
- [ ] `MINIO_PUBLIC_URL`、`CORS_ORIGINS`、`APP_DOMAIN` 使用正式 HTTPS 域名。
- [ ] DNS 已解析到目标服务器，防火墙只开放必要端口。
- [ ] PostgreSQL 和 MinIO 未直接暴露公网，MinIO Console 未开放公网。
- [ ] 已记录当前 Git commit、镜像标签、数据库 revision 和 Compose 状态。

## 二、备份与预检

```bash
./deploy/scripts/backup.sh /srv/eatanything/backups
DRY_RUN=1 ./deploy/scripts/deploy.sh
docker compose -f deploy/compose.yml --env-file deploy/.env run --rm --no-deps db-init \
  python /app/scripts/validate_production_config.py
```

- [ ] PostgreSQL dump 和两个 MinIO 目录均存在，备份目录只有运维账号可读。
- [ ] 最近一次恢复演练结果有效，磁盘空间足够容纳新镜像、数据库和备份。
- [ ] 变更中涉及的 Alembic migration 已在测试环境从旧版本完整升级验证。

## 三、执行发布

```bash
./deploy/scripts/deploy.sh
./deploy/scripts/smoke-test.sh https://你的域名
```

部署脚本只允许 fast-forward 更新；迁移成功前不会更新现有 API。失败时保留现场，不会自动 reset、删除 volume 或回滚数据库。

## 四、业务验收

- [ ] `/health/live` 与 `/health/ready` 返回 HTTP 200。
- [ ] `/admin/` 可登录，HTTPS 证书、静态资源和安全响应头正常。
- [ ] 平台管理员可切换全部学校；学校管理员无法访问未授权学校。
- [ ] 学校、区域、店铺的新增、编辑和筛选正常。
- [ ] CSV/XLSX 店铺导入可预校验，错误批次不写入。
- [ ] 用户档案能查看账号、评论和打卡，限制操作生效。
- [ ] 评论和打卡照片可隐藏、恢复，审计日志完整。
- [ ] 通知和公告可按权限创建、定时发布、阅读与撤回，首页公告和消息未读数正常。
- [ ] `notification-worker` 处于 running；测试账号可完成两套模板授权并收到测试订阅消息，失败任务无持续重试风暴。
- [ ] 小程序登录、学校切换、店铺、随机、收藏、打卡、评论和图片显示正常。
- [ ] 微信公众平台的 `request`、`uploadFile`、`downloadFile` 合法域名已登记。
- [ ] 观察 15 至 30 分钟：无持续 5xx、容器重启、磁盘告警或异常登录。

## 五、回滚原则

1. 立即停止继续发布，保留日志、commit、容器状态和失败命令。
2. 纯前端或无数据库变更时，可重新部署上一已验证 commit 对应镜像。
3. 已执行数据库 migration 时，不要直接回退应用；先确认 migration 是否向后兼容。
4. 只有确认必须恢复数据时，进入维护窗口并使用已验证备份：

```bash
CONFIRM_RESTORE=YES ./deploy/scripts/restore-postgres.sh /备份目录/postgres.dump
```

5. MinIO 需要恢复时，人工核对目标 bucket 后用 `mc mirror --overwrite`，避免覆盖错误环境。
6. 回滚后重复公网冒烟和完整业务验收，并记录故障原因与处理结果。

普通回滚禁止执行 `docker compose down -v`、`git reset --hard` 或删除备份目录。
