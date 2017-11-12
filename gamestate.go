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
	"time"

	"github.com/go-redis/redis"
	"github.com/vmihailenco/msgpack"
)

// GameStateRevision is the current version of the GameState struct. If this
// structure changes we need a way to detect old versions of the structure so we
// can convert them to the newer version.
const GameStateRevision = 1

// GameStateNamespace is prepended to keys relating to active games.
const GameStateNamespace = "chotrivia.games"

// GameStateLifetime is the amount of time a GameState object will persist.
const GameStateLifetime = 86400 * time.Second

// GameState represents a game context taking place in a server.
type GameState struct {
	Revision           int
	StartTime          time.Time
	Question           string
	Answers            []string
	RemainingQuestions int
	Started            bool
	Finished           bool
	Waiting            bool
	GuildID            string
	ChannelID          string
	UserScores         map[string]int
}

// Winner is a Discord user id with an associated score.
type Winner struct {
	UserID string
	Score  int
}

// Save serializes a GameState struct using msgpack and stores it in the redis
// cluster with a lifetime of a day.
func (gs *GameState) Save(rcli *redis.Client) error {
	var (
		err error
	)

	data, err := msgpack.Marshal(gs)
	if err != nil {
		return err
	}

	key := BuildGameStateKey(gs.GuildID)
	err = rcli.Set(key, data, GameStateLifetime).Err()
	if err != nil {
		return err
	}
	log.Printf("Wrote GameState to '%s'", key)

	return nil
}

// GetWinners returns a list of users with the highest score. A list is returned
// as multiple users can tie for a high score.
func (gs *GameState) GetWinners() []Winner {
	// Find out what the highest score is.
	highestScore := 0
	for _, v := range gs.UserScores {
		if v > highestScore {
			highestScore = v
		}
	}

	// There are no winners if no one tries :\
	if highestScore <= 0 {
		return []Winner{}
	}

	// Find users with the highest score, more than 1 means a tie.
	winners := []Winner{}
	for k, v := range gs.UserScores {
		if v == highestScore {
			winners = append(winners, Winner{
				UserID: k,
				Score:  v,
			})
		}
	}

	return winners
}

// CreateGameState initializes a GameState struct with default values.
func CreateGameState(guildID string, channelID string) *GameState {
	return &GameState{
		Revision:           GameStateRevision,
		StartTime:          time.Now().UTC(),
		Question:           "Which mod doesn't give me questions to ask?",
		Answers:            []string{},
		RemainingQuestions: 3,
		Started:            false,
		Finished:           false,
		Waiting:            false,
		GuildID:            guildID,
		ChannelID:          channelID,
		UserScores:         make(map[string]int),
	}
}

// LoadGameState queries for a GameState struct in redis and deserializes it. If
// there's no game object in redis a new one is created and returned.
func LoadGameState(rcli *redis.Client, guildID string, channelID string) (*GameState, error) {
	var (
		err error
	)

	key := BuildGameStateKey(guildID)
	data, err := rcli.Get(key).Bytes()
	if err == redis.Nil && len(channelID) > 0 {
		return CreateGameState(guildID, channelID), nil
	} else if err != nil {
		return nil, err
	}

	gs := &GameState{}
	err = msgpack.Unmarshal(data, gs)
	if err != nil {
		return nil, err
	}

	return gs, nil
}

// BuildGameStateKey returns a key to a specific GameState stored in redis.
func BuildGameStateKey(guildID string) string {
	return fmt.Sprintf("%s.%s", GameStateNamespace, guildID)
}
