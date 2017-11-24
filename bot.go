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
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis"
)

const (
	// commandWord is a string used to interact with Cho.
	commandWord = "!cho"

	// botStatus is a hard-coded status shown when the bot is online.
	botStatus = "Trivia with the boys"

	// sorryMessage is sent to the Discord channel when a problem arises.
	sorryMessage = "Sorry, I'm having trouble fulfilling your request right now, please try again later."

	// questionTimeout is the amount of time the bot will wait before answering.
	questionTimeout = 15 * time.Second

	// answerTimeout is the amount of time to wait after a question is answered.
	answerTimeout = 3 * time.Second

	// startTimeout is the amount of time before the game starts.
	startTimeout = 10 * time.Second
)

var (
	gameStateMutex = &sync.Mutex{}
)

// ready is called when the initial Discord connection succeeds.
func ready(s *discordgo.Session, event *discordgo.Ready) {
	log.Println("Recieved READY payload")
	s.UpdateStatus(0, botStatus)
}

// messageCreate gets called each time a message is sent to a channel / guild
// assigned to the current shard by Discord.
func messageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	if m.Author.ID == s.State.User.ID {
		return
	}

	if strings.HasPrefix(m.Content, commandWord) {
		commandMessage(s, m)
	} else {
		freeMessage(s, m)
	}
}

// commandMessage is dispatched when a message's contents is deemed a command
// (starts with !cho). The argument splitter is somewhat stupid right now and
// counts double-spaces as individual arguments.
func commandMessage(s *discordgo.Session, m *discordgo.MessageCreate) {
	args := strings.Split(m.Content, " ")
	if len(args) == 3 && args[1] == "start" {
		startCommand(s, m, args[2])
	} else if len(args) == 2 && args[1] == "stop" {
		stopCommand(s, m)
	} else {
		s.ChannelMessageSend(m.ChannelID, "I'm afraid I don't know what you're talking about.")
		return
	}
}

// startCommand starts a new game in the user provided channel.
func startCommand(s *discordgo.Session, m *discordgo.MessageCreate, channelID string) {
	if !(strings.HasPrefix(channelID, "<#") && strings.HasSuffix(channelID, ">")) {
		s.ChannelMessageSend(m.ChannelID, "That's not a valid channel.")
		return
	}
	startGame(s, m, extractChannelID(channelID))
}

// stopCommand stops the current game in the guild where the message was posted.
func stopCommand(s *discordgo.Session, m *discordgo.MessageCreate) {
	gameStateMutex.Lock()
	defer gameStateMutex.Unlock()

	channel, err := discord.State.Channel(m.ChannelID)
	if err != nil {
		log.Println(err)
		return
	}
	gs, err := LoadGameState(rcli, channel.GuildID, "")
	if err != nil {
		s.ChannelMessageSend(m.ChannelID, sorryMessage)
		log.Println("Unable to load GameState:", err)
		return
	} else if err == redis.Nil || gs.Finished {
		s.ChannelMessageSend(m.ChannelID, "There is no game in progress.")
		return
	}

	gs.Finished = true
	if err = gs.Save(rcli); err != nil {
		s.ChannelMessageSend(m.ChannelID, sorryMessage)
		log.Println("Unable to save GameState:", err)
		return
	}
	s.ChannelMessageSend(m.ChannelID, "Oh okay... I've stopped the game per your request. Goodbye...")
}

// freeMessage is dispatched when a message contains normal human text and isn't
// a command. This function is used to process trivia answers from users if a
// game is currently ongoing.
func freeMessage(s *discordgo.Session, m *discordgo.MessageCreate) {
	gameStateMutex.Lock()
	defer gameStateMutex.Unlock()

	channel, err := discord.State.Channel(m.ChannelID)
	if err != nil {
		log.Println(err)
		return
	}
	gs, err := LoadGameState(rcli, channel.GuildID, "")
	if err == redis.Nil {
		return // No game in progress if not in cache.
	} else if err != nil {
		s.ChannelMessageSend(m.ChannelID, sorryMessage)
		log.Println("Unable to load GameState:", err)
		return
	}

	// Ignore chat messages from channels other than the current trivia channel
	// and ignore chat when the bot is waiting after answering a question.
	if m.ChannelID != gs.ChannelID || !gs.Waiting {
		return
	}

	// Where the magic happens, the answer is checked with Levenshtein Distance.
	if !gs.Finished && gs.CheckAnswer(m.Content) {
		if len(gs.Answers) > 0 {
			s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("Correct <@!%s>, the answer was \"%s\"", m.Author.ID, gs.Answers[0]))
		} else {
			s.ChannelMessageSend(m.ChannelID, "Correct.")
		}

		gs.UserScores[m.Author.ID]++
		gs.RemainingQuestions--
		gs.Waiting = false
		if err = gs.Save(rcli); err != nil {
			s.ChannelMessageSend(m.ChannelID, sorryMessage)
			log.Println("Unable to save GameState:", err)
			return
		}

		go func(gs GameState) {
			time.Sleep(answerTimeout)
			checkFinishCondition(s, &gs)
		}(*gs)
	}
}

// checkFinishCondition will finish the game if no more questions remain,
// otherwise it will ask another question.
func checkFinishCondition(s *discordgo.Session, gs *GameState) {
	if gs.RemainingQuestions <= 0 {
		finishGame(s, gs)
	} else {
		askQuestion(s, gs)
	}
}

// startGame creates a new game context object and stores it in redis. The user
// who attempts to start the game will be informed that it started and the first
// question will be asked in the trivia channel specified.
func startGame(s *discordgo.Session, m *discordgo.MessageCreate, triviaChannelID string) {
	gameStateMutex.Lock()
	defer gameStateMutex.Unlock()

	var (
		err error
	)

	// Make sure the trivia channel mentioned by the user exists so we can give
	// the user a helpful message if they made a typo.
	_, err = discord.Channel(triviaChannelID)
	if err != nil {
		s.ChannelMessageSend(m.ChannelID, "I'm sorry, I can't find that channel.")
		return
	}

	// Load GameState from redis so it may be examined and create a new
	// GameState to replace the currently stored one if the previous game has
	// been finished.
	channel, err := discord.State.Channel(m.ChannelID)
	if err != nil {
		log.Println(err)
		return
	}
	gs, err := LoadGameState(rcli, channel.GuildID, triviaChannelID)
	if err != nil {
		s.ChannelMessageSend(m.ChannelID, sorryMessage)
		log.Println("Unable to load GameState:", err)
		return
	}
	if gs.Finished {
		gs = CreateGameState(channel.GuildID, triviaChannelID)
	}

	// Send an appropriate response regarding the game's current state depending
	// on the context.
	if gs.Started {
		s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("A game is already in progress in <#%s>, come join in on the fun!", gs.ChannelID))
	} else {
		s.ChannelMessageSend(m.ChannelID, fmt.Sprintf("I started a game in <#%s>. I promise not to go easy.", gs.ChannelID))

		go func(gs GameState) {
			time.Sleep(startTimeout)
			checkFinishCondition(s, &gs)
		}(*gs)
	}

	gs.Started = true
	if err = gs.Save(rcli); err != nil {
		log.Println(err)
		return
	}
}

// askQuestion picks the next question and sends it to the trivia channel. A
// timer is also set to tell people the answer if no one gets it right.
//
// A question is deemed unanswered if the number of remaining questions does not
// change in the time before the timer starting and ending.
func askQuestion(s *discordgo.Session, gs *GameState) {
	gs.ChooseRandomQuestion()
	s.ChannelMessageSend(gs.ChannelID, gs.Question)

	gs.Waiting = true
	if err := gs.Save(rcli); err != nil {
		log.Println(err)
		return
	}

	go func(gs GameState) {
		time.Sleep(questionTimeout)
		checkIfQuestionAnswered(s, &gs)
	}(*gs)
}

// checkIfQuestionAnswered will check if the current game state has the same
// number of remaining questions as the one passed in. If that's the case that
// means the question wasn't answered successfully and the answers should be
// provided by Cho.
//
// After the answer is provided another question is asked.
func checkIfQuestionAnswered(s *discordgo.Session, gs *GameState) {
	gameStateMutex.Lock()
	defer gameStateMutex.Unlock()

	var (
		err error
	)

	currentGameState, err := LoadGameState(rcli, gs.GuildID, "")
	if err != nil {
		log.Println("Unable to load GameState:", err)
		return
	}
	if currentGameState.Finished {
		return
	}

	if currentGameState.RemainingQuestions == gs.RemainingQuestions {
		if len(gs.Answers) > 0 {
			s.ChannelMessageSend(gs.ChannelID, fmt.Sprintf("The correct answer was \"%s\".", gs.Answers[0]))
		} else {
			s.ChannelMessageSend(gs.ChannelID, "Trick question, there was no answer.")
		}

		gs.RemainingQuestions--
		gs.Waiting = false
		if err = gs.Save(rcli); err != nil {
			log.Println(err)
			return
		}

		go func(gs GameState) {
			time.Sleep(answerTimeout)
			checkFinishCondition(s, &gs)
		}(*gs)
	}
}

// finishGame determines who the winners are and sets the GameState to finished.
// A nice winners list is sent to chat with user nicks and scores listed in a
// bullet list.
func finishGame(s *discordgo.Session, gs *GameState) {
	var (
		err error
	)

	gs.Finished = true
	gs.Waiting = false
	if err = gs.Save(rcli); err != nil {
		log.Println(err)
		return
	}

	winners := gs.GetWinners()
	if len(winners) > 0 {
		msg := "Alright we're out of questions, here are your winners:\n\n"
		for _, winner := range winners {
			plural := ""
			if winner.Score > 1 {
				plural = "s"
			}
			msg += fmt.Sprintf("* <@!%s> - %d point%s\n", winner.UserID, winner.Score, plural)
		}
		msg += "\nThank you for playing! I hope to see you again soon."
		s.ChannelMessageSend(gs.ChannelID, msg)
	} else {
		s.ChannelMessageSend(gs.ChannelID, "Well it appears no one won because no one answered a *single* question right. You people really don't know much about your world.")
	}
}

// extractChannelID removes the discord wrapper characters from a channel id
// that was read from user chat.
func extractChannelID(channelID string) string {
	channelID = strings.TrimPrefix(channelID, "<#")
	channelID = strings.TrimSuffix(channelID, ">")
	return channelID
}
