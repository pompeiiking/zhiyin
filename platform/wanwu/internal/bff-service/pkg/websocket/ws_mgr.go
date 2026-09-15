package websocket

import (
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

type Mgr struct {
	upgrader websocket.Upgrader
	wg       sync.WaitGroup

	mutex   sync.Mutex
	idCnt   int             // generate new client id
	clients map[int]*client // id -> client
	stopped bool
	stop    chan struct{}
}

func NewMgr() *Mgr {
	return &Mgr{
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		},
		clients: make(map[int]*client),
		stop:    make(chan struct{}, 1),
	}
}

func (m *Mgr) Run() error {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	if m.stopped {
		return fmt.Errorf("ws mgr already stop")
	}

	m.wg.Add(1)
	go func() {
		defer util.PrintPanicStack()
		defer m.wg.Done()
		ticker := time.NewTicker(time.Minute)
		defer ticker.Stop()
		log.Infof("ws mgr start run")
		for {
			select {
			case <-m.stop:
				m.mutex.Lock()
				for id, c := range m.clients {
					if !c.checkStop() {
						c.stop()
					}
					delete(m.clients, id)
				}
				m.mutex.Unlock()
				return
			case <-ticker.C:
				m.mutex.Lock()
				for id, c := range m.clients {
					if c.checkStop() {
						delete(m.clients, id)
					}
				}
				m.mutex.Unlock()
			}
		}
	}()
	return nil
}

func (m *Mgr) Stop() {
	m.mutex.Lock()
	if m.stopped {
		log.Errorf("ws mgr already stop")
		m.mutex.Unlock()
		return
	}
	m.stopped = true
	m.stop <- struct{}{}
	m.mutex.Unlock()
	m.wg.Wait()
	log.Infof("ws mgr stop")
}

func (m *Mgr) HandleWebSocket(ctx *gin.Context, user *userInfo) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	if m.stopped {
		return fmt.Errorf("ws mgr already stop")
	}

	conn, err := m.upgrader.Upgrade(ctx.Writer, ctx.Request, nil)
	if err != nil {
		return fmt.Errorf("ws mgr upgrade to websocket err: %v", err)
	}
	m.idCnt++
	m.clients[m.idCnt] = newClient(m.idCnt, user, conn, &m.wg)
	return nil
}

func (m *Mgr) Broadcast(msg interface{}) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	log.Infof("ws mgr broadcast msg (%v)", msg)
	for id, c := range m.clients {
		if !c.checkStop() {
			if err := c.sendMsg(msg); err != nil {
				log.Errorf("ws mgr broadcast to client %v user %v err: %v", id, c.userID(), err)
			} else {
				log.Infof("ws mgr broadcast to client %v user %v", id, c.userID())
			}
		}
	}
}

func (m *Mgr) SendToUsers(msg interface{}, userIDs []string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	log.Infof("ws mgr send msg (%v) to users %v", msg, userIDs)
	for id, c := range m.clients {
		if !c.checkStop() && c.checkUserIDs(userIDs) {
			if err := c.sendMsg(msg); err != nil {
				log.Errorf("ws mgr send to client %v user %v err: %v", id, c.userID(), err)
			} else {
				log.Infof("ws mgr send to client %v user %v", id, c.userID())
			}
		}
	}
}

func (m *Mgr) SendByPerm(msg interface{}, orgID, perm string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	log.Infof("ws mgr send msg (%v) to org %v perm %v", msg, orgID, perm)
	for id, c := range m.clients {
		if !c.checkStop() && c.checkPerm(orgID, perm) {
			if err := c.sendMsg(msg); err != nil {
				log.Errorf("ws mgr send to client %v user %v err: %v", id, c.userID(), err)
			} else {
				log.Infof("ws mgr send to client %v user %v", id, c.userID())
			}
		}
	}
}

func (m *Mgr) CloseUsers(userIDs []string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	log.Infof("ws mgr close users %v", userIDs)
	for id, c := range m.clients {
		if !c.checkStop() && c.checkUserIDs(userIDs) {
			c.stop()
			delete(m.clients, id)
			log.Infof("ws mgr close client %v user %v", id, c.userID())
		}
	}
}
