"""Add is_public flag to appmodel

Revision ID: a9c2d41b7e30
Revises: fb3473960be7
Create Date: 2026-10-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9c2d41b7e30'
down_revision: Union[str, Sequence[str], None] = 'fb3473960be7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'appmodel',
        sa.Column(
            'is_public',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column('appmodel', 'is_public')
