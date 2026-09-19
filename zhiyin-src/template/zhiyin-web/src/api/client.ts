import axios, { type AxiosInstance } from 'axios'
import type { BackendErrorCode } from './schema'

/**
 * 统一响应拆包。
 *
 * 后端统一信封为 { code, message, data, trace_id }（见 zhiyin_api.dto.common.ApiResponse）。
 * 本文件是全前端唯一处理该信封的地方：成功直接返回 data，失败抛 ApiError。
 */

/**
 * 错误码口径：数值必须与后端 `zhiyin_api/dto/common.py::ErrorCode` 一致。
 *
 * `satisfies Record<string, BackendErrorCode>` 是编译期守卫——这里写错一个数字，
 * `npm run typecheck` 直接失败（该联合类型由后端 OpenAPI 生成）。
 * 运行期的同一份口径由 `tests/test_frontend_alignment.py` 再守一次
 * （跨语言，只能靠断言比对）。
 */
export const ErrorCode = {
  OK: 0,
  INVALID_PARAM: 1001,
  NOT_FOUND: 1002,
  CONFLICT: 1003,
  UNAUTHORIZED: 1004,
  GUEST_LIMIT: 1005,
  STAGE_UNCERTAIN: 1006,
  DEPENDENCY_UNAVAILABLE: 1007,
  INTERNAL: 1999,
} as const satisfies Record<string, BackendErrorCode>

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode]

export class ApiError extends Error {
  constructor(
    readonly code: ErrorCodeValue,
    message: string,
    readonly traceId = '',
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface Envelope<T> {
  code: number
  message: string
  data: T | null
  trace_id: string
}

/** 后端返回码 → 前端应对动作。UI 只按 code 分支，不解析文案。 */
export const ERROR_HANDLING: Record<number, string> = {
  [ErrorCode.UNAUTHORIZED]: '拉起登录 Modal',
  [ErrorCode.GUEST_LIMIT]: '游客采集超过 2 问 → 触发登录拦截',
  [ErrorCode.STAGE_UNCERTAIN]: '环节判定不确定 → 渲染澄清追问，不报错',
  [ErrorCode.DEPENDENCY_UNAVAILABLE]: '依赖降级 → 顶部弱提示，不阻塞对话',
}

/**
 * 接口前缀。**必须**与后端 `zhiyin_api.app.API_PREFIX` 一致（《AGENTS.md》§9）：
 * 前端 base URL 用 `/api/v1`，endpoint 只写 `/app/...`，代理原样转发、不再补版本段。
 *
 * 为什么给兜底值而不是只读环境变量：`zhiyin-web/.env` 是 **gitignored** 的
 * （`.gitignore` 的 `.env` 规则），新克隆的仓库里没有它。此前 `baseURL` 直接取
 * `import.meta.env.VITE_API_BASE_URL`、**没有兜底**，于是缺 `.env` 时前端请求会打到
 * `/app/bootstrap`（少了 `/api/v1`），而 vite 只代理 `/api`——实测构建产物里连
 * 一个 `api/v1` 字符串都没有，属于"换个环境就静默不联通"。
 * 需要指向别的后端时仍然用 `VITE_API_BASE_URL` 覆盖。
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    // 后端**所有**错误响应也是统一信封（`zhiyin_api/app.py` 把 404/400/401/503 全套成
    // {code, message, data, trace_id}），只是非 2xx 时 axios 把它放在 `error.response.data`。
    // 这里曾经无条件替换成 `INTERNAL` + axios 英文串，结果是：
    //   401/503 的 handleGuestError 与降级提示全部失效；
    //   404 的真实业务文案（如"尚未生成诊断报告"）被丢成 "Request failed with status code 404"。
    // 因此先认信封，认不出来（网络错误 / 非本项目响应）才退化成 INTERNAL。
    const envelope = error?.response?.data as Envelope<unknown> | undefined
    if (typeof envelope?.code === 'number' && envelope.code !== ErrorCode.OK) {
      throw new ApiError(envelope.code as ErrorCodeValue, envelope.message, envelope.trace_id)
    }
    throw new ApiError(ErrorCode.INTERNAL, error?.message ?? '网络异常')
  },
)

/** 发起请求并拆掉信封。所有 api/endpoints.ts 里的函数都走这里。 */
export async function request<T>(config: Parameters<AxiosInstance['request']>[0]): Promise<T> {
  const response = await http.request<Envelope<T>>(config)
  const envelope = response.data
  if (envelope.code !== ErrorCode.OK) {
    throw new ApiError(envelope.code as ErrorCodeValue, envelope.message, envelope.trace_id)
  }
  return envelope.data as T
}

export default http
