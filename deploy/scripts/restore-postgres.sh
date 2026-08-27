#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
ENV_FILE="${DEPLOY_DIR}/.env"
DUMP="${1:-}"
[[ -f "${ENV_FILE}" && -f "${DUMP}" ]] || { echo "用法：restore-postgres.sh <postgres.dump>" >&2; exit 1; }
[[ "${CONFIRM_RESTORE:-}" == "YES" ]] || { echo "恢复会覆盖目标数据库，请设置 CONFIRM_RESTORE=YES" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "缺少 docker" >&2; exit 1; }
checksum_file="$(dirname -- "${DUMP}")/SHA256SUMS"
if [[ -f "${checksum_file}" && "$(basename -- "${DUMP}")" == "postgres.dump" ]]; then
    command -v sha256sum >/dev/null 2>&1 || { echo "缺少 sha256sum" >&2; exit 1; }
    echo "校验 PostgreSQL 备份完整性..."
    (cd -- "$(dirname -- "${DUMP}")" && sha256sum --check SHA256SUMS)
fi
read_env() { sed -n -E "s/^$1[[:space:]]*=[[:space:]]*//p" "${ENV_FILE}" | tail -n 1 | tr -d '\r"' | xargs; }
project="$(read_env COMPOSE_PROJECT_NAME)"; db="$(read_env POSTGRES_DB)"; user="$(read_env POSTGRES_USER)"
[[ -n "${project}" && -n "${db}" && -n "${user}" ]] || { echo "部署配置不完整" >&2; exit 1; }
compose=(docker compose --project-name "${project}" --file "${DEPLOY_DIR}/compose.yml" --env-file "${ENV_FILE}")
echo "开始恢复 PostgreSQL（不输出密码）..."
"${compose[@]}" exec -T postgres pg_restore --clean --if-exists --no-owner --no-acl --username="${user}" --dbname="${db}" < "${DUMP}"
echo "PostgreSQL 恢复完成，请执行 readiness 和业务冒烟测试。"
