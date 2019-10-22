package main

import(
	"os/exec"
	"os"
)

func main(){
	unins_file := "C:\\Program Files\\TacticalAgent\\unins000.exe"

	if fileExists(unins_file) {
		c := exec.Command("cmd", "/C", unins_file, "/VERYSILENT", "/SUPPRESSMSGBOXES")
		c.Run()
	}
}

func fileExists(filename string) bool {
    info, err := os.Stat(filename)
    if os.IsNotExist(err) {
        return false
    }
    return !info.IsDir()
}
