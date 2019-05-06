# Cho Trivia [![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](COPYING)

Cho Trivia is a Discord bot that asks trivia questions related to the game
World of Warcraft.

## Contributing

I can always use more questions and answers for Cho, feel free to make pull
requests with new questions and answers if you want to help out.

## Building

The project requires a recent version of python (3.6+) and uses pip to manage
dependencies.

## Running

A bot token is required for running Cho.

```bash
# Install dependencies.
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt

# Run the bot.
source ./env.sh
./main.py

# Done!
```

An example environment file:

```bash
export CHO_DISCORD_TOKEN="<your_discord_token>"
export CHO_PG_HOST="/var/run/postgresql"
export CHO_PG_DATABASE="cho_trivia"
```

## License

This work is licensed under the GPLv3.
