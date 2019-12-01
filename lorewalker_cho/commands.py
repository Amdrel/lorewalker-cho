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

"""Contains functions that are called when Cho commands are received."""

import logging
import re

import discord
import redis

import lorewalker_cho.sql.guild as sql_guild
import lorewalker_cho.sql.scoreboard as sql_scoreboard

from lorewalker_cho.utils import cho_command

CMD_HELP = "help"
CMD_SCOREBOARD = "scoreboard"
CMD_SET_CHANNEL = "set-channel"
CMD_SET_PREFIX = "set-prefix"
CMD_SET_STATUS = "set-status"
CMD_START = "start"
CMD_STOP = "stop"

DISCORD_CHANNEL_REGEX = re.compile(r"^<#([0-9]*)>$")
ALLOWED_PREFIXES = {"!", "&", "?", "|", "^", "%"}

LOGGER = logging.getLogger("cho")


class CommandsMixin():
    """Contains command handler functions for ChoClient."""

    @cho_command(CMD_HELP)
    async def handle_help(self, message, args, config):
        """Responds with help to teach users about the bot's functions.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        embed = discord.Embed(
            title="Lorewalker Cho Commands",
            description="Commands are typed as such: !cho 'command'",
            color=discord.Color(0xf5f117))
        embed.add_field(
            name=CMD_HELP,
            value="Shows the help information, you know, the stuff you're "
                  "currently reading.",
            inline=True)
        embed.add_field(
            name=CMD_START,
            value="Starts a new trivia game.",
            inline=True)
        embed.add_field(
            name=CMD_STOP,
            value="Stops the currently running trivia game.",
            inline=True)
        embed.add_field(
            name=CMD_SCOREBOARD,
            value="Shows the server's scoreboard which shows all points "
                  "earned by members of the server.",
            inline=True)
        embed.add_field(
            name=CMD_SET_CHANNEL,
            value="Changes the channel that the bot hosts trivia games in. "
                  "Server admins only.",
            inline=True)
        embed.add_field(
            name=CMD_SET_PREFIX,
            value="Changes the prefix used to summon Cho. Server admins only.",
            inline=True)
        embed.set_footer(text="Lorewalker Cho")

        await message.channel.send(
            "Nice to meet you, <@!{user_id}>. Here's all of the things you "
            "can ask me to do!"
            .format(
                user_id=message.author.id
            )
        )
        await message.channel.send(embed=embed)

    @cho_command(CMD_START, kind="channel")
    async def handle_start_command(self, message, args, config):
        """Starts a new game at the request of a user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if self.is_game_in_progress(message.guild.id):
            await message.channel.send(
                "A game is already active in the trivia channel. If you "
                "want to participate please go in there."
            )
            return

        LOGGER.info(
            "Starting game in guild %s, requested by %s",
            message.guild.id, message.author
        )
        await message.channel.send(
            "Okay I'm starting a game. Don't expect me to go easy."
        )
        await self.start_game(message.guild, message.channel)

    @cho_command(CMD_STOP, kind="channel")
    async def handle_stop_command(self, message, args, config):
        """Stops the current game at the request of the user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id

        if self.is_game_in_progress(guild_id):
            LOGGER.info(
                "Stopping game in guild %s, requested by %s",
                guild_id, message.author
            )
            await self.stop_game(guild_id)

            await message.channel.send(
                "I'm stopping the game for now. Maybe we can play another time?"
            )
        else:
            await message.channel.send(
                "There's no game to stop right now. If you're interested in "
                "stopping games before they end, I recommend that you start "
                "one first."
            )

    @cho_command(CMD_SCOREBOARD, kind="channel")
    async def handle_scoreboard_command(self, message, args, config):
        """Displays a scoreboard at the request of the user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id
        guild = self.get_guild(guild_id)

        guild_scoreboard = sql_scoreboard.get_scoreboard(self.engine, guild_id)
        if not guild_scoreboard:
            guild_scoreboard = {}
        else:
            guild_scoreboard = guild_scoreboard[0]

        scoreboard_message = "Here is the scoreboard for this server:\n"
        score_count = 0

        for user_id, score in guild_scoreboard.items():
            member = guild.get_member(int(user_id))
            if not member:
                continue

            if score != 1:
                plural = "s"
            else:
                plural = ""

            scoreboard_message += "\n- **{}**: {} point{}".format(
                member.display_name, score, plural)
            score_count += 1

        if score_count > 0:
            await message.channel.send(scoreboard_message)
        else:
            await message.channel.send(
                "Currently no scores are available. Try playing a game to "
                "get some scores in the scoreboard.")

    @cho_command(CMD_SET_CHANNEL, admin_only=True)
    async def handle_set_channel(self, message, args, config):
        """Updates the trivia channel configuration for the guild.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if len(args) < 3:
            await message.channel.send(
                f"Please specify a channel when using \"{CMD_SET_CHANNEL}\"."
            )
            return

        guild_id = message.guild.id
        trivia_channel_id = args[2]
        trivia_channel_re_match = DISCORD_CHANNEL_REGEX.match(
            trivia_channel_id
        )

        if not trivia_channel_re_match:
            await message.channel.send(
                "That doesn't look like a channel to me. Please try again."
            )
            return

        config["trivia_channel"] = int(trivia_channel_re_match.group(1))
        sql_guild.update_guild_config(self.engine, guild_id, config)

        await message.channel.send(
            "The trivia channel is now in {}.".format(trivia_channel_id)
        )

    @cho_command(CMD_SET_PREFIX, admin_only=True)
    async def handle_set_prefix(self, message, args, config):
        """Updates the prefix used for the guild.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if len(args) < 3:
            await message.channel.send(
                f"Please specify a prefix when using \"{CMD_SET_PREFIX}\"."
            )
            return

        guild_id = message.guild.id
        new_prefix = args[2]

        if new_prefix not in ALLOWED_PREFIXES:
            await message.channel.send(
                "Sorry, that's not a supported prefix for me. Please try "
                "another one."
            )
            return

        config["prefix"] = new_prefix
        sql_guild.update_guild_config(self.engine, guild_id, config)

        await message.channel.send(f"My prefix is now \"{new_prefix}\".")

    @cho_command(CMD_SET_STATUS, owner_only=True)
    async def handle_set_status(self, message, args, config):
        """Updates the bot's status across all shards.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if len(args) < 3:
            await message.channel.send(
                f"Please specify a status when using \"{CMD_SET_STATUS}\"."
            )
            return
        elif len(args) > 3:
            await message.channel.send(
                f"Too many arguments for \"{CMD_SET_STATUS}\". Surround your "
                f"status with double quotes to include spaces."
            )
            return

        new_status = args[2]

        try:
            self.redis.set("cho:status", new_status)
            await self.set_status()
        except redis.ConnectionError as exc:
            LOGGER.warning(exc)

            await message.channel.send(
                "Unable to set status due to a redis connection error."
            )
        else:
            await message.channel.send(f"My status is now \"{new_status}\".")
