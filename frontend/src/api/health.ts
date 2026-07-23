export interface ReadinessResponse {
  status: 'ready'
  database: 'ok'
  vector_database: 'ok'
  redis: 'ok'
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  const response = await fetch('/api/v1/health/ready', {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`健康检查返回 HTTP ${response.status}`)
  }

  return (await response.json()) as ReadinessResponse
}
