"""给检索审计表增加"降级原因"列（D13 残留）。

为什么需要迁移而不是只改模型：本项目 `DatabaseContext.ensure_ready()` 用的是
`Base.metadata.create_all`，它**只建缺失的表、不给已有表加列**。所以运行中的库
必须在部署时显式跑一次 `alembic upgrade head`（compose 里的 `zhiyin-migrate`
服务就干这个），否则带新列的 INSERT 会直接失败——而审计写失败会让**检索本身**失败。

列是新加且可空（`server_default=''`），对既有行与旧代码都兼容。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260919_0003"
down_revision = "20260918_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "retrieval_log",
        sa.Column(
            "degraded_reason",
            sa.String(length=32),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("retrieval_log", "degraded_reason")
