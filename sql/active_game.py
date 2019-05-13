# Lorewalker Cho is a Discord bot that plays WoW-inspired trivia games.
# Copyright (C) 2019  Walter Kuppens

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Contains CRUD functions for game states in postgres."""

import logging
import sqlalchemy as sa

from sqlalchemy.engine.interfaces import Connectable
from sqlalchemy.engine.result import ResultProxy

from sql.schema import guilds, active_games

LOGGER = logging.getLogger("cho")


def get_incomplete_games(conn: Connectable) -> list:
    """Queries for games that haven't finished (usually present on restart).

    :param c conn:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :rtype: list
    :return:
    """

    query = sa.select([guilds.c.discord_guild_id, active_games.c.game_state]) \
        .select_from(
            sa.join(active_games, guilds,
                    active_games.c.guild_id == guilds.c.id)) \
        .where(active_games.c.game_state['complete'] == "false")
    return conn.execute(query).fetchall()


def get_game_state(conn: Connectable, guild_id: int) -> tuple:
    """Retrieves an existing game state.

    :param c conn:
    :param int guild_id:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :rtype: tuple
    :return:
    """

    query = sa.select([guilds.c.id]) \
        .where(guilds.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = sa.select([active_games.c.game_state]) \
        .where(active_games.c.guild_id == guild_id_fkey[0]) \
        .limit(1)
    return conn.execute(query).first()


def save_game_state(conn: Connectable, game_state) -> ResultProxy:
    """Saves a game state to the database.

    :param c conn:
    :param g game_state:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :type r: sqlalchemy.engine.result.ResultProxy
    :type g: game_state.GameState
    :rtype: r
    :return:
    """

    query = sa.select([guilds.c.id]) \
        .where(guilds.c.discord_guild_id == game_state.guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = sa.select([active_games.c.id]) \
        .where(active_games.c.guild_id == guild_id_fkey[0]) \
        .limit(1)
    existing_game_id = conn.execute(query).first()

    if existing_game_id is not None:
        LOGGER.debug("Updating existing game state.")

        query = active_games.update(None).values({
            "game_state": game_state.serialize(),
        }).where(active_games.c.id == existing_game_id[0])
        return conn.execute(query)
    else:
        LOGGER.debug("Creating new game state.")

        query = active_games.insert(None).values({
            "guild_id": guild_id_fkey[0],
            "game_state": game_state.serialize(),
        })
        return conn.execute(query)


def clear_game_state(conn: Connectable, guild_id: int) -> ResultProxy:
    """Removes an existing game state from the database.

    :param c conn:
    :param int guild_id:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :type r: sqlalchemy.engine.result.ResultProxy
    :rtype: r
    :return:
    """

    query = sa.select([guilds.c.id]) \
        .where(guilds.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = active_games.delete(None) \
        .where(active_games.c.guild_id == guild_id_fkey[0])
    return conn.execute(query)
