"""Add shapesdocument table and AppModel provenance columns

Revision ID: c47f18e2b905
Revises: a9c2d41b7e30
Create Date: 2026-10-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c47f18e2b905'
down_revision: Union[str, Sequence[str], None] = 'a9c2d41b7e30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'shapesdocument',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('format', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('content_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Dedupe is per user: the same user cannot store identical content twice,
    # but different users may each keep their own copy of the same shapes.
    op.create_index(
        op.f('ix_shapesdocument_owner_content_hash'),
        'shapesdocument',
        ['owner_id', 'content_hash'],
        unique=True,
    )

    op.add_column('appmodel', sa.Column('shapes_id', sa.Uuid(), nullable=True))
    op.add_column(
        'appmodel',
        sa.Column(
            'generation_method',
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
    )
    # Deleting a shapes document keeps its generated models; they just lose
    # the provenance link.
    op.create_foreign_key(
        'fk_appmodel_shapes_id_shapesdocument',
        'appmodel',
        'shapesdocument',
        ['shapes_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_appmodel_shapes_id_shapesdocument', 'appmodel', type_='foreignkey'
    )
    op.drop_column('appmodel', 'generation_method')
    op.drop_column('appmodel', 'shapes_id')
    op.drop_index(op.f('ix_shapesdocument_owner_content_hash'), table_name='shapesdocument')
    op.drop_table('shapesdocument')
