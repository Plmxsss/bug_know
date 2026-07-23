import { apiClient } from './http'

export interface DiagnosedEntity {
  entity_id: number
  name: string
  confidence: number
  count: number
  introduction: string
  typical_features: string
  host_plants: string[]
  damage: string
  environmental_conditions: string
  prevention: string[]
  control_methods: string[]
  uncertainty: string
  citation_point_ids: string[]
}

export interface DiagnosisReference {
  point_id: string
  document_id: number
  title: string
  source_organization: string
  source_url: string | null
  publication_date: string | null
  region: string | null
  locator: string
}

export interface DiagnosisReport {
  id: number
  task_id: number
  status: 'completed'
  llm_provider: string
  llm_model: string
  prompt_version: string
  report: {
    summary: string
    detected_entities: DiagnosedEntity[]
    references: DiagnosisReference[]
    disclaimer: string
  }
  usage: {
    prompt_tokens: number | null
    completion_tokens: number | null
    total_tokens: number | null
  }
  created_at: string
  completed_at: string
}

export async function generateDiagnosis(
  taskId: number,
): Promise<DiagnosisReport> {
  const response = await apiClient.post<DiagnosisReport>(
    `/detections/${taskId}/diagnosis`,
  )
  return response.data
}

export async function fetchDiagnosis(
  taskId: number,
): Promise<DiagnosisReport> {
  const response = await apiClient.get<DiagnosisReport>(`/reports/${taskId}`)
  return response.data
}
