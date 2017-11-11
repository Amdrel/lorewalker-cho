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
	"fmt"
	"log"
	"strings"

	"github.com/bwmarrin/discordgo"
)

// ready is called when the initial Discord connection succeeds.
func ready(s *discordgo.Session, event *discordgo.Ready) {
	log.Println("Recieved READY payload")
	s.UpdateStatus(0, "chotrivia.com")
}

// messageCreate gets called each time a message is sent to a channel / guild
// assigned to the current shard by Discord.
func messageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	if m.Author.ID == s.State.User.ID {
		return
	}

	if strings.HasPrefix(m.Content, "!cho") {
		commandMessage(s, m)
	} else {
		freeMessage(s, m)
	}
}

// commandMessage is dispatched when a message's contents is deemed a command
// (starts with !cho).
func commandMessage(s *discordgo.Session, m *discordgo.MessageCreate) {
	args := strings.Split(m.Content, " ")
	if len(args) == 3 && args[1] == "start" {
		// Ensure the channel being referenced is an actual channel reference.
		if !(strings.HasPrefix(args[2], "<#") && strings.HasSuffix(args[2], ">")) {
			s.ChannelMessageSend(m.ChannelID, "That's not a valid channel.")
			return
		}

		// Start a game in the channel specified by the user.
		channelID := args[2]
		channelID = strings.TrimPrefix(channelID, "<#")
		channelID = strings.TrimSuffix(channelID, ">")
		startGame(s, m, channelID)
	} else {
		s.ChannelMessageSend(m.ChannelID, "I'm afraid I don't know what you're talking about.")
		return
	}
}

// freeMessage is dispatched when a message contains normal human text and isn't
// a command. This function is used to process trivia answers from users if a
// game is currently ongoing.
func freeMessage(s *discordgo.Session, m *discordgo.MessageCreate) {
}

// startGame creates a new game context object and stores it in redis.
func startGame(s *discordgo.Session, m *discordgo.MessageCreate, triviaChannelID string) {
	var (
		err error
	)

	// Make sure the trivia channel mentioned by the user exists.
	_, err = discord.Channel(triviaChannelID)
	if err != nil {
		s.ChannelMessageSend(m.ChannelID, "I'm sorry, I can't find that channel.")
		return
	}

	// Load GameState from redis so it may be examined.
	channel, err := discord.State.Channel(m.ChannelID)
	if err != nil {
		log.Println(err)
		return
	}
	gs, err := LoadGameState(rcli, channel.GuildID, triviaChannelID)
	if err != nil {
		log.Println("Unable to load GameState:", err)
		return
	}

	// Create a new GameState to replace the currently stored one if a previous
	// game has been finished.
	if gs.Finished {
		gs = CreateGameState(channel.GuildID, triviaChannelID)
	}

	// Send an appropriate response regarding the game depending on the context.
	if gs.Started {
		s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("A game is already in progress in <#%s>, come join in on the fun!", triviaChannelID))
	} else {
		s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("I started a game in <#%s>. I promise not to go easy.", triviaChannelID))
	}

	gs.Started = true
	err = gs.Save(rcli)
	if err != nil {
		log.Println(err)
		return
	}
}
