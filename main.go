package main

// env CGO_ENABLED=0 go build -v -a -ldflags "-s -w" -o nats-api

import (
	"flag"
	"fmt"

	"github.com/wh1te909/tacticalrmm/natsapi"
)

var version = "1.0.8"

func main() {
	ver := flag.Bool("version", false, "Prints version")
	apiHost := flag.String("api-host", "", "django full base url")
	natsHost := flag.String("nats-host", "", "nats full connection string")
	debug := flag.Bool("debug", false, "Debug")
	flag.Parse()

	if *ver {
		fmt.Println(version)
		return
	}

	api.Listen(*apiHost, *natsHost, version, *debug)
}
