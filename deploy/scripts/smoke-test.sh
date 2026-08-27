#!/usr/bin/env bash

set -Eeuo pipefail

PUBLIC_BASE_URL="${1:-${PUBLIC_BASE_URL:-}}"
ALLOW_HTTP="${ALLOW_HTTP:-0}"

[[ -n "${PUBLIC_BASE_URL}" ]] || {
    echo "用法：smoke-test.sh https://你的域名" >&2
    exit 1
}
[[ "${ALLOW_HTTP}" == "0" || "${ALLOW_HTTP}" == "1" ]] || {
    echo "ALLOW_HTTP 只允许设置为 0 或 1" >&2
    exit 1
}
if [[ "${ALLOW_HTTP}" != "1" && "${PUBLIC_BASE_URL}" != https://* ]]; then
    echo "正式冒烟测试必须使用 HTTPS；临时测试 HTTP 时显式设置 ALLOW_HTTP=1" >&2
    exit 1
fi

command -v curl >/dev/null 2>&1 || { echo "缺少 curl" >&2; exit 1; }
PUBLIC_BASE_URL="${PUBLIC_BASE_URL%/}"
RESPONSE_FILE="$(mktemp)"
HEADER_FILE="$(mktemp)"
trap 'rm -f -- "${RESPONSE_FILE}" "${HEADER_FILE}"' EXIT

echo "检查存活状态..."
curl --fail --silent --show-error --max-time 15 \
    "${PUBLIC_BASE_URL}/health/live" > "${RESPONSE_FILE}"
grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' "${RESPONSE_FILE}" || {
    echo "存活检查响应不符合预期" >&2
    exit 1
}

echo "检查依赖就绪状态..."
curl --fail --silent --show-error --max-time 15 \
    "${PUBLIC_BASE_URL}/health/ready" > "${RESPONSE_FILE}"
grep -Eq '"status"[[:space:]]*:[[:space:]]*"ready"' "${RESPONSE_FILE}" || {
    echo "就绪检查响应不符合预期" >&2
    exit 1
}

echo "检查 Web 管理后台和安全响应头..."
curl --fail --silent --show-error --max-time 20 \
    --dump-header "${HEADER_FILE}" --output /dev/null \
    "${PUBLIC_BASE_URL}/admin/"
grep -Eiq '^x-content-type-options:[[:space:]]*nosniff' "${HEADER_FILE}" || {
    echo "管理后台缺少 X-Content-Type-Options: nosniff" >&2
    exit 1
}

echo "公网冒烟测试通过：${PUBLIC_BASE_URL}"
