"""创建 M3 关系存储运行表。"""

from __future__ import annotations

from alembic import op

from zhiyin_infrastructure.persistence.models import Base

revision = "20260916_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
