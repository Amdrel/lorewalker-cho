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

"""Contains the Discord client class for Cho."""

import asyncio
import logging
import shlex
import traceback

from commands import CommandsMixin

import discord
import redis

from discord.message import Message
from redis import Redis
from sqlalchemy.engine import Engine

import utils
import sql.guild

from game import GameMixin

LOGGER = logging.getLogger("cho")


class LorewalkerCho(CommandsMixin, GameMixin, discord.Client):
    """Discord client wrapper that uses functionality from cho.py."""

    def __init__(self, engine: Engine, redis_client: Redis):
        """Initializes the ChoClient with a sqlalchemy connection pool.

        :param e engine: SQLAlchemy engine to make queries with.
        :param r redis_client: A redis client for caching non-persistant data.
        :type e: sqlalchemy.engine.Engine
        :type r: redis.Redis
        :rtype: LorewalkerCho
        :return:
        """

        super().__init__()

        self.engine = engine
        self.redis = redis_client
        self.guild_configs = {}
        self.active_games = {}

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        LOGGER.info("Client logged in as \"%s\"", self.user)

        await self.set_status()

        asyncio.ensure_future(self.resume_incomplete_games())

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
            prefix = utils.get_prefix(config)
        else:
            prefix = utils.get_prefix(None)

        if utils.is_command(message, prefix):
            await self.handle_command(message)
        elif self.is_game_in_progress(guild_id):
            await self.handle_message_response(message)

    async def on_error(self, event_name, *args, **kwargs):
        """Logs exceptions to the bot's log."""

        stack_trace = traceback.format_exc()
        LOGGER.error("Received uncaught exception:\n\n%s", stack_trace)

    async def handle_command(self, message):
        """Called when a Cho command is received from a user.

        :param m message:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id

        # This is a good opportunity to make sure the guild we're getting a
        # command from is setup properly in the database.
        guild_query_results = sql.guild.get_guild(self.engine, guild_id)
        if not guild_query_results:
            LOGGER.info("Got command from new guild: %s", guild_id)
            sql.guild.create_guild(self.engine, guild_id)
            config = {}
        else:
            _, config = guild_query_results

        # Split arguments as if they're in a shell-like syntax using shlex.
        # This allows for arguments to be quoted so strings with spaces can be
        # included.
        args = shlex.split(message.content)

        # Handle cho invocations with no command.
        if len(args) < 2:
            await message.channel.send(
                "You didn't specify a command. If you want to "
                "start a game use the \"start\" command."
            )
            return

        command = args[1].lower()

        # Process commands that are marked for global usage.
        for global_command, func in utils.GLOBAL_COMMANDS.items():
            if global_command == command:
                await func(self, message, args, config)
                return

        # Anything not handled above must be done in the configured channel.
        if not utils.is_message_from_trivia_channel(message, config):
            await message.channel.send(
                "Sorry, I can't be summoned into this channel. Please go "
                "to the trivia channel for this server."
            )
            return

        # Process commands that are marked for channel-only usage.
        for channel_command, func in utils.CHANNEL_COMMANDS.items():
            if channel_command == command:
                await func(self, message, args, config)
                return

        await message.channel.send(
            "I'm afraid I don't know that command. If you want to "
            "start a game use the \"start\" command."
        )

    async def handle_message_response(self, message: Message):
        """Processes a non-command message received during an active game.

        :param m message:
        :type m: discord.message.Message
        """

        guild_id = guild_id = message.guild.id

        guild_query_results = sql.guild.get_guild(self.engine, guild_id)
        if guild_query_results:
            _, config = guild_query_results
        else:
            config = {}

        if utils.is_message_from_trivia_channel(message, config):
            await self.process_answer(message)

    async def set_status(self):
        """Sets the bot status to the saved one, or the default if missing."""

        status = "!cho help"

        try:
            saved_status = self.redis.get("cho:status")
            if saved_status:
                status = saved_status.decode()
        except redis.ConnectionError as exc:
            LOGGER.warning(exc)

        LOGGER.debug("Setting status to \"%s\"", status)

        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=status))
