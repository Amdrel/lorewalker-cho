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

"""Contains logic for the trivia game in Cho."""

import asyncio
import logging
import cho_utils
import sql.guild
import sql.scoreboard

from discord.channel import TextChannel
from discord.guild import Guild
from discord.message import Message
from game_state import GameState

SHORT_WAIT_SECS = 5
LONG_WAIT_SECS = 30

LOGGER = logging.getLogger("cho")


class ChoGameMixin():
    """Adds trivia game logic to ChoClient. Gotta love compartmentalization."""

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

        if cho_utils.is_message_from_trivia_channel(message, config):
            await self._process_answer(message)

    async def resume_incomplete_games(self):
        """Resumes all inactive games, usually caused by the bot going down."""

        incomplete_games = sql.active_game.get_incomplete_games(self.engine)

        LOGGER.info(
            "Found %d incomplete games that need to be resumed",
            len(incomplete_games))

        for guild_id, active_game_dict in incomplete_games:
            existing_game_state = GameState(
                self.engine,
                guild_id,
                active_game_dict=active_game_dict,
                save_to_db=True)
            self.active_games[guild_id] = existing_game_state

            guild = self.get_guild(guild_id)

            if guild:
                channel = guild.get_channel(existing_game_state.channel_id)
                asyncio.ensure_future(
                    self._ask_question(channel, existing_game_state))

    async def _start_game(self, guild: Guild, channel: TextChannel):
        """Starts a new trivia game.

        :param g guild:
        :param c channel:
        :type g: discord.guild.Guild
        :type c: discord.channel.TextChannel
        """

        new_game = self._create_game(guild.id, channel.id)

        await asyncio.sleep(SHORT_WAIT_SECS)
        await self._ask_question(channel, new_game)

    async def _stop_game(self, guild_id: int):
        """Stops a game in progress for a guild.

        :param int guild_id:
        """

        game_state = self._get_game(guild_id)
        game_state.stop_game()

        self._cleanup_game(guild_id)

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

        guild_id = channel.guild.id
        self._cleanup_game(guild_id)

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

        guild_scoreboard = sql.scoreboard.get_scoreboard(self.engine, guild_id)
        if not guild_scoreboard:
            guild_scoreboard = {}
        else:
            guild_scoreboard = guild_scoreboard[0]

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

            # Update the guild's scoreboard score for the current user. The
            # score may not exist so default to zero.
            guild_member_score = guild_scoreboard.get(str(user_id), 0)
            guild_member_score += score
            guild_scoreboard[str(user_id)] = guild_member_score

        sql.scoreboard.save_scoreboard(self.engine, guild_id, guild_scoreboard)

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

    def _cleanup_game(self, guild_id: int):
        """Removes the game state of a guild from memory.

        :param int guild_id:
        """

        del self.active_games[guild_id]

    def _get_game(self, guild_id: int) -> GameState:
        """Retrieves a guild's game state from memory.

        :param int guild_id:
        :rtype: GameState
        :return:
        """

        return self.active_games[guild_id]

    def _create_game(self, guild_id: int, channel_id: int) -> GameState:
        """Creates a new game state.

        :param int guild_id:
        :param int channel_id:
        :rtype: GameState
        :return:
        """

        new_game = GameState(
            self.engine,
            guild_id,
            channel_id=channel_id,
            save_to_db=True)
        self.active_games[guild_id] = new_game
        return new_game

    def _is_game_in_progress(self, guild_id: int) -> bool:
        """Checks if a game is in progress for a guild.

        :param int guild_id:
        :rtype: bool
        :return:
        """

        return guild_id in self.active_games

    def _is_same_game_in_progress(
            self,
            guild_id: int,
            game_state: GameState) -> bool:
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
