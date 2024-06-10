"""Add article ids from navlog

Revision ID: 9a6524d70ed9
Revises: 90a5570900f4
Create Date: 2024-06-05 15:11:33.047498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a6524d70ed9'
down_revision: Union[str, None] = '90a5570900f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('article', sa.Column('_document_id', sa.Integer(), nullable=True))
    op.add_column('article', sa.Column('_parent_document_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('article', '_parent_document_id')
    op.drop_column('article', '_document_id')
    # ### end Alembic commands ###
