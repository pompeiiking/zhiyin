package websocket

import (
	"fmt"
	"sync"

	"github.com/UnicomAI/wanwu/pkg/log"
	"github.com/UnicomAI/wanwu/pkg/util"
	"github.com/gorilla/websocket"
)

type client struct {
	id   int
	user *userInfo
	conn *websocket.Conn
	wg   *sync.WaitGroup

	mutex   sync.Mutex
	stopped bool
	stopCh  chan struct{}
}

func newClient(id int, user *userInfo, conn *websocket.Conn, wg *sync.WaitGroup) *client {
	c := &client{
		id:     id,
		user:   user,
		conn:   conn,
		wg:     wg,
		stopCh: make(chan struct{}, 1),
	}
	c.run()
	return c
}

func (c *client) run() {
	// wait stop
	c.wg.Add(1)
	go func() {
		defer util.PrintPanicStack()
		defer c.wg.Done()
		<-c.stopCh
		if err := c.conn.Close(); err != nil {
			log.Errorf("ws client %v user %v stop err: %v", c.id, c.user.userID, err)
		} else {
			log.Infof("ws client %v user %v stop", c.id, c.user.userID)
		}
	}()
	// read msg
	c.wg.Add(1)
	go func() {
		defer util.PrintPanicStack()
		defer c.wg.Done()
		log.Infof("ws client %v user %v start run", c.id, c.user.userID)
		for {
			msgType, msg, err := c.conn.ReadMessage()
			if err != nil {
				c.mutex.Lock()
				if !c.stopped {
					c.stopped = true
					c.stopCh <- struct{}{}
					if !websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
						log.Errorf("ws client %v user %v read msg typ %v err: %v", c.id, c.user.userID, msgType, err)
					}
				}
				c.mutex.Unlock()
				break
			}
			log.Warnf("ws client %v user %v read msg (%v) %v", c.id, c.user.userID, msgType, string(msg))
		}
	}()
}

func (c *client) stop() {
	c.mutex.Lock()
	if c.stopped {
		log.Errorf("ws client %v user %v already stop", c.id, c.user.userID)
		c.mutex.Unlock()
		return
	}
	c.stopped = true
	c.stopCh <- struct{}{}
	c.mutex.Unlock()
}

func (c *client) checkStop() bool {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	return c.stopped
}

func (c *client) sendMsg(msg interface{}) error {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	if c.stopped {
		return fmt.Errorf("ws client %v user %v send msg but already stop", c.id, c.user.userID)
	}
	if err := c.conn.WriteJSON(msg); err != nil {
		c.stopped = true
		c.stopCh <- struct{}{}
		return fmt.Errorf("ws client %v user %v send msg err: %v", c.id, c.user.userID, err)
	}
	return nil
}

func (c *client) userID() string {
	return c.user.userID
}

func (c *client) checkUserIDs(userIDs []string) bool {
	return c.user.checkUserIDs(userIDs)
}

func (c *client) checkPerm(orgID, perm string) bool {
	return c.user.checkPerm(orgID, perm)
}
