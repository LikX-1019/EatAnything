#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DEPLOY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
REPO_ROOT="$(cd -- "${DEPLOY_DIR}/.." && pwd -P)"
COMPOSE_FILE="${DEPLOY_DIR}/compose.yml"
ENV_FILE="${DEPLOY_DIR}/.env"

DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-0}"
NO_CACHE="${NO_CACHE:-0}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
READINESS_TIMEOUT="${READINESS_TIMEOUT:-30}"

CURRENT_STEP="初始化"
COMPOSE_DIAGNOSTICS_READY=0
OLD_COMMIT=""
NEW_COMMIT=""
CURRENT_BRANCH=""
COMPOSE_PROJECT_NAME_VALUE=""
COMPOSE=()

log() {
    printf '[deploy] %s\n' "$*"
}

warn() {
    printf '[deploy] 警告：%s\n' "$*" >&2
}

print_compose_command() {
    printf '  '
    printf '%q ' "${COMPOSE[@]}" "$@"
    printf '\n'
}

print_failure_diagnostics() {
    if (( COMPOSE_DIAGNOSTICS_READY == 0 )); then
        return
    fi

    printf '\n[deploy] 当前 Compose 状态：\n' >&2
    "${COMPOSE[@]}" ps -a >&2 || true
    printf '\n[deploy] 可使用以下命令查看日志：\n' >&2
    print_compose_command logs api --tail=200 >&2
    print_compose_command logs postgres --tail=200 >&2
    print_compose_command logs minio --tail=200 >&2
    printf '  minio-init/db-init 使用 run --rm，本次执行输出保留在当前部署终端中。\n' >&2
}

fail() {
    local message="$1"
    trap - ERR
    printf '[deploy] 错误：%s\n' "${message}" >&2
    print_failure_diagnostics
    exit 1
}

on_error() {
    local exit_code="$1"
    local line_number="$2"
    local command="$3"
    trap - ERR
    set +e
    printf '[deploy] 错误：步骤“%s”失败（行 %s，退出码 %s）。\n' \
        "${CURRENT_STEP}" "${line_number}" "${exit_code}" >&2
    printf '[deploy] 失败命令：%s\n' "${command}" >&2
    print_failure_diagnostics
    exit "${exit_code}"
}

trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR

require_command() {
    local command_name="$1"
    command -v "${command_name}" >/dev/null 2>&1 \
        || fail "缺少必需命令：${command_name}"
}

validate_flag() {
    local name="$1"
    local value="$2"
    [[ "${value}" == "0" || "${value}" == "1" ]] \
        || fail "${name} 只允许设置为 0 或 1，当前值为：${value}"
}

validate_timeout() {
    local name="$1"
    local value="$2"
    [[ "${value}" =~ ^[1-9][0-9]*$ ]] \
        || fail "${name} 必须是正整数秒数，当前值为：${value}"
}

# 只读取脚本需要的非敏感键，不 source 或输出整个 .env。
read_env_value() {
    local key="$1"
    local line
    local value

    line="$(sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?${key}[[:space:]]*=(.*)$/\\2/p" "${ENV_FILE}" | tail -n 1)"
    [[ -n "${line}" ]] || return 1

    value="${line%$'\r'}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ "${value}" == \"* ]]; then
        value="${value#\"}"
        value="${value%%\"*}"
    elif [[ "${value}" == \'* ]]; then
        value="${value#\'}"
        value="${value%%\'*}"
    else
        value="${value%%[[:space:]]#*}"
        value="${value%"${value##*[![:space:]]}"}"
    fi
    printf '%s' "${value}"
}

check_env_permissions() {
    local mode
    if ! mode="$(stat -c '%a' "${ENV_FILE}" 2>/dev/null)"; then
        warn "无法检查 deploy/.env 权限；建议在服务器执行 chmod 600 deploy/.env。"
        return
    fi

    if [[ "${mode}" =~ [0-7]([0-7]{2})$ && "${BASH_REMATCH[1]}" != "00" ]]; then
        warn "deploy/.env 当前权限为 ${mode}，建议执行 chmod 600 deploy/.env。"
    fi
}

compose_container_id() {
    local service="$1"
    "${COMPOSE[@]}" ps -a -q "${service}" | tail -n 1
}

wait_for_healthy() {
    local service="$1"
    local deadline=$((SECONDS + HEALTH_TIMEOUT))
    local container_id
    local state
    local health

    log "等待 ${service} 进入 healthy（最长 ${HEALTH_TIMEOUT} 秒）..."
    while (( SECONDS < deadline )); do
        container_id="$(compose_container_id "${service}")"
        if [[ -n "${container_id}" ]]; then
            state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
            health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")"
            if [[ "${state}" == "running" && "${health}" == "healthy" ]]; then
                return 0
            fi
            if [[ "${state}" == "exited" || "${state}" == "dead" ]]; then
                fail "${service} 在健康检查通过前进入 ${state} 状态。"
            fi
        fi
        sleep 2
    done
    fail "等待 ${service} healthy 超时（${HEALTH_TIMEOUT} 秒）。"
}

wait_for_running() {
    local service="$1"
    local deadline=$((SECONDS + HEALTH_TIMEOUT))
    local container_id
    local state

    log "等待 ${service} 进入 running（最长 ${HEALTH_TIMEOUT} 秒）..."
    while (( SECONDS < deadline )); do
        container_id="$(compose_container_id "${service}")"
        if [[ -n "${container_id}" ]]; then
            state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
            if [[ "${state}" == "running" ]]; then
                return 0
            fi
            if [[ "${state}" == "exited" || "${state}" == "dead" ]]; then
                fail "${service} 未保持运行，当前状态为 ${state}。"
            fi
        fi
        sleep 2
    done
    fail "等待 ${service} running 超时（${HEALTH_TIMEOUT} 秒）。"
}

run_oneshot() {
    local service="$1"
    local exit_code

    if timeout --foreground --kill-after=10s "${HEALTH_TIMEOUT}s" \
        "${COMPOSE[@]}" run --rm --no-deps "${service}"; then
        return 0
    else
        exit_code=$?
    fi

    if [[ "${exit_code}" == "124" || "${exit_code}" == "137" ]]; then
        fail "${service} 本次执行超时（${HEALTH_TIMEOUT} 秒）。"
    fi
    fail "${service} 本次执行失败，退出码为 ${exit_code}。"
}

check_readiness() {
    local url="$1"
    local deadline=$((SECONDS + READINESS_TIMEOUT))
    local response
    local body
    local http_code=""

    log "验证宿主机 readiness：${url}（最长 ${READINESS_TIMEOUT} 秒）..."
    while (( SECONDS < deadline )); do
        if response="$(curl --silent --show-error --max-time 5 --write-out $'\n%{http_code}' "${url}" 2>/dev/null)"; then
            http_code="${response##*$'\n'}"
            body="${response%$'\n'*}"
            if [[ "${http_code}" == "200" ]] \
                && grep -Eq '"status"[[:space:]]*:[[:space:]]*"ready"' <<<"${body}"; then
                return 0
            fi
        fi
        sleep 2
    done
    fail "readiness 校验失败：${url} 未返回 HTTP 200 且 status=ready（最后 HTTP 状态：${http_code:-无}）。"
}

main() {
    local git_root
    local remote_ref
    local remote_commit
    local env_project_name=""
    local api_container_port=""
    local published_address=""
    local readiness_url=""
    local -a build_args=(build)

    CURRENT_STEP="检查参数"
    validate_flag DRY_RUN "${DRY_RUN}"
    validate_flag NO_CACHE "${NO_CACHE}"
    validate_timeout HEALTH_TIMEOUT "${HEALTH_TIMEOUT}"
    validate_timeout READINESS_TIMEOUT "${READINESS_TIMEOUT}"

    CURRENT_STEP="检查环境文件"
    [[ -f "${ENV_FILE}" ]] || fail "缺少 deploy/.env。请先执行：cp deploy/.env.example deploy/.env，然后填写真实配置。"
    check_env_permissions

    CURRENT_STEP="读取 Compose project 配置"
    require_command sed
    require_command tail
    env_project_name="$(read_env_value COMPOSE_PROJECT_NAME || true)"
    if [[ -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
        COMPOSE_PROJECT_NAME_VALUE="${COMPOSE_PROJECT_NAME}"
    elif [[ -n "${env_project_name}" ]]; then
        COMPOSE_PROJECT_NAME_VALUE="${env_project_name}"
    else
        fail "COMPOSE_PROJECT_NAME 未配置。请在 deploy/.env 中设置 COMPOSE_PROJECT_NAME=eatanything-test；未来 production 可使用 COMPOSE_PROJECT_NAME=eatanything-prod。"
    fi
    [[ "${COMPOSE_PROJECT_NAME_VALUE}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] \
        || fail "COMPOSE_PROJECT_NAME 无效：${COMPOSE_PROJECT_NAME_VALUE}"
    COMPOSE=(
        docker compose
        --project-name "${COMPOSE_PROJECT_NAME_VALUE}"
        --file "${COMPOSE_FILE}"
        --env-file "${ENV_FILE}"
    )

    CURRENT_STEP="检查依赖"
    require_command git
    require_command docker
    require_command curl
    require_command grep
    require_command timeout
    docker compose version >/dev/null 2>&1 \
        || fail "Docker Compose plugin 不可用；请确认 docker compose version 能正常执行。"
    docker info >/dev/null 2>&1 \
        || fail "无法连接 Docker daemon；请确认 Docker Engine 已启动且当前用户有访问权限。"

    CURRENT_STEP="检查 Git 工作区"
    git_root="$(git -C "${REPO_ROOT}" rev-parse --show-toplevel)"
    git_root="$(cd -- "${git_root}" && pwd -P)"
    [[ "${git_root}" == "${REPO_ROOT}" ]] \
        || fail "脚本解析的仓库根目录与 Git 根目录不一致：${REPO_ROOT} != ${git_root}"
    [[ -z "$(git -C "${REPO_ROOT}" status --porcelain)" ]] \
        || fail "Git 工作区不干净，已停止部署。请人工检查 git status；脚本不会 stash、reset 或删除修改。"
    CURRENT_BRANCH="$(git -C "${REPO_ROOT}" symbolic-ref --quiet --short HEAD)" \
        || fail "当前处于 detached HEAD，已停止部署。"
    git check-ref-format --branch "${DEPLOY_BRANCH}" >/dev/null 2>&1 \
        || fail "DEPLOY_BRANCH 不是有效分支名：${DEPLOY_BRANCH}"
    [[ "${CURRENT_BRANCH}" == "${DEPLOY_BRANCH}" ]] \
        || fail "当前分支为 ${CURRENT_BRANCH}，要求部署分支为 ${DEPLOY_BRANCH}。脚本不会自动 checkout；请人工确认。"
    git -C "${REPO_ROOT}" remote get-url origin >/dev/null 2>&1 \
        || fail "Git remote origin 不存在。"
    OLD_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
    NEW_COMMIT="${OLD_COMMIT}"

    CURRENT_STEP="校验 Compose 配置"
    log "校验 Compose 配置（project=${COMPOSE_PROJECT_NAME_VALUE}）..."
    "${COMPOSE[@]}" config --quiet
    COMPOSE_DIAGNOSTICS_READY=1

    if [[ "${DRY_RUN}" == "1" ]]; then
        printf '\n================================\n'
        printf 'EatAnything deploy dry-run PASS\n\n'
        printf 'Branch: %s\n' "${CURRENT_BRANCH}"
        printf 'Commit: %s\n' "${OLD_COMMIT}"
        printf 'Compose project: %s\n' "${COMPOSE_PROJECT_NAME_VALUE}"
        printf '未执行 git fetch/merge、镜像构建、服务启动或数据库迁移。\n'
        printf '================================\n'
        return
    fi

    CURRENT_STEP="更新 Git 分支"
    log "从 origin 获取最新提交..."
    git -C "${REPO_ROOT}" fetch --prune origin
    remote_ref="refs/remotes/origin/${DEPLOY_BRANCH}"
    git -C "${REPO_ROOT}" show-ref --verify --quiet "${remote_ref}" \
        || fail "远端分支 origin/${DEPLOY_BRANCH} 不存在。"
    log "仅以 fast-forward 方式更新 ${DEPLOY_BRANCH}..."
    git -C "${REPO_ROOT}" merge --ff-only "origin/${DEPLOY_BRANCH}"
    NEW_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
    remote_commit="$(git -C "${REPO_ROOT}" rev-parse "${remote_ref}")"
    [[ "${NEW_COMMIT}" == "${remote_commit}" ]] \
        || fail "本地 ${DEPLOY_BRANCH} 含有 origin/${DEPLOY_BRANCH} 不存在的提交，已拒绝部署。请人工核对分支历史。"
    if [[ "${OLD_COMMIT}" == "${NEW_COMMIT}" ]]; then
        log "代码已是最新版本，继续执行配置、构建与健康检查。"
    else
        log "代码已从 ${OLD_COMMIT} fast-forward 到 ${NEW_COMMIT}。"
    fi

    # 更新后再次校验，确保实际将部署的新版本配置有效。
    CURRENT_STEP="重新校验更新后的 Compose 配置"
    "${COMPOSE[@]}" config --quiet

    CURRENT_STEP="构建 API 镜像"
    if [[ "${NO_CACHE}" == "1" ]]; then
        build_args+=(--no-cache)
    fi
    log "构建 api 镜像（db-init 与 api 共用该镜像）..."
    "${COMPOSE[@]}" "${build_args[@]}" api

    CURRENT_STEP="启动基础服务"
    log "启动或更新 postgres 与 minio（保留现有 volume，不更新 api）..."
    "${COMPOSE[@]}" up -d postgres minio

    CURRENT_STEP="等待基础服务状态"
    wait_for_healthy postgres
    wait_for_running minio

    CURRENT_STEP="执行本次 MinIO 初始化"
    log "显式执行本次 minio-init..."
    run_oneshot minio-init

    CURRENT_STEP="执行本次数据库迁移"
    log "显式执行本次 db-init；成功前不会更新 api..."
    run_oneshot db-init

    CURRENT_STEP="启动或更新 API"
    log "本次 db-init 已成功，开始启动或更新 api..."
    "${COMPOSE[@]}" up -d --no-deps api

    CURRENT_STEP="等待 API 健康状态"
    wait_for_healthy api

    CURRENT_STEP="解析 API 发布地址"
    api_container_port="${API_CONTAINER_PORT:-$(read_env_value API_CONTAINER_PORT || true)}"
    api_container_port="${api_container_port:-8000}"
    [[ "${api_container_port}" =~ ^[0-9]+$ ]] && (( api_container_port >= 1 && api_container_port <= 65535 )) \
        || fail "API_CONTAINER_PORT 必须是 1 到 65535 的整数，当前值为：${api_container_port}"
    published_address="$("${COMPOSE[@]}" port api "${api_container_port}" | tail -n 1)"
    [[ -n "${published_address}" ]] \
        || fail "无法从 docker compose port 获取 api 的宿主机发布地址。"
    case "${published_address}" in
        0.0.0.0:*) published_address="127.0.0.1:${published_address##*:}" ;;
        \[::\]:*) published_address="[::1]:${published_address##*:}" ;;
    esac
    readiness_url="http://${published_address}/health/ready"

    CURRENT_STEP="验证 HTTP readiness"
    check_readiness "${readiness_url}"

    printf '\n================================\n'
    printf 'EatAnything deploy success\n\n'
    printf 'Branch: %s\n' "${CURRENT_BRANCH}"
    printf 'Old commit: %s\n' "${OLD_COMMIT}"
    printf 'New commit: %s\n\n' "${NEW_COMMIT}"
    printf 'Compose project: %s\n' "${COMPOSE_PROJECT_NAME_VALUE}"
    printf 'postgres: healthy\n'
    printf 'minio: running\n'
    printf 'minio-init: passed\n'
    printf 'db-init: passed\n'
    printf 'api: healthy\n\n'
    printf 'readiness: HTTP 200, status=ready\n'
    printf '================================\n'
}

main "$@"
