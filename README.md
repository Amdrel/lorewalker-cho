# Cho Trivia [![Build Status](https://travis-ci.org/Reshurum/cho-trivia.svg?branch=master)](https://travis-ci.org/Reshurum/cho-trivia) [![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](COPYING)

Cho Trivia is a Discord bot that asks trivia questions related to the game World of Warcraft.

## Contributing

We can always use more questions and answers for Cho, feel free to make pull requests with new questions and answers if you want to help out.

## Building

The project is built in Go and uses the official [dep](https://github.com/golang/dep) package manager. The typical `go build` and run workflow works for this project.

## Running

A bot token and redis are required for running Cho. Redis is used for saving game states between bot restarts; a list of ip/port combinations and an optional password must be passed as arguments.

```bash
./cho-trivia -t BOT_TOKEN -r 127.0.0.1:6379 -p OPTIONAL_PASSWORD
```

## License

This work is licensed under the GPLv3.
