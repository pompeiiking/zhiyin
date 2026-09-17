import { ApiError, ErrorCode } from '@/api/client'
import { useSessionStore } from '@/stores/session'

/** 仅处理后端给出的游客限制，不在前端推断问题次数或权限。 */
export function useGuestGuard() {
  const session = useSessionStore()
  function handleGuestError(error: unknown): boolean {
    if (!(error instanceof ApiError)) return false
    if (error.code !== ErrorCode.UNAUTHORIZED && error.code !== ErrorCode.GUEST_LIMIT) return false
    session.identity = { ...session.identity, role: 'guest' }
    session.openLogin(error.code === ErrorCode.GUEST_LIMIT ? '本次体验已达到游客上限，登录后继续。' : '请登录后继续。')
    return true
  }
  return { handleGuestError }
}
