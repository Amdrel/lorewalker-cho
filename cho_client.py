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
import cho

LOGGER = logging.getLogger("cho")


class ChoClient(discord.Client):
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
        self.active_games = {}

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        LOGGER.info("Client logged in as \"%s\"", self.user)

    async def on_message(self, message):
        """Called whenever the bot receives a message from Discord.

        :param m message:
        :type m: discord.message.Message
        """

        LOGGER.info("Message from \"%s\": %s", message.author, message.content)

        if message.guild is None:
            await message.channel.send(
                "Oh hello there, I don't currently do private trivia "
                "sessions. If you want to start a game, call for me in a "
                "Discord server."
            )
            return

        # TODO: Get prefix from the configuration.
        prefix = "!"
        game_in_progress = message.guild.id in self.active_games

        if cho.is_command(message, prefix):
            self.handle_command(message)
        elif game_in_progress and cho.is_message_from_trivia_channel(message):
            self.handle_answer(message)

    async def handle_command(self, message):
        """Called when a Cho command is received from a user."""

        if not cho.is_message_from_trivia_channel(message):
            await message.channel.send(
                "Sorry, I can't be summoned into this channel. Please go "
                "to the trivia channel for this server."
            )
            return

        args = message.content.split()
        if len(args) > 1 and args[1].lower() == "start":
            LOGGER.info(
                "Starting game in guild %s, requested by %s",
                message.guild.id, message.author
            )

    async def handle_answer(self, message):
        """Called when an answer is received from a user."""

        pass
