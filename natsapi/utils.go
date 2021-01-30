package api

import (
	"math/rand"
	"time"
)

func makeChunks(ids []string, chunkSize int) [][]string {
	var chunks [][]string
	for i := 0; i < len(ids); i += chunkSize {
		end := i + chunkSize
		if end > len(ids) {
			end = len(ids)
		}
		chunks = append(chunks, ids[i:end])
	}
	return chunks
}

func randRange(min, max int) int {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(max-min) + min
}
