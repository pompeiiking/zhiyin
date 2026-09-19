import { computed } from 'vue'

import { ApiError, ErrorCode } from '@/api/client'
import { useConversationStore } from '@/stores/conversation'
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
/**
 * 画像覆盖口径（全站唯一处）。
 *
 * 阈值与关键字段数来自 `data/registry/policy_params.json::profile_collection`：
 * 关键字段 6 项、覆盖率 ≥ 0.8 且整体置信度 ≥ 0.7 才算采集完成。
 * 组件不得各自再写一套阈值，也不得按画像字段总数另算覆盖率——`profile.fields` 是「已落库字段」
 * （含 2 个待采集），既不是关键字段全集，也不是覆盖率分母。
 *
 * ⚠️ 第一期这三个常量是演示期的落地值（前端先按同一份口径渲染）；接口接入后应由 bootstrap
 *    下发 `profile_collection` 规则参数，前端只读不算，与后端「阈值不硬编码」的口径一致。
 */
export const PROFILE_KEY_FIELDS = 6
export const PROFILE_COVERAGE_THRESHOLD = 0.8
export const PROFILE_CONFIDENCE_THRESHOLD = 0.7

export function useProfileCoverage() {
  const conversation = useConversationStore()
  const profile = computed(() => conversation.profile as Record<string, unknown>)
  const coverage = computed(() => (typeof profile.value.coverage === 'number' ? profile.value.coverage : 0))
  const confidence = computed(() =>
    typeof profile.value.overall_confidence === 'number' ? profile.value.overall_confidence : 0,
  )
  const gaps = computed(() =>
    ((profile.value.gaps ?? []) as Array<{ name?: string }>).map((item) => item.name ?? '').filter(Boolean),
  )
  const coverageText = computed(() => `${Math.round(coverage.value * PROFILE_KEY_FIELDS)} / ${PROFILE_KEY_FIELDS}`)
  const confidenceText = computed(() => confidence.value.toFixed(2))
  const archiveReady = computed(
    () => coverage.value >= PROFILE_COVERAGE_THRESHOLD && confidence.value >= PROFILE_CONFIDENCE_THRESHOLD,
  )
  return { profile, coverage, confidence, gaps, coverageText, confidenceText, archiveReady }
}