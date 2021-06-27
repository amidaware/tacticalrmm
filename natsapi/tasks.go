package api

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math/rand"
	"sync"
	"time"

	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
	nats "github.com/nats-io/nats.go"
	"github.com/ugorji/go/codec"
)

type JsonFile struct {
	Agents  []string `json:"agents"`
	Key     string   `json:"key"`
	NatsURL string   `json:"natsurl"`
}

type DjangoConfig struct {
	Key     string `json:"key"`
	NatsURL string `json:"natsurl"`
	User    string `json:"user"`
	Pass    string `json:"pass"`
	Host    string `json:"host"`
	Port    int    `json:"port"`
	DBName  string `json:"dbname"`
}

type Agent struct {
	ID      int    `db:"id"`
	AgentID string `db:"agent_id"`
}

type Recovery struct {
	Func string            `json:"func"`
	Data map[string]string `json:"payload"`
}

func setupNatsOptions(key string) []nats.Option {
	opts := []nats.Option{
		nats.Name("TacticalRMM"),
		nats.UserInfo("tacticalrmm", key),
		nats.ReconnectWait(time.Second * 2),
		nats.RetryOnFailedConnect(true),
		nats.MaxReconnects(3),
		nats.ReconnectBufSize(-1),
	}
	return opts
}

func MonitorAgents(file string) {
	var result JsonFile
	var payload, recPayload []byte
	var mh codec.MsgpackHandle
	mh.RawToString = true
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "ping"})

	rec := codec.NewEncoderBytes(&recPayload, new(codec.MsgpackHandle))
	rec.Encode(Recovery{
		Func: "recover",
		Data: map[string]string{"mode": "tacagent"},
	})

	jret, _ := ioutil.ReadFile(file)
	err := json.Unmarshal(jret, &result)
	if err != nil {
		log.Fatalln(err)
	}

	opts := setupNatsOptions(result.Key)

	nc, err := nats.Connect(result.NatsURL, opts...)
	if err != nil {
		log.Fatalln(err)
	}
	defer nc.Close()

	var wg sync.WaitGroup
	var resp string
	wg.Add(len(result.Agents))

	for _, id := range result.Agents {
		go func(id string, nc *nats.Conn, wg *sync.WaitGroup) {
			defer wg.Done()
			out, err := nc.Request(id, payload, 1*time.Second)
			if err != nil {
				return
			}
			dec := codec.NewDecoderBytes(out.Data, &mh)
			if err := dec.Decode(&resp); err == nil {
				// if the agent is respoding to pong from the rpc service but is not showing as online (handled by tacticalagent service)
				// then tacticalagent service is hung. forcefully restart it
				if resp == "pong" {
					nc.Publish(id, recPayload)
				}
			}
		}(id, nc, &wg)
	}
	wg.Wait()
}

func CheckIn(file string) {
	var r DjangoConfig

	jret, _ := ioutil.ReadFile(file)
	err := json.Unmarshal(jret, &r)
	if err != nil {
		log.Fatalln(err)
	}

	psqlInfo := fmt.Sprintf("host=%s port=%d user=%s "+
		"password=%s dbname=%s sslmode=disable",
		r.Host, r.Port, r.User, r.Pass, r.DBName)

	db, err := sqlx.Connect("postgres", psqlInfo)
	if err != nil {
		log.Fatalln(err)
	}
	db.SetMaxOpenConns(15)

	agent := Agent{}
	agents := make([]Agent, 0)
	rows, err := db.Queryx("SELECT agents_agent.id, agents_agent.agent_id FROM agents_agent")
	if err != nil {
		log.Fatalln(err)
	}

	for rows.Next() {
		err := rows.StructScan(&agent)
		if err != nil {
			continue
		}
		agents = append(agents, agent)
	}

	var payload []byte
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "ping"})

	opts := setupNatsOptions(r.Key)

	nc, err := nats.Connect(r.NatsURL, opts...)
	if err != nil {
		log.Fatalln(err)
	}
	defer nc.Close()

	var wg sync.WaitGroup
	wg.Add(len(agents))

	loc, _ := time.LoadLocation("UTC")
	now := time.Now().In(loc)

	for _, a := range agents {
		go func(id string, pk int, nc *nats.Conn, wg *sync.WaitGroup, db *sqlx.DB, now time.Time) {
			defer wg.Done()

			var resp string
			var mh codec.MsgpackHandle
			mh.RawToString = true

			time.Sleep(time.Duration(randRange(100, 1500)) * time.Millisecond)
			out, err := nc.Request(id, payload, 1*time.Second)
			if err != nil {
				return
			}

			dec := codec.NewDecoderBytes(out.Data, &mh)
			if err := dec.Decode(&resp); err == nil {
				if resp == "pong" {
					_, err = db.NamedExec(
						`UPDATE agents_agent SET last_seen=:lastSeen WHERE agents_agent.id=:pk`,
						map[string]interface{}{"lastSeen": now, "pk": pk},
					)
					if err != nil {
						fmt.Println(err)
					}
				}
			}
		}(a.AgentID, a.ID, nc, &wg, db, now)
	}
	wg.Wait()
	db.Close()
}

func GetWMI(file string) {
	var result JsonFile
	var payload []byte
	var mh codec.MsgpackHandle
	mh.RawToString = true
	ret := codec.NewEncoderBytes(&payload, new(codec.MsgpackHandle))
	ret.Encode(map[string]string{"func": "wmi"})

	jret, _ := ioutil.ReadFile(file)
	err := json.Unmarshal(jret, &result)
	if err != nil {
		log.Fatalln(err)
	}

	opts := setupNatsOptions(result.Key)

	nc, err := nats.Connect(result.NatsURL, opts...)
	if err != nil {
		log.Fatalln(err)
	}
	defer nc.Close()

	var wg sync.WaitGroup
	wg.Add(len(result.Agents))

	for _, id := range result.Agents {
		go func(id string, nc *nats.Conn, wg *sync.WaitGroup) {
			defer wg.Done()
			time.Sleep(time.Duration(randRange(0, 28)) * time.Second)
			nc.Publish(id, payload)
		}(id, nc, &wg)
	}
	wg.Wait()
}

func randRange(min, max int) int {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(max-min) + min
}
