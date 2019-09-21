# Lorewalker Cho is a Discord bot that plays WoW-inspired trivia games.
# Copyright (C) 2019  Walter Kuppens
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql

METADATA = sa.MetaData()

GUILDS = sa.Table(
    "guilds",
    METADATA,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("discord_guild_id", sa.BigInteger, nullable=False),
    sa.Column("config", postgresql.JSONB(), nullable=False),
    sa.Index(
        "guilds_discord_guild_id_idx",
        "discord_guild_id",
        unique=True,
    ),
)

ACTIVE_GAMES = sa.Table(
    "active_games",
    METADATA,
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

SCOREBOARDS = sa.Table(
    "scoreboards",
    METADATA,
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
