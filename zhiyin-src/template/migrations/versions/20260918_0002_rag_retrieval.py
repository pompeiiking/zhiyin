"""增加第三期 RAG 权威文档表。"""

from __future__ import annotations

from alembic import op

from zhiyin_infrastructure.persistence.models import RetrievalDocumentRow

revision = "20260918_0002"
down_revision = "20260916_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    RetrievalDocumentRow.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    RetrievalDocumentRow.__table__.drop(bind=op.get_bind(), checkfirst=True)
