"""Add Article._logged_at Index

Revision ID: bde4990708ab
Revises: 3e4b38f9a4b0
Create Date: 2024-04-25 14:27:03.808270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bde4990708ab'
down_revision: Union[str, None] = '3e4b38f9a4b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_article__logged_at'), 'article', ['_logged_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_article__logged_at'), table_name='article')
    # ### end Alembic commands ###
