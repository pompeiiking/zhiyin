"""创建对话消息表。

`conversation_message` 是本轮新增的只追加消息表，用于按任务会话读回历史。
为什么必须写迁移：生产装配的 `DatabaseContext` 是 `auto_create=False`
（见 `zhiyin-boot/zhiyin_boot/container/repositories.py`），
`ensure_ready()` 里的 `Base.metadata.create_all` 不会执行，库表完全由 alembic 管理。
首版迁移 `20260916_0001` 里的 `create_all` 只在首次执行时建过当时的表，
新增表不会因为模型文件里多了一个类就自动出现——缺表会让读历史直接抛
`(1146, "Table 'conversation_message' doesn't exist")`。
"""

from __future__ import annotations

from alembic import op

from zhiyin_infrastructure.persistence.models import ConversationMessageRow

revision = "20260920_0004"
down_revision = "20260919_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ConversationMessageRow.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ConversationMessageRow.__table__.drop(bind=op.get_bind(), checkfirst=True)
