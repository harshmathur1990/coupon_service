"""changed varchar to text

Revision ID: 21c7f528e703
Revises: 3b85516e3d44
Create Date: 2016-06-04 14:33:13.396608

"""

# revision identifiers, used by Alembic.
revision = '21c7f528e703'
down_revision = '3b85516e3d44'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('auto_tester', 'body',
               existing_type=sa.VARCHAR(5000),
               type_=sa.TEXT,
               existing_nullable=False,
               nullable=False
                    )
    op.alter_column('auto_tester', 'prod_response',
               existing_type=sa.VARCHAR(5000),
               type_=sa.TEXT,
               existing_nullable=False,
               nullable=False
                    )
    op.alter_column('auto_tester', 'staging_response',
               existing_type=sa.VARCHAR(5000),
               existing_nullable=False,
               type_=sa.TEXT,
               nullable=False
                    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('auto_tester', 'body',
               existing_type=sa.TEXT,
               type_=sa.VARCHAR(5000),
               existing_nullable=False,
               nullable=False
                    )
    op.alter_column('auto_tester', 'prod_response',
               existing_type=sa.TEXT,
               type_=sa.VARCHAR(5000),
               existing_nullable=False,
               nullable=False
                    )
    op.alter_column('auto_tester', 'staging_response',
               existing_type=sa.TEXT,
               type_=sa.VARCHAR(5000),
               existing_nullable=False,
               nullable=False
                    )
    ### end Alembic commands ###
