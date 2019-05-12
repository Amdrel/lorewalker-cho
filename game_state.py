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

"""Contains logic for mutating game states."""

import copy
import json
import random
import uuid
import cho_utils
import sql.game_state

from data.questions import DEFAULT_QUESTIONS

CURRENT_REVISION = 0


class GameState():
    """Python class representing a Cho game state."""

    def __init__(self, engine, guild_id, active_game_dict=None):
        """Converts a game state dict into an object.

        :param e engine:
        :param int guild_id:
        :param dict active_game_dict:
        :type e: sqlalchemy.engine.Engine
        """

        self.engine = engine
        self.guild_id = guild_id

        if active_game_dict:
            if CURRENT_REVISION != active_game_dict["revision"]:
                raise ValueError("GameState revision mismatch.")

            self.revision = CURRENT_REVISION
            self.questions = active_game_dict["questions"]
            self.current_question = active_game_dict["current_question"]
            self.complete = active_game_dict["complete"]
            self.scores = active_game_dict["scores"]
        else:
            self.revision = CURRENT_REVISION
            self.questions = self._select_questions(DEFAULT_QUESTIONS)
            self.current_question = 0
            self.complete = False
            self.scores = {}

        self.uuid = uuid.uuid4()
        self.correct_answers_total = 0
        self.waiting = False

    def _select_questions(self, questions, count=3):
        """Selects a bunch of random questions for a trivia session.

        :param list questions:
        :param int count:
        """

        cloned_questions = copy.deepcopy(questions)
        random.shuffle(cloned_questions)

        return cloned_questions[:count]

    def _complete_game(self):
        """Completes the game and determines the winner."""

        self.complete = True

    def serialize(self):
        """Converts the game state object into JSON so it an be stored.

        :rtype: str
        :return: JSON representation of the state that can be used for storage.
        """

        return json.dumps({
            "revision": CURRENT_REVISION,
            "questions": self.questions,
            "current_question": self.current_question,
            "complete": self.complete,
            "scores": self.scores,
        })

    def step(self):
        """Advances the game forward."""

        self.current_question += 1

        if self.current_question >= len(self.questions):
            self._complete_game()

        sql.game_state.save_game_state(self.engine, self)

    def check_answer(self, answer, ratio=0.8):
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
            answer_ratio = cho_utils.levenshtein_ratio(answer, correct_answer)
            if answer_ratio >= ratio:
                return True

        return False

    def bump_score(self, user_id, amount=1):
        """Increases the score of a player by an amount.

        :param int user_id:
        :param int amount:
        """

        user_score = self.scores.get(user_id, 0)
        self.scores[user_id] = user_score + amount
        self.correct_answers_total += 1

    def get_question(self):
        """Returns the current question."""

        return self.questions[self.current_question]
