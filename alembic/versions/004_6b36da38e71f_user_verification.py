"""
Migration to add fields for password reset and user verification.

Revision ID: 6b36da38e71f
Revises: b3069b0347d5
Create Date: 2022-07-03 14:54:13.364583

"""

import os
import sys

import sqlalchemy as sa
from alembic import op

sys.path.append(os.getcwd())

# revision identifiers, used by Alembic.
revision = "6b36da38e71f"
down_revision = "b3069b0347d5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_verification",
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "modified",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "username", sa.String(length=256, collation="NOCASE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(length=256), nullable=False),
        sa.Column("expiration_timestamp", sa.Integer(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "user",
        sa.Column("verified", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE user SET verified=false")
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("verified", nullable=False)
    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("verified")
    op.drop_table("user_verification")
    # ### end Alembic commands ###
