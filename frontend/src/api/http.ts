import axios from 'axios'

interface ApiErrorResponse {
  error: {
    code: string
    message: string
    request_id: string
    details: unknown
  }
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
  headers: {
    Accept: 'application/json',
  },
})

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return (
      error.response?.data.error.message ??
      (error.code === 'ECONNABORTED'
        ? '请求超时，请稍后重试。'
        : '无法连接后端服务。')
    )
  }

  return error instanceof Error ? error.message : '发生未知错误。'
}

export function apiErrorCode(error: unknown): string | null {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data.error.code ?? null
  }
  return null
}
