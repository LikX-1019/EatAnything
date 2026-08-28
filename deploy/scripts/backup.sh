#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
REPO_ROOT="$(cd -- "${DEPLOY_DIR}/.." && pwd -P)"
ENV_FILE="${DEPLOY_DIR}/.env"
BACKUP_ROOT="${1:-${REPO_ROOT}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_ROOT}/${STAMP}"

[[ -f "${ENV_FILE}" ]] || { echo "缺少 deploy/.env" >&2; exit 1; }
[[ "${TARGET}" != "/" && "${TARGET}" != "${REPO_ROOT}" ]] || { echo "拒绝使用危险备份路径" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "缺少 docker" >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "缺少 sha256sum" >&2; exit 1; }
mkdir -p "${TARGET}"

COMPOSE_PROJECT_NAME="$(sed -n -E 's/^COMPOSE_PROJECT_NAME[[:space:]]*=[[:space:]]*//p' "${ENV_FILE}" | tail -n 1 | tr -d '\r"' | xargs)"
POSTGRES_DB="$(sed -n -E 's/^POSTGRES_DB[[:space:]]*=[[:space:]]*//p' "${ENV_FILE}" | tail -n 1 | tr -d '\r"' | xargs)"
POSTGRES_USER="$(sed -n -E 's/^POSTGRES_USER[[:space:]]*=[[:space:]]*//p' "${ENV_FILE}" | tail -n 1 | tr -d '\r"' | xargs)"
[[ -n "${COMPOSE_PROJECT_NAME}" && -n "${POSTGRES_DB}" && -n "${POSTGRES_USER}" ]] || { echo "部署配置缺少项目名或数据库名称" >&2; exit 1; }
COMPOSE=(docker compose --project-name "${COMPOSE_PROJECT_NAME}" --file "${DEPLOY_DIR}/compose.yml" --env-file "${ENV_FILE}")

echo "备份 PostgreSQL（不输出密码）..."
"${COMPOSE[@]}" exec -T postgres pg_dump --format=custom --no-owner --no-acl --username="${POSTGRES_USER}" "${POSTGRES_DB}" > "${TARGET}/postgres.dump"
echo "备份 MinIO 公开和私有 bucket..."
# minio-init 服务自身已经配置 `/bin/sh -c` 入口。这里显式覆盖入口，避免
# 再追加一层 `sh -c` 后外层 shell 只执行 `sh` 并等待标准输入。
"${COMPOSE[@]}" run --rm --no-deps --entrypoint /bin/sh -v "${TARGET}:/backup" minio-init -c 'scheme=http; [ "$MINIO_SECURE" = "true" ] && scheme=https; mc alias set local "${scheme}://${MINIO_ENDPOINT}" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null && mc mirror --overwrite "local/${MINIO_BUCKET}" /backup/minio-public && mc mirror --overwrite "local/${MINIO_PRIVATE_BUCKET}" /backup/minio-private' >/dev/null
(
    cd -- "${TARGET}"
    sha256sum postgres.dump > SHA256SUMS
    printf 'created_at_utc=%s\ncompose_project=%s\npostgres_db=%s\n' \
        "${STAMP}" "${COMPOSE_PROJECT_NAME}" "${POSTGRES_DB}" > manifest.txt
)
# TARGET 由当前部署用户在 umask 077 下创建；只需保证这个入口目录不可被
# 其他用户遍历。MinIO 容器写出的文件可能属于 root，递归 chmod 会误报失败。
chmod go-rwx "${TARGET}"
echo "备份完成：${TARGET}"
