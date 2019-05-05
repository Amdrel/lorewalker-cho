"""Contains the Discord client class for Cho."""

import logging
import discord

LOGGER = logging.getLogger("cho")


class ChoClient(discord.Client):
    """Discord client wrapper that uses functionality from cho.py."""

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        LOGGER.info("Client logged in as \"%s\"", self.user)

    async def on_message(self, message):
        """Called whenever the bot receives a message from Discord.

        :param m message:
        :type m: discord.message.Message
        """

        LOGGER.info("Message from \"%s\": %s", message.author, message.content)
