# 后端 API 生产镜像：EatAnything backend
# 仅安装运行时依赖，不把宿主机 .env、测试与缓存打入镜像。
# 环境变量在运行时通过 Docker Compose 注入，禁止在镜像内写死密钥。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_EXTRA_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

WORKDIR /app

# 先复制 pyproject.toml，按 [project].dependencies 安装运行时依赖，
# 以利用 Docker 镜像层缓存：依赖层只在 pyproject.toml 变化时重建。
# 项目当前不是可直接 `pip install .` 的标准 package（flat-layout），
# 因此不安装项目本身，运行时通过 WORKDIR=/app 直接导入 app 包。
COPY pyproject.toml ./
RUN python -c "import tomllib; from pathlib import Path; deps=tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']; Path('requirements.txt').write_text('\n'.join(deps)+'\n', encoding='utf-8')" \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -f requirements.txt

# 应用代码与迁移定义（alembic / database 供运行和迁移使用）
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY database ./database
COPY scripts ./scripts

# 以非 root 用户运行
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
