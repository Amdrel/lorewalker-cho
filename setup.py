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

"""setup.py for lorewalker_cho."""

from setuptools import setup, find_packages

setup(
    name="lorewalker_cho",
    packages=find_packages(),
    entry_points={
        "console_scripts": ["lorewalker_cho = lorewalker_cho.__main__:main"]
    },
    version="0.99.4",
    description="Lorewalker Cho is a Discord bot that plays WoW-inspired "
                "trivia games.",
    author="Walter Kuppens",
    author_email="reshurum@gmail.com",
)
