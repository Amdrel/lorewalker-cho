"""Contains the Discord client class for Cho."""

import logging
import discord

logger = logging.getLogger("cho")


class ChoClient(discord.Client):
    """Discord client wrapper that uses functionality from cho.py."""

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord."""

        logger.info("Client logged in as \"%s\"", self.user)

    async def on_message(self, message):
        """Called whenever the bot recieves a message from Discord.

        :param m message:
        :type m: discord.message.Message
        """

        logger.info("Message from \"%s\": %s", message.author, message.content)
