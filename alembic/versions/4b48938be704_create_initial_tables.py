"""create initial tables

Revision ID: 4b48938be704
Revises:
Create Date: 2019-05-05 04:39:48.160733+00:00
"""

# pylint: disable=no-member

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql

from alembic import op


# Revision identifiers, used by Alembic.
revision = "4b48938be704"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrades the database a single revision."""

    op.create_table(
        "guilds",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("discord_guild_id", sa.Text, nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Index(
            "guilds_discord_guild_id_idx",
            "discord_guild_id",
            unique=True,
        ),
    )
    op.create_table(
        "active_games",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("guild_id", sa.BigInteger, nullable=False),
        sa.Column("game_state", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guilds.id"],
            ondelete="CASCADE",
        ),
        sa.Index("active_games_guild_id_idx", "guild_id", unique=True),
    )


def downgrade():
    """Downgrades the database a single revision."""

    op.drop_table("active_games")
    op.drop_table("guilds")
