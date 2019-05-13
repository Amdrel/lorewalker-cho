import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql

metadata = sa.MetaData()

guilds = sa.Table(
    "guilds",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("discord_guild_id", sa.BigInteger, nullable=False),
    sa.Column("config", postgresql.JSONB(), nullable=False),
    sa.Index(
        "guilds_discord_guild_id_idx",
        "discord_guild_id",
        unique=True,
    ),
)

active_games = sa.Table(
    "active_games",
    metadata,
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

scoreboards = sa.Table(
    "scoreboards",
    metadata,
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
