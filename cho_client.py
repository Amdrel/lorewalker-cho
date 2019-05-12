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

"""Contains the Discord client class for Cho."""

import logging
import discord

from discord.message import Message

import cho_utils
import sql.guild

from cho_commands import ChoCommandsMixin
from cho_game import ChoGameMixin

LOGGER = logging.getLogger("cho")


class ChoClient(ChoCommandsMixin, ChoGameMixin, discord.Client):
    """Discord client wrapper that uses functionality from cho.py."""

    def __init__(self, engine):
        """Initializes the ChoClient with a sqlalchemy connection pool.

        :param e engine: SQLAlchemy engine to make queries with.
        :type e: sqlalchemy.engine.Engine
        :rtype: ChoClient
        :return:
        """

        super().__init__()

        self.engine = engine
        self.guild_configs = {}
        self.active_games = {}

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        LOGGER.info("Client logged in as \"%s\"", self.user)

    async def on_message(self, message: Message):
        """Called whenever the bot receives a message from Discord.

        :param m message:
        :type m: discord.message.Message
        """

        # Ignore messages from self. Let's not risk going in a loop here.
        if self.user.id == message.author.id:
            return

        LOGGER.debug(
            "Message from \"%s\": %s",
            message.author, message.content
        )

        # Don't accept direct messages at this time. I might circle back later
        # and add support for private trivia sessions, but it's not a priority
        # for me right now.
        if message.guild is None:
            await message.channel.send(
                "Oh hello there, I don't currently do private trivia "
                "sessions. If you want to start a game, call for me in a "
                "Discord server."
            )
            return

        guild_id = message.guild.id

        # Gets the configured prefix if there is one. If there isn't one a
        # default that's hardcoded is used instead.
        results = sql.guild.get_guild(self.engine, guild_id)
        if results:
            _, config = results
            prefix = cho_utils.get_prefix(config)
        else:
            prefix = cho_utils.get_prefix(None)

        if cho_utils.is_command(message, prefix):
            await self.handle_command(message)
        elif self._is_game_in_progress(guild_id):
            await self.handle_message_response(message)
