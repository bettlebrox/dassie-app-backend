"""MOdify article to use string for document ids

Revision ID: 2031f0fe6bff
Revises: 9a6524d70ed9
Create Date: 2024-06-05 15:49:46.418945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2031f0fe6bff'
down_revision: Union[str, None] = '9a6524d70ed9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('article', '_document_id',
               existing_type=sa.INTEGER(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('article', '_parent_document_id',
               existing_type=sa.INTEGER(),
               type_=sa.String(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('article', '_parent_document_id',
               existing_type=sa.String(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('article', '_document_id',
               existing_type=sa.String(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    # ### end Alembic commands ###
