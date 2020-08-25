package main

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"time"
	"flag"
	"strings"
)

var Version string
var Api string
var Client string
var Site string
var Atype string
var Power string
var Rdp string
var Ping string
var Token string

func downloadAgent(filepath string, url string) (err error) {

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Bad response: %s", resp.Status)
	}

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return err
	}

	return nil
}



func main() {

	debugLog := flag.String("log", "", "Verbose output")
	localSalt := flag.String("local-salt", "", "Use local salt minion")
	localMesh := flag.String("local-mesh", "", "Use local mesh agent")
	flag.Parse()

	agentBinary := fmt.Sprintf("C:\\Windows\\Temp\\winagent-v%s.exe", Version)

	
	url := fmt.Sprintf("https://github.com/wh1te909/winagent/releases/download/v%s/winagent-v%s.exe", Version, Version)
	fmt.Println("Downloading agent...")
	dl := downloadAgent(agentBinary, url)
	if dl != nil {
		fmt.Println("ERROR: unable to download agent from", url)
		fmt.Println(dl)
		os.Exit(1)
	}

	fmt.Println("Extracting files...")
	winagentCmd := exec.Command(agentBinary, "/VERYSILENT", "/SUPPRESSMSGBOXES")
	err := winagentCmd.Run()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	time.Sleep(20 * time.Second)

	tacrmm := "C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"

	cmdArgs := []string{
		"-m", "install", "--api", Api, "--client-id",
		Client, "--site-id", Site, "--agent-type", Atype,
		"--power", Power, "--rdp", Rdp, "--ping", Ping,
		"--auth", Token,
	}

	if strings.TrimSpace(*debugLog) == "DEBUG" {
		cmdArgs = append(cmdArgs, "--log", "DEBUG")
	}

	if len(strings.TrimSpace(*localSalt)) != 0 {
		cmdArgs = append(cmdArgs, "--local-salt", *localSalt)
	}

	if len(strings.TrimSpace(*localMesh)) != 0 {
		cmdArgs = append(cmdArgs, "--local-mesh", *localMesh)
	}

	fmt.Println("Installation starting.")
	cmd := exec.Command(tacrmm, cmdArgs...)

	cmdReader, err := cmd.StdoutPipe()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return
	}

	scanner := bufio.NewScanner(cmdReader)
	go func() {
		for scanner.Scan() {
			fmt.Println(scanner.Text())
		}
	}()

	err = cmd.Start()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return
	}

	err = cmd.Wait()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return
	}

	e := os.Remove(agentBinary)
	if e != nil {
		fmt.Println(e)
	}
}
