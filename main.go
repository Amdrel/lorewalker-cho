// Discord bot that does World of Warcraft trivia.
// Copyright (C) 2017  Walter Kuppens
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

package main

import (
	"encoding/json"
	"flag"
	"io/ioutil"
	"log"
	"math/rand"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis"
)

// ChoConfig represents the values contained in the question config file.
type ChoConfig struct {
	Ratio         float64    `json:"ratio"`
	QuestionCount int        `json:"questionCount"`
	Questions     []Question `json:"questions"`
}

var (
	// Command-line flags are stored here after being parsed.
	flags struct {
		Token         string
		Redis         string
		RedisPassword string
		ShardID       int
		ShardCount    int
	}

	discord *discordgo.Session
	rcli    *redis.Client

	// choConfig is the default set of questions and answers Cho asks, among
	// other configuration values soon to come.
	choConfig = &ChoConfig{}
)

func init() {
	rand.Seed(time.Now().Unix()) // Initialize global PRNG.

	flag.StringVar(&flags.Token, "t", "", "Bot Token")
	flag.StringVar(&flags.Redis, "r", "", "Redis Connection String")
	flag.StringVar(&flags.RedisPassword, "p", "", "Optional Redis Password")
	flag.IntVar(&flags.ShardID, "s", 0, "Shard ID")
	flag.IntVar(&flags.ShardCount, "c", 1, "Number of shards")
	flag.Parse()

	if len(flags.Token) == 0 {
		log.Fatalln("A token must be provided to start Cho.")
	} else if len(flags.Redis) == 0 {
		log.Fatalln("A redis connection string must be provided.")
	} else if (flags.ShardID) < 0 {
		log.Fatalln("A shard id can't be negative.")
	} else if flags.ShardCount <= 0 {
		log.Fatalln("You cannot have less than 1 shard.")
	}

	// Read from the questions file provided in the command-line arguments and
	// load them into memory for use by the bot during runtime.
	freeArgs := flag.Args()
	if len(freeArgs) <= 0 {
		log.Fatalln("Please specify a questions file as an argument.")
	}
	data, err := ioutil.ReadFile(freeArgs[0])
	if err != nil {
		log.Fatalln(err)
	}
	if err = json.Unmarshal(data, choConfig); err != nil {
		log.Fatalln(err)
	}
}

func main() {
	var (
		err error
	)

	// Connect to the redis cluster and send a ping to ensure success.
	log.Println("Connecting to redis cluster:", flags.Redis)
	rcli = redis.NewClient(&redis.Options{
		Addr:     flags.Redis,
		DB:       0,
		Password: flags.RedisPassword,
	})
	_, err = rcli.Ping().Result()
	if err != nil {
		log.Fatalln("Failed to connect to redis:", err)
	}

	discord, err = discordgo.New("Bot " + flags.Token)
	if err != nil {
		log.Fatalln(err)
	}
	discord.ShardCount = flags.ShardCount
	discord.ShardID = flags.ShardID
	discord.AddHandler(ready)
	discord.AddHandler(messageCreate)

	// Open a websocket with Discord to start receiving messages.
	err = discord.Open()
	if err != nil {
		log.Fatalln("Unable to open connection with Discord:", err)
	}
	defer discord.Close()

	// Setup a channel to wait for a termination signal from the OS. Once a
	// signal is received connections are cleaned up and we exit.
	log.Println("Cho is now running, send SIGTERM to close gracefully.")
	signalChannel := make(chan os.Signal, 1)
	signal.Notify(signalChannel, syscall.SIGINT, syscall.SIGTERM, os.Interrupt, os.Kill)
	<-signalChannel

	log.Println("Cho is shutting down...")
}
