// Discord bot that does World of Warcraft trivia.
// Copyright (C) 2017  Walter Kuppens

// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	"github.com/bwmarrin/discordgo"
	redis "gopkg.in/redis.v3"
)

var (
	// Command-line flags are stored here after being parsed.
	flags struct {
		Token      string
		Redis      string
		Shard      int
		ShardCount int
	}

	discord *discordgo.Session
	rcli    *redis.Client
)

func init() {
	var (
		Shard      string
		ShardCount string
		err        error
	)

	flag.StringVar(&flags.Token, "t", "", "Bot Token")
	flag.StringVar(&flags.Redis, "r", "", "Redis Connection String")
	flag.StringVar(&Shard, "s", "0", "Shard ID")
	flag.StringVar(&ShardCount, "c", "1", "Number of shards")
	flag.Parse()

	if len(flags.Token) == 0 {
		log.Fatalln("A token must be provided to start Cho.")
	} else if len(flags.Redis) == 0 {
		log.Fatalln("A redis connection string must be provided.")
	} else if flags.Shard, err = strconv.Atoi(Shard); err != nil {
		log.Fatalln("Invalid shard id passed.")
	} else if flags.ShardCount, err = strconv.Atoi(ShardCount); err != nil {
		log.Fatalln("Invalid shard count passed.")
	} else if flags.ShardCount <= 0 {
		log.Fatalln("You cannot have less than 1 shard.")
	}

	log.Println(flags.ShardCount)
}

func main() {
	var (
		err error
	)

	discord, err := discordgo.New("Bot " + flags.Token)
	if err != nil {
		log.Fatalln(err)
	}
	discord.AddHandler(messageCreate)

	err = discord.Open()
	if err != nil {
		log.Fatalln("Unable to open connection with Discord", err)
	}

	// Setup a channel to wait for a termination signal from the os. Once a
	// signal is received connections are cleaned up.
	log.Println("Cho is now running, send SIGTERM to close gracefully.")
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
	<-signalChannel

	log.Println("Cho is shutting down...")
	discord.Close()
}
