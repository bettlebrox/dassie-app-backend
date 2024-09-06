"""_updated to base

Revision ID: 77e138b9dcaf
Revises: c4796d9139b9
Create Date: 2024-09-05 17:08:27.328881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77e138b9dcaf'
down_revision: Union[str, None] = 'c4796d9139b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('association', sa.Column('_updated_at', sa.DateTime(), nullable=True))
    op.add_column('browsed', sa.Column('_updated_at', sa.DateTime(), nullable=True))
    op.add_column('recurrent', sa.Column('_updated_at', sa.DateTime(), nullable=True))
    op.add_column('sporadic', sa.Column('_updated_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sporadic', '_updated_at')
    op.drop_column('recurrent', '_updated_at')
    op.drop_column('browsed', '_updated_at')
    op.drop_column('association', '_updated_at')
    # ### end Alembic commands ###
