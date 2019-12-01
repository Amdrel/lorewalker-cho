#!/usr/bin/env python3
#
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
#
# pylint: disable=wrong-import-position

"""Command-line interface to start cho."""

import argparse
import logging
import os
import sys

import discord
import redis
import sqlalchemy as sa

PARENT_PATH = os.path.dirname((os.path.dirname(os.path.realpath(__file__))))
sys.path.append(PARENT_PATH)

import lorewalker_cho.config as config

from lorewalker_cho.bot import build_client

DISCORD_TOKEN = os.environ["CHO_DISCORD_TOKEN"]
SQLALCHEMY_POOL_SIZE = int(os.environ.get("SQLALCHEMY_POOL_SIZE", 6))
SQLALCHEMY_POOL_MAX = int(os.environ.get("SQLALCHEMY_POOL_MAX", 10))

LOGGER = logging.getLogger("cho")


def main():
    """Entrypoint for Cho on the CLI."""

    parser = argparse.ArgumentParser(
        description="Start a Lorewalker Cho worker.")
    parser.add_argument(
        "-d", "--debug", action='store_true', default=False,
        help="Enable debug logging.")
    parser.add_argument(
        "-l", "--log", help="Specify a log file path to log to.")
    parser.add_argument(
        "--autoshard", action='store_true', default=False,
        help="Enable autosharding")
    parser.add_argument(
        "-c", "--shard-count", default=1,
        help="Number of shards for sharding.")
    parser.add_argument(
        "-s", "--shard-id", default=0, help="Discord shard id.")
    args = parser.parse_args()

    config.setup_logging(debug=args.debug, logpath=args.log)

    LOGGER.info(
        "Starting Lorewalker Cho worker (%s)",
        ("autosharded" if args.autoshard
         else "shard {}".format(
             args.shard_id if args.shard_id is not None else "?")))
    LOGGER.debug("Debug logging activated.")

    # Connect to the postgres database and setup connection pools.
    sqlalchemy_url = config.get_postgres_url()
    engine = sa.create_engine(
        sqlalchemy_url,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLALCHEMY_POOL_MAX
    )
    engine.connect()
    LOGGER.info("Started connection pool with size: %d", SQLALCHEMY_POOL_SIZE)

    redis_url = os.environ.get("CHO_REDIS_URL") or "redis://localhost:6379"
    redis_client = redis.Redis.from_url(redis_url)

    # We use a special function called 'build_client' that will dynamically set
    # the base class of our bot's client class. We need to do this to make
    # autosharding configurable as that's controlled by a separate class.
    base_class = (
        discord.AutoShardedClient if args.autoshard else discord.Client)
    client_class = build_client(base_class)

    shard_id = (
        int(args.shard_id) if args.shard_id is not None else None)
    shard_count = (
        int(args.shard_count) if args.shard_count is not None else None)

    discord_client = client_class(
        engine, redis_client, shard_id=shard_id, shard_count=shard_count)
    discord_client.run(DISCORD_TOKEN)

    LOGGER.info("Shutting down... good bye!")


if __name__ == "__main__":
    main()
