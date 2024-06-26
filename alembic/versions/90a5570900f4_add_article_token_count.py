"""Add article token_count

Revision ID: 90a5570900f4
Revises: 761dee54e82d
Create Date: 2024-05-29 16:39:58.489843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90a5570900f4'
down_revision: Union[str, None] = '761dee54e82d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('article', sa.Column('_token_count', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('article', '_token_count')
    # ### end Alembic commands ###
