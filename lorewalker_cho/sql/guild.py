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

"""Contains CRUD functions for guilds in postgres."""

import sqlalchemy as sa

from sqlalchemy.engine.interfaces import Connectable
from sqlalchemy.engine.result import ResultProxy

from lorewalker_cho.sql.schema import GUILDS


def get_guild(conn: Connectable, guild_id: int) -> tuple:
    """Retrieves config guild information.

    :param c conn:
    :param int guild_id:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :rtype: tuple
    :return:
    """

    query = sa.select([GUILDS.c.discord_guild_id, GUILDS.c.config]) \
        .where(GUILDS.c.discord_guild_id == guild_id) \
        .limit(1)
    return conn.execute(query).first()


def create_guild(
        conn: Connectable,
        guild_id: int,
        config: dict = None) -> ResultProxy:
    """Ensures a specified Discord guild is in the database.

    :param c conn:
    :param int guild_id:
    :param dict config:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :type r: sqlalchemy.engine.result.ResultProxy
    :rtype: r
    :return:
    """

    query = GUILDS.insert(None).values({
        "discord_guild_id": guild_id,
        "config": config or {},
    })
    return conn.execute(query)


def update_guild_config(
        conn: Connectable,
        guild_id: int,
        config: dict = None) -> ResultProxy:
    """Updates an existing guild's configuration.

    :param c conn:
    :param int guild_id:
    :param dict config:
    :type c: sqlalchemy.engine.interfaces.Connectable
    :type r: sqlalchemy.engine.result.ResultProxy
    :rtype: r
    :return:
    """

    query = GUILDS.update(None).values({
        "config": config or {},
    }).where(GUILDS.c.discord_guild_id == guild_id)
    return conn.execute(query)
