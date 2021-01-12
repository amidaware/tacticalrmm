package main

import (
	"flag"

	"github.com/wh1te909/tacticalrmm/natsapi"
)

func main() {
	apiHost := flag.String("api-host", "", "django api base url")
	debug := flag.Bool("debug", false, "Debug")
	flag.Parse()

	api.Listen(*apiHost, *debug)
}
