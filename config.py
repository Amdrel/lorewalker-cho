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

"""Contains helper functions to get configuration data for the worker."""

import logging
import os


def get_postgres_url():
    """Generate a database connection url for sqlalchemy.

    :rtype str:
    :return:
    """

    return "postgresql+psycopg2://:@/{dbname}?host={host}".format(
        dbname=os.environ["CHO_PG_DATABASE"], host=os.environ["CHO_PG_HOST"]
    )


def setup_logging(debug=False):
    """Setup text logging for the bot.

    :param bool debug:
    """

    logging.basicConfig(format="%(asctime)-15s [%(levelname)s] %(message)s")
    logger = logging.getLogger("cho")

    if debug:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")
