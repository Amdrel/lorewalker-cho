"""added scoreboard table

Revision ID: c033216d2d8a
Revises: 4b48938be704
Create Date: 2019-05-13 06:54:04.291916+00:00
"""

# pylint: disable=no-member

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql

from alembic import op


# Revision identifiers, used by Alembic.
revision = 'c033216d2d8a'
down_revision = '4b48938be704'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrades the database a single revision."""

    op.create_table(
        "scoreboards",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("guild_id", sa.BigInteger, nullable=False),
        sa.Column("scores", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guilds.id"],
            ondelete="CASCADE",
        ),
        sa.Index("scoreboards_guild_id_idx", "guild_id", unique=True),
    )


def downgrade():
    """Downgrades the database a single revision."""

    op.drop_table("scoreboards")
