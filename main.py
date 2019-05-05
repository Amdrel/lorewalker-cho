#!/usr/bin/env python3

"""Command-line interface to start cho."""

import argparse
import logging
import os
import sqlalchemy as sa

from cho_client import ChoClient

POSTGRES_CONFIG = {
    "connection_type": os.environ["CHO_PG_CONNECTION_TYPE"],
    "host": os.environ["CHO_PG_HOST"],
    "database": os.environ["CHO_PG_DATABASE"],
}
SQLALCHEMY_URL = "postgresql+psycopg2://:@/{dbname}?host={host}".format(
    dbname=POSTGRES_CONFIG["database"], host=POSTGRES_CONFIG["host"]
)

DISCORD_TOKEN = os.environ["CHO_DISCORD_TOKEN"]
SQLALCHEMY_POOL_SIZE = int(os.environ.get("SQLALCHEMY_POOL_SIZE", 6))

# Setup text logging for the bot that will be used throughout the application.
LOG_FORMAT = "%(asctime)-15s [%(levelname)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT)
LOGGER = logging.getLogger("cho")
LOGGER.setLevel("INFO")


def main():
    """Entrypoint for Cho on the CLI."""

    parser = argparse.ArgumentParser(description="Start a Cho Trivia worker.")
    args = parser.parse_args()

    LOGGER.info("Starting Cho Trivia worker")
    engine = sa.create_engine(
        SQLALCHEMY_URL, pool_size=SQLALCHEMY_POOL_SIZE, max_overflow=0
    )
    LOGGER.info("Started connection pool with size: %d", SQLALCHEMY_POOL_SIZE)

    discord_client = ChoClient()
    discord_client.run(DISCORD_TOKEN)

    LOGGER.info("Shutting down... good bye!")


if __name__ == "__main__":
    main()
