package main

import (
	"flag"
	"fmt"

	"github.com/wh1te909/tacticalrmm/natsapi"
)

var version = "1.0.0"

func main() {
	ver := flag.Bool("version", false, "Prints version")
	apiHost := flag.String("api-host", "", "django api base url")
	debug := flag.Bool("debug", false, "Debug")
	flag.Parse()

	if *ver {
		fmt.Println(version)
		return
	}

	api.Listen(*apiHost, *debug)
}
