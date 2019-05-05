#!/usr/bin/env python3
#
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

"""Command-line interface to start cho."""

import argparse
import logging
import os
import sqlalchemy as sa
import config

from cho_client import ChoClient

DISCORD_TOKEN = os.environ["CHO_DISCORD_TOKEN"]
SQLALCHEMY_POOL_SIZE = int(os.environ.get("SQLALCHEMY_POOL_SIZE", 6))
SQLALCHEMY_POOL_MAX = int(os.environ.get("SQLALCHEMY_POOL_MAX", 10))

LOGGER = logging.getLogger("cho")


def main():
    """Entrypoint for Cho on the CLI."""

    parser = argparse.ArgumentParser(description="Start a Cho Trivia worker.")
    args = parser.parse_args()

    config.setup_logging()

    LOGGER.info("Starting Cho Trivia worker")

    # Connect to the postgres database and setup connection pools.
    sqlalchemy_url = config.get_postgres_url()
    engine = sa.create_engine(
        sqlalchemy_url,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLALCHEMY_POOL_MAX
    )
    engine.connect()
    LOGGER.info("Started connection pool with size: %d", SQLALCHEMY_POOL_SIZE)

    discord_client = ChoClient(engine)
    discord_client.run(DISCORD_TOKEN)
    LOGGER.info("Shutting down... good bye!")


if __name__ == "__main__":
    main()
