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

"""Contains CRUD functions for scoreboards in postgres."""

import logging
import sqlalchemy as sa

from sqlalchemy.engine.interfaces import Connectable
from sqlalchemy.engine.result import ResultProxy

from lorewalker_cho.sql.schema import GUILDS, SCOREBOARDS

LOGGER = logging.getLogger("cho")


def get_scoreboard(conn: Connectable, guild_id: int) -> tuple:
    """Retrieves an existing game state.

    :param c conn:
    :param int guild_id:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :rtype: tuple
    :return:
    """

    query = sa.select([GUILDS.c.id]) \
        .where(GUILDS.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = sa.select([SCOREBOARDS.c.scores]) \
        .where(SCOREBOARDS.c.guild_id == guild_id_fkey[0]) \
        .limit(1)
    return conn.execute(query).first()


def save_scoreboard(conn: Connectable, guild_id: int, scores) -> ResultProxy:
    """Saves a game state to the database.

    :param c conn:
    :param int guild_id:
    :param dict scores:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :type r: sqlalchemy.engine.result.ResultProxy
    :rtype: r
    :return:
    """

    query = sa.select([GUILDS.c.id]) \
        .where(GUILDS.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = sa.select([SCOREBOARDS.c.id]) \
        .where(SCOREBOARDS.c.guild_id == guild_id_fkey[0]) \
        .limit(1)
    existing_scoreboard_id = conn.execute(query).first()

    if existing_scoreboard_id is not None:
        LOGGER.debug("Updating existing scoreboard.")

        query = SCOREBOARDS.update(None).values({
            "scores": scores or {},
        }).where(SCOREBOARDS.c.id == existing_scoreboard_id[0])
        return conn.execute(query)

    LOGGER.debug("Creating new scoreboard.")

    query = SCOREBOARDS.insert(None).values({
        "guild_id": guild_id_fkey[0],
        "scores": scores or {},
    })
    return conn.execute(query)
