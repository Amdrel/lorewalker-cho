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

"""Contains functions that are called when Cho commands are received."""

import logging
import re
import discord
import cho_utils
import sql.guild

CMD_START = "start"
CMD_STOP = "stop"
CMD_SCOREBOARD = "scoreboard"
CMD_SET_CHANNEL = "set-channel"
CMD_SET_PREFIX = "set-prefix"
CMD_HELP = "help"

DISCORD_CHANNEL_REGEX = re.compile("^<#([0-9]*)>$")
ALLOWED_PREFIXES = set(["!", "&", "?", "|", "^", "%"])

LOGGER = logging.getLogger("cho")


class ChoCommandsMixin():
    """Contains command handler functions for ChoClient."""

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

        args = message.content.split()
        if len(args) < 2:
            await message.channel.send(
                "You didn't specify a command. If you want to "
                "start a game use the \"start\" command."
            )
            return

        command = args[1].lower()

        if command == CMD_HELP:
            await self._handle_help(message, args, config)
            return

        # Admin commands should be processed anywhere.
        if command == CMD_SET_CHANNEL:
            await self._handle_set_channel(message, args, config)
            return
        elif command == CMD_SET_PREFIX:
            await self._handle_set_prefix(message, args, config)
            return

        # Anything not handled above must be done in the configured channel.
        if not cho_utils.is_message_from_trivia_channel(message, config):
            await message.channel.send(
                "Sorry, I can't be summoned into this channel. Please go "
                "to the trivia channel for this server."
            )
            return

        # Trivia channel-only commands.
        if command == CMD_START:
            await self._handle_start_command(message, args, config)
            return
        elif command == CMD_STOP:
            await self._handle_stop_command(message, args, config)
            return
        elif command == CMD_SCOREBOARD:
            await self._handle_scoreboard_command(message, args, config)
            return

        await message.channel.send(
            "I'm afraid I don't know that command. If you want to "
            "start a game use the \"start\" command."
        )

    async def _handle_help(self, message, args, config):
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
            value="Coming Soon!",
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

    async def _handle_start_command(self, message, args, config):
        """Starts a new game at the request of a user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if self._is_game_in_progress(message.guild.id):
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
        await self._start_game(message.guild, message.channel)

    async def _handle_stop_command(self, message, args, config):
        """Stops the current game at the request of the user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id

        if self._is_game_in_progress(guild_id):
            LOGGER.info(
                "Stopping game in guild %s, requested by %s",
                guild_id, message.author
            )
            await self._stop_game(guild_id)

            await message.channel.send(
                "I'm stopping the game for now. Maybe we can play another time?"
            )
        else:
            await message.channel.send(
                "There's no game to stop right now. If you're interested in "
                "stopping games before they end, I recommend that you start "
                "one first."
            )

    async def _handle_scoreboard_command(self, message, args, config):
        """Displays a scoreboard at the request of the user.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id
        guild = self.get_guild(guild_id)

        guild_scoreboard = sql.scoreboard.get_scoreboard(self.engine, guild_id)
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

    async def _handle_set_channel(self, message, args, config):
        """Updates the trivia channel configuration for the guild.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if len(args) < 3:
            await message.channel.send(
                "Please specify a channel when using \"set-channel\"."
            )
            return

        if not cho_utils.is_admin(message.author, message.channel):
            await message.channel.send(
                "Sorry, only administrators can move me."
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
        sql.guild.update_guild_config(self.engine, guild_id, config)

        await message.channel.send(
            "The trivia channel is now in {}.".format(trivia_channel_id)
        )

    async def _handle_set_prefix(self, message, args, config):
        """Updates the prefix used for the guild.

        :param m message:
        :param list args:
        :param dict config:
        :type m: discord.message.Message
        """

        if len(args) < 3:
            await message.channel.send(
                "Please specify a prefix when using \"set-prefix\"."
            )
            return

        if not cho_utils.is_admin(message.author, message.channel):
            await message.channel.send(
                "Sorry, only administrators can change the prefix."
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
        sql.guild.update_guild_config(self.engine, guild_id, config)

        await message.channel.send(
            "My prefix is now in \"{}\".".format(new_prefix)
        )
