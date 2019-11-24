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

"""Core code that controls Cho's behavior."""

import logging
import os

from collections import OrderedDict

import jellyfish

from discord.channel import TextChannel
from discord.member import Member
from discord.message import Message

DEFAULT_PREFIX = "!"

LOGGER = logging.getLogger("cho")

GLOBAL_COMMANDS = OrderedDict()
CHANNEL_COMMANDS = OrderedDict()


def cho_command(command, kind="global", admin_only=False, owner_only=False):
    """Marks a function as a runnable command."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if owner_only:
                message = args[1]
                if not is_owner(message.author):
                    return message.channel.send(
                        "Sorry, only the bot owner can run that command."
                    )
                return func(*args, **kwargs)
            elif admin_only:
                message = args[1]
                if not is_admin(message.author, message.channel):
                    return message.channel.send(
                        "Sorry, only administrators run that command."
                    )
                return func(*args, **kwargs)

            return func(*args, **kwargs)

        if kind == "global":
            GLOBAL_COMMANDS[command] = wrapper
        elif kind == "channel":
            CHANNEL_COMMANDS[command] = wrapper
        else:
            raise ValueError("Unknown cho command type passed in decorator.")

        return wrapper

    return decorator


def get_prefix(config: dict = None) -> str:
    """Gets the prefix for the specified guild.

    :param dict config:
    :rtype: str
    :return:
    """

    if config and "prefix" in config:
        return config["prefix"]

    return DEFAULT_PREFIX


def is_command(message: Message, prefix: str) -> bool:
    """Checks if a Discord message is a Cho command invocation.

    :param m message:
    :param str prefix:
    :type m: discord.message.Message
    :rtype: bool
    :return:
    """

    return (
        message.content.startswith("{}cho".format(prefix))
        or message.content.startswith("{}trivia".format(prefix))
    )


def is_admin(member: Member, channel: TextChannel) -> bool:
    """Checks if a passed in Member is an administrator.

    :param m member:
    :param c channel:
    :type m: discord.member.Member
    :type c: discord.channel.Channel
    :rtype: bool
    :return:
    """

    return channel.permissions_for(member).administrator


def is_owner(member: Member) -> bool:
    """Checks if a passed in Member is the bot owner (me!).

    :param m member:
    :type m: discord.member.Member
    :rtype: bool
    :return:
    """

    is_bot_owner = False

    try:
        is_bot_owner = member.id == int(os.environ.get("CHO_OWNER", 0))
    except ValueError:
        pass

    return is_bot_owner


def is_message_from_trivia_channel(message: Message, config: dict) -> bool:
    """Checks if the message is from the trivia channel.

    :param m message:
    :param dict config:
    :type m: discord.message.Message
    """

    if "trivia_channel" in config:
        return message.channel.id == config["trivia_channel"]

    return message.channel.name == "trivia"


def levenshtein_ratio(source, target, ignore_case=True):
    """Calculates the levenshtein ratio between two strings.

    The ratio is computed as follows:
        (len(source) + len(target) - distance) / (len(source) + len(target))

    This function has been ported from (MIT license):
        https://github.com/texttheater/golang-levenshtein/blob/4041401c6e7f6a2b49815c4aea652e518ca8e92e/levenshtein/levenshtein.go#L115-L130

    :param str source:
    :param str target:
    :rtype: float
    :return:
    """

    if ignore_case:
        distance = jellyfish.levenshtein_distance(
            source.lower().strip(),
            target.lower().strip()
        )
    else:
        distance = jellyfish.levenshtein_distance(source, target)

    source_len = len(source)
    target_len = len(target)

    return (source_len + target_len - distance) / (source_len + target_len)
