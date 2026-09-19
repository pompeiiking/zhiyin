import { computed } from 'vue'

import { ApiError, ErrorCode } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import { useWorkspaceStore } from '@/stores/workspace'

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
 * 覆盖率和整体置信度**不是前端算的**：后端按决策 5（关键字段口径）算好，
 * 经 `GET /app/workspace` 的 `profile_panel` 下发，前端只读不算。
 *
 * 此前这里硬编码了「关键字段 6 项 / 覆盖率 ≥ 0.8 / 置信度 ≥ 0.7」，并按字段总数
 * 推算覆盖度——既与后端各写一份阈值（必然漂移），又根本算不对：前端没有关键字段
 * 全集，`profile.fields` 只是"已落库字段"。同理，"是否已达解析门槛"由后端判定并
 * 触发交接，前端不再自行宣称。
 */
export function useProfileCoverage() {
  const workspace = useWorkspaceStore()
  const session = useSessionStore()

  const profile = computed(() => workspace.profilePanel as Record<string, unknown> | null)
  const coverage = computed(() =>
    typeof profile.value?.coverage === 'number' ? (profile.value.coverage as number) : 0,
  )
  const confidence = computed(() =>
    typeof profile.value?.overall_confidence === 'number'
      ? (profile.value.overall_confidence as number)
      : 0,
  )
  const gaps = computed(() =>
    ((profile.value?.gaps ?? []) as Array<{ key?: string }>)
      .map((item) => String(item.key ?? ''))
      .filter(Boolean)
      .map((key) => session.copyBundle[`profile.field.${key}`] ?? key),
  )
  const coverageText = computed(() => `${Math.round(coverage.value * 100)}%`)
  const confidenceText = computed(() => confidence.value.toFixed(2))

  return { profile, coverage, confidence, gaps, coverageText, confidenceText }
}