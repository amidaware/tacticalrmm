package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
	trmm "github.com/wh1te909/trmm-shared"
)

func GetConfig(cfg string) (db *sqlx.DB, r DjangoConfig, err error) {
	if cfg == "" {
		cfg = "/rmm/api/tacticalrmm/nats-api.conf"
		if !trmm.FileExists(cfg) {
			err = errors.New("unable to find config file")
			return
		}
	}

	jret, _ := os.ReadFile(cfg)
	err = json.Unmarshal(jret, &r)
	if err != nil {
		return
	}

	psqlInfo := fmt.Sprintf("host=%s port=%d user=%s "+
		"password=%s dbname=%s sslmode=%s",
		r.Host, r.Port, r.User, r.Pass, r.DBName, r.SSLMode)

	db, err = sqlx.Connect("postgres", psqlInfo)
	if err != nil {
		return
	}
	db.SetMaxOpenConns(20)
	return
}
