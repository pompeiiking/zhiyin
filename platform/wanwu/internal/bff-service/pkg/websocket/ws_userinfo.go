package websocket

type userInfo struct {
	userID  string
	orgID   string
	isAdmin bool
	perms   []string
}

func NewUserInfo(userID, orgID string, isAdmin bool, perms []string) *userInfo {
	return &userInfo{
		userID:  userID,
		orgID:   orgID,
		isAdmin: isAdmin,
		perms:   perms,
	}
}

func (u *userInfo) checkUserIDs(userIDs []string) bool {
	for _, userID := range userIDs {
		if userID == u.userID {
			return true
		}
	}
	return false
}

func (u *userInfo) checkPerm(orgID, perm string) bool {
	if u.orgID != orgID {
		return false
	}
	if u.isAdmin {
		return true
	}
	for _, p := range u.perms {
		if p == perm {
			return true
		}
	}
	return false
}
