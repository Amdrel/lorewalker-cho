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

"""Core code that controls Cho's behavior."""

import asyncio
import logging
import jellyfish
import sqlalchemy as sa

from game_state import GameState
from schema import guilds, active_games

LOGGER = logging.getLogger("cho")


def get_guild(conn, guild_id):
    """Retrieves config guild information."""

    query = sa.select([guilds.c.discord_guild_id, guilds.c.config]) \
        .where(guilds.c.discord_guild_id == guild_id) \
        .limit(1)
    return conn.execute(query).first()


def create_guild(conn, guild_id, config={}):
    """Ensures a specified Discord guild is in the database."""

    query = guilds.insert(None).values({
        "discord_guild_id": guild_id,
        "config": config,
    })
    return conn.execute(query)


def update_guild_config(conn, guild_id, config):
    """Updates an existing guild's configuration."""

    query = guilds.update(None).values({
        "config": config,
    }).where(guilds.c.discord_guild_id == guild_id)
    return conn.execute(query)


def get_game_state(conn, guild_id):
    """Retrieves an existing game state."""

    query = sa.select([guilds.c.id]) \
        .where(guilds.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = sa.select([active_games.c.game_state]) \
        .where(active_games.c.guild_id == guild_id_fkey[0]) \
        .limit(1)
    return conn.execute(query).first()


def save_game_state(conn, game_state):
    """Saves a game state to the database."""

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


def clear_game_state(conn, guild_id):
    """Removes an existing game state from the database."""

    query = sa.select([guilds.c.id]) \
        .where(guilds.c.discord_guild_id == guild_id) \
        .limit(1)
    guild_id_fkey = conn.execute(query).first()

    query = active_games.delete(None) \
        .where(active_games.c.guild_id == guild_id_fkey[0])
    return conn.execute(query)


def is_command(message, prefix):
    """Checks if a Discord message is a Cho command invocation."""

    return (
        message.content.startswith("{}cho".format(prefix))
        or message.content.startswith("{}trivia".format(prefix))
    )


def is_message_from_trivia_channel(message, config):
    """Checks if the message is from the trivia channel."""

    if "trivia_channel" in config:
        return message.channel.id == config["trivia_channel"]
    else:
        return message.channel.name == "trivia"


def levenshtein_ratio(source, target, ignore_case=True):
    """Calculates the levenshtein ratio between two strings.

    The ratio is computed as follows:
        (len(source) + len(target) - distance) / (len(source) + len(target))

    This function has been ported from (MIT license):
        https://github.com/texttheater/golang-levenshtein/blob/4041401c6e7f6a2b49815c4aea652e518ca8e92e/levenshtein/levenshtein.go#L115-L130

    :param str source:
    :param str target:
    :rtype: float
    :return:
    """

    if ignore_case:
        distance = jellyfish.levenshtein_distance(
            source.lower().strip(),
            target.lower().strip()
        )
    else:
        distance = jellyfish.levenshtein_distance(source, target)

    source_len = len(source)
    target_len = len(target)

    return (source_len + target_len - distance) / (source_len + target_len)
