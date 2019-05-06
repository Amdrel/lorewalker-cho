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
import jellyfish
import sqlalchemy as sa

from schema import guilds, active_games


# async def game_loop(discord_client, guild_id, config):
#     """The game loop for any particular game in progress."""

#     game_state = get_game_state(discord_client.engine, guild_id)

#     while not game_state.complete:
#         await asyncio.sleep(10)

#         with discord_client.engine.begin() as conn:
#             game_state.step()


def save_game_state(conn, guild_pk, guild_id, game_state):
    """Saves a game state to the database."""

    query = active_games.insert(None).values({
        "guild_id": guild_id,
        "game_state": guild_id,
    })
    return conn.execute(query)


def get_game_state(conn, guild_id):
    """Retrieves an existing game state."""

    query = active_games \
        .select([guilds.c.game_state]) \
        .where(guilds.c.guild_id == guild_id) \
        .limit(1)
    return conn.execute(query).first()


def clear_game_state(conn, guild_id):
    """Removes an existing game state from the database."""

    query = active_games.delete(None).where(guilds.c.guild_id == guild_id)
    return conn.execute(query)


def get_guild(conn, guild_id, config):
    """Retrieves config guild information."""

    query = active_games \
        .select([guilds.c.game_state]) \
        .where(guilds.c.guild_id == guild_id) \
        .limit(1)
    return conn.execute(query).first()


def create_guild(conn, guild_id, config):
    """Ensures a specified Discord guild is in the database."""

    query = guilds.insert(None).values({
        "discord_guild_id": guild_id,
        "config": config,
    })
    return conn.execute(query)


def is_command(message, prefix):
    """Checks if a Discord message is a Cho command invocation."""

    return (
        message.content.startswith("{}cho".format(prefix))
        or message.content.startswith("{}trivia".format(prefix))
    )


def is_message_from_trivia_channel(message):
    """Checks if the message is from the trivia channel."""

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
