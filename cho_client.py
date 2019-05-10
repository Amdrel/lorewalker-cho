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

import asyncio
import logging
import re
import discord
import cho

from game_state import GameState

SHORT_WAIT_SECS = 5
LONG_WAIT_SECS = 10

CMD_START = "start"
CMD_STOP = "stop"
CMD_SCOREBOARD = "scoreboard"
CMD_SET_CHANNEL = "set-channel"
CMD_SET_PREFIX = "set-prefix"

DISCORD_CHANNEL_REGEX = re.compile("^<#([0-9]*)>$")
ALLOWED_PREFIXES = set(["!", "&", "?", "|", "^", "%"])

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
        self.guild_configs = {}
        self.active_games = {}

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        LOGGER.info("Client logged in as \"%s\"", self.user)

    async def on_message(self, message):
        """Called whenever the bot receives a message from Discord.

        :param m message:
        :type m: discord.message.Message
        """

        # Ignore messages from self. Let's not risk going in a loop here.
        if self.user.id == message.author.id:
            return

        LOGGER.debug("Message from \"%s\": %s", message.author, message.content)

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
        game_in_progress = guild_id in self.active_games

        # Gets the configured prefix if there is one. If there isn't one a
        # default that's hardcoded is used instead.
        results = cho.get_guild(self.engine, guild_id)
        if results:
            _, config = results
            prefix = cho.get_prefix(config)
        else:
            prefix = cho.get_prefix(None)

        if cho.is_command(message, prefix):
            await self._handle_command(message)
        elif game_in_progress:
            _, config = cho.get_guild(self.engine, guild_id)

            if cho.is_message_from_trivia_channel(message, config):
                await self._process_answer(message)

    async def _handle_command(self, message):
        """Called when a Cho command is received from a user.

        :param m message:
        :type m: discord.message.Message
        """

        guild_id = message.guild.id

        # This is a good opportunity to make sure the guild we're getting a
        # command from is setup properly in the database.
        guild_query_results = cho.get_guild(self.engine, guild_id)
        if not guild_query_results:
            LOGGER.info("Got command from new guild: %s", guild_id)
            cho.create_guild(self.engine, guild_id)
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

        # Admin commands should be processed anywhere.
        if command == CMD_SET_CHANNEL:
            await self._handle_set_channel(message, args, config)
            return
        elif command == CMD_SET_PREFIX:
            await self._handle_set_prefix(message, args, config)
            return

        if not cho.is_message_from_trivia_channel(message, config):
            await message.channel.send(
                "Sorry, I can't be summoned into this channel. Please go "
                "to the trivia channel for this server."
            )
            return

        if command == CMD_START:
            await self._handle_start_command(message, args, config)
        elif command == CMD_STOP:
            await self._handle_stop_command(message, args, config)
        elif command == CMD_SCOREBOARD:
            await self._handle_scoreboard_command(message, args, config)
        else:
            await message.channel.send(
                "I'm afraid I don't know that command. If you want to "
                "start a game use the \"start\" command."
            )

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
            self._cleanup_game(guild_id)

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

        await message.channel.send(
            "Sorry, I currently don't track scores between games; however I "
            "do plan on doing this soon! Ask me again later."
        )

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

        if not cho.is_admin(message.author, message.channel):
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
        cho.update_guild_config(self.engine, guild_id, config)

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

        if not cho.is_admin(message.author, message.channel):
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
        cho.update_guild_config(self.engine, guild_id, config)

        await message.channel.send(
            "My prefix is now in \"{}\".".format(new_prefix)
        )

    async def _start_game(self, guild, channel):
        """Starts a new trivia game.

        :param g guild:
        :param c channel:
        :type g: discord.guild.Guild
        :type c: discord.channel.Channel
        """

        new_game = self._create_game(guild.id)

        await asyncio.sleep(SHORT_WAIT_SECS)
        await self._ask_question(channel, new_game)

    async def _process_answer(self, message):
        """Called when an answer is received from a user.

        :param m message:
        :type m: discord.message.Message
        """

        game_state = self._get_game(message.guild.id)

        # Don't process the answer if the bot is currently in-between asking
        # questions. Without this multiple people can get the answer right
        # rather than just the first person.
        if not game_state.waiting:
            LOGGER.debug("Ignoring answer: %s", message.content)
            return

        if game_state.check_answer(message.content):
            LOGGER.debug("Correct answer received: %s", message.content)

            user_id = message.author.id
            question = game_state.get_question()

            game_state.waiting = False
            game_state.bump_score(user_id)
            game_state.step()

            await message.channel.send(
                "Correct, <@!{user_id}>! The answer is \"{answer}\".".format(
                    user_id=user_id,
                    answer=question["answers"][0],
                ),
            )
            await asyncio.sleep(SHORT_WAIT_SECS)
            await self._ask_question(message.channel, game_state)
        else:
            LOGGER.debug("Incorrect answer received: %s", message.content)

    async def _ask_question(self, channel, game_state):
        """Asks a trivia question in a Discord channel.

        :param c channel:
        :param GameState game_state:
        :type c: discord.channel.Channel
        """

        guild_id = channel.guild.id

        # This prevents questions from being asked after a game was ended
        # through the stop command before it ended naturally.
        #
        # This check also covers the rare edge-case where a game is stopped and
        # started again within the 10 second window between questions so that
        # the trivia game doesn't duplicate itself.
        if not self._is_same_game_in_progress(guild_id, game_state):
            return

        if game_state.complete:
            await self._finish_game(channel, game_state)
            return

        question = game_state.get_question()
        last_correct_answers_total = game_state.correct_answers_total

        game_state.waiting = True
        await channel.send(question["text"])
        await asyncio.sleep(LONG_WAIT_SECS)

        # Check again as it can happen here too.
        if not self._is_same_game_in_progress(guild_id, game_state):
            return

        # If the correct answer total was not incrememnted, that means that no
        # one answered the question correctly. Give them the answer if so.
        if last_correct_answers_total == game_state.correct_answers_total:
            game_state.waiting = False
            game_state.step()

            await channel.send(
                "The correct answer was \"{answer}\".".format(
                    answer=question["answers"][0],
                ),
            )
            await asyncio.sleep(SHORT_WAIT_SECS)
            await self._ask_question(channel, game_state)

    async def _finish_game(self, channel, game_state):
        """Outputs the scoreboard and announces the winner of a game.

        :param c channel:
        :param GameState game_state:
        :type c: discord.channel.Channel
        """

        self._cleanup_game(channel.guild.id)

        score_fmt = "{emoji} <@!{user_id}> - {score} point{suffix}\n"
        scores = list(game_state.scores.items())

        # Don't bother making a scoreboard if it's going to be empty. It's
        # better to make fun of everyone for being so bad at the game instead!
        if len(scores) == 0:
            await channel.send(
                "Well it appears no one won because no one answered a "
                "*single* question right. You people really don't know much "
                "about your own world. Come back after you learn some more."
            )
            return

        scores.sort(key=lambda x: x[1], reverse=True)
        winner_user_id, highest_score = scores[0]
        ties = 0
        scoreboard = ""

        for index, data in enumerate(scores):
            user_id, score = data
            if index > 0 and score >= highest_score:
                ties += 1

            scoreboard += score_fmt.format(
                emoji=":white_check_mark:" if score >= highest_score else ":x:",
                user_id=user_id,
                score=score,
                suffix="s" if score != 0 else "",
            )

        if ties == 0:
            await channel.send(
                "Alright we're out of questions, the winner is <@!{}>!\n\n"
                "**Scoreboard**:\n{}"
                "\nThank you for playing! I hope to see you again soon."
                .format(winner_user_id, scoreboard)
            )
        else:
            await channel.send(
                "Alright we're out of questions, it seems to be a {}-way tie!\n\n"
                "**Scoreboard**:\n{}"
                "\nThank you for playing! I hope to see you again soon."
                .format(str(ties + 1), scoreboard)
            )

    def _cleanup_game(self, guild_id):
        """Removes the game state of a guild from memory.

        :param int guild_id:
        """

        del self.active_games[guild_id]

    def _get_game(self, guild_id):
        """Retrieves a guild's game state from memory.

        :param int guild_id:
        :rtype: GameState
        :return:
        """

        return self.active_games[guild_id]

    def _create_game(self, guild_id):
        """Creates a new game state.

        :param int guild_id:
        :rtype: GameState
        :return:
        """

        new_game = GameState(self.engine, guild_id)
        self.active_games[guild_id] = new_game
        return new_game

    def _is_game_in_progress(self, guild_id):
        """Checks if a game is in progress for a guild.

        :param int guild_id:
        :rtype: bool
        :return:
        """

        return guild_id in self.active_games

    def _is_same_game_in_progress(self, guild_id, game_state):
        """Checks if the game of the specified game state is running.

        :param int guild_id:
        :param GameState game_state:
        :rtype: bool
        :return:
        """

        return (
            self._is_game_in_progress(guild_id)
            and self._get_game(guild_id).uuid == game_state.uuid
        )
