"""只验证生产配置是否满足 fail-closed 规则，不输出任何 Secret。"""

from app.core.config import Settings


def main() -> int:
    settings = Settings()
    if settings.app_env.lower() not in {"production", "prod"}:
        raise SystemExit("APP_ENV 必须设置为 production 才能执行生产配置预检")
    print("生产配置校验通过（Secret 内容未输出）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
