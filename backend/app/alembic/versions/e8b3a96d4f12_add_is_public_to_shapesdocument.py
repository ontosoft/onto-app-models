"""Add is_public flag to shapesdocument

Revision ID: e8b3a96d4f12
Revises: c47f18e2b905
Create Date: 2026-10-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e8b3a96d4f12'
down_revision: Union[str, Sequence[str], None] = 'c47f18e2b905'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'shapesdocument',
        sa.Column(
            'is_public',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('shapesdocument', 'is_public')
