"""在一次性 MySQL 库上执行与本地实现相同的 Repository 契约测试。"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from urllib.parse import quote_plus

import pymysql

VERIFY_DATABASE = "zhiyin_contract_verify"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少契约验证配置：{name}")
    return value


def _identifier(value: str, label: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise RuntimeError(f"{label} 只能包含字母、数字和下划线")
    return value


def main() -> int:
    host = _required("MYSQL_HOST")
    root_password = _required("MYSQL_ROOT_PASSWORD")
    app_user = _identifier(_required("ZHIYIN_MYSQL_USER"), "MySQL 用户名")
    app_password = _required("ZHIYIN_MYSQL_PASSWORD")
    database = _identifier(VERIFY_DATABASE, "验证库名")

    root = pymysql.connect(host=host, user="root", password=root_password, autocommit=True)
    try:
        with root.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
            cursor.execute(
                f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_0900_ai_ci"
            )
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{app_user}`@'%' ")

        encoded_user = quote_plus(app_user)
        encoded_password = quote_plus(app_password)
        database_url = (
            f"mysql+pymysql://{encoded_user}:{encoded_password}@{host}:3306/{database}"
            "?charset=utf8mb4"
        )
        env = {**os.environ, "ZHIYIN_DATABASE_URL": database_url}
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
        env["ZHIYIN_TEST_MYSQL_URL"] = database_url
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/contracts/test_repository_contract.py", "-q"],
            env=env,
            check=False,
        )
        return result.returncode
    finally:
        with root.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        root.close()


if __name__ == "__main__":
    raise SystemExit(main())
