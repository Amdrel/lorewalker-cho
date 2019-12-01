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

"""Contains logic for mutating game states."""

import copy
import random
import uuid

from sqlalchemy.engine import Engine

import lorewalker_cho.utils as utils
import lorewalker_cho.sql.active_game as sql_active_game

from lorewalker_cho.data.questions import DEFAULT_QUESTIONS

CURRENT_REVISION = 0


class GameState():
    """Python class representing a Cho game state."""

    def __init__(
            self,
            engine: Engine,
            guild_id: int,
            channel_id: int = None,
            existing_game: dict = None,
            save_to_db=False):
        """Converts a game state dict into an object.

        :param e engine:
        :param int guild_id:
        :param int channel_id:
        :param dict existing_game:
        :param bool save_to_db:
        :type e: sqlalchemy.engine.Engine
        """

        self.engine = engine
        self.guild_id = guild_id
        self.save_to_db = save_to_db

        if existing_game:
            if CURRENT_REVISION != existing_game["revision"]:
                raise ValueError("GameState revision mismatch.")

            self.revision = CURRENT_REVISION
            self.questions = existing_game["questions"]
            self.current_question = existing_game["current_question"]
            self.complete = existing_game["complete"]
            self.scores = existing_game["scores"]
            self.channel_id = existing_game["channel_id"]
        else:
            self.revision = CURRENT_REVISION
            self.questions = self.__select_questions(DEFAULT_QUESTIONS)
            self.current_question = 0
            self.complete = False
            self.scores = {}

            if channel_id is not None:
                self.channel_id = channel_id
            else:
                raise TypeError("Field channel_id is required for GameState.")

        self.uuid = uuid.uuid4()
        self.correct_answers_total = 0
        self.waiting = False

        if self.save_to_db:
            sql_active_game.save_game_state(self.engine, self)

    @staticmethod
    def __select_questions(questions: list, count=10) -> list:
        """Selects a bunch of random questions for a trivia session.

        :param list questions:
        :param int count:
        """

        cloned_questions = copy.deepcopy(questions)
        random.shuffle(cloned_questions)

        return cloned_questions[:count]

    def __complete_game(self):
        """Completes the game and determines the winner."""

        self.complete = True

    def serialize(self) -> str:
        """Converts the game state object into JSON so it an be stored.

        :rtype: str
        :return: JSON representation of the state that can be used for storage.
        """

        return {
            "revision": CURRENT_REVISION,
            "questions": self.questions,
            "current_question": self.current_question,
            "complete": self.complete,
            "scores": self.scores,
            "channel_id": self.channel_id,
        }

    def stop_game(self):
        """Stops a game in progress."""

        self.__complete_game()

        if self.save_to_db:
            sql_active_game.save_game_state(self.engine, self)

    def step(self):
        """Advances the game forward to the next question.

        This function will check if the game is complete and ensure the
        active game state is saved to the database as it's likely the game
        state was mutated before this function was called.
        """

        self.current_question += 1

        if self.current_question >= len(self.questions):
            self.__complete_game()

        if self.save_to_db:
            sql_active_game.save_game_state(self.engine, self)

    def bump_score(self, user_id: int, amount=1):
        """Increases the score of a player by an amount.

        :param int user_id:
        :param int amount:
        """

        user_score = self.scores.get(str(user_id), 0)

        self.scores[str(user_id)] = user_score + amount
        self.correct_answers_total += 1

    def check_answer(self, answer: str, ratio=0.8) -> bool:
        """Checks an answer for correctness.

        Any answers that fall below the given ratio are incorrect, while any
        that are equal to or above are correct. The ratio is compared to the
        levenshtein ratio of the answer and the current question's answer.
        This allows for some degree of misspelling.

        :param str answer:
        :param float ratio:
        :rtype: bool
        :return: True if correct, false otherwise.
        """

        question = self.get_question()

        for correct_answer in question["answers"]:
            answer_ratio = utils.levenshtein_ratio(answer, correct_answer)
            if answer_ratio >= ratio:
                return True

        return False

    def get_question(self) -> dict:
        """Returns the current question."""

        return self.questions[self.current_question]
