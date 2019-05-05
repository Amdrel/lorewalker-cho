"""Contains logic for mutating game states."""

import json
import cho

CURRENT_REVISION = 0


class GameState():
    """Python class representing a Cho game state."""

    def __init__(self, active_game_json):
        """Converts a JSON representation of a game state into an object.

        :param str active_game_json:
        """

        active_game_dict = json.loads(active_game_json)

        self.revision = active_game_dict["revision"]
        self.questions = active_game_dict["questions"]
        self.current_question = active_game_dict["current_question"]
        self.complete = active_game_dict["complete"]
        self.scores = active_game_dict["scores"]
        self.channel_id = active_game_dict["channel_id"]

        self.correct_answers_total = 0

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
            "channel_id": self.channel_id,
        })

    def step(self):
        """Advances the game forward."""

        self.current_question += 1

        if len(self.current_question) >= len(self.questions):
            self.complete_game()

    def complete_game(self):
        """Completes the game and determines the winner."""

        self.complete = True

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

        question = self._get_question()

        for correct_answer in question["answers"]:
            answer_ratio = cho.levenshtein_ratio(answer, correct_answer)
            if answer_ratio >= ratio:
                return True

        return False

    def bump_score(self, discord_user_id, amount=1):
        """Increases the score of a player by an amount."""

        user_score = self.scores.get(discord_user_id, 0)
        self.scores[discord_user_id] = user_score + amount

    def _get_question(self):
        """Returns the current question."""

        return self.questions[self.current_question]
