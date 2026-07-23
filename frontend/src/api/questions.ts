import type { DiagnosisReference } from './diagnosis'
import { apiClient } from './http'

export interface KnowledgeQuestionAnswer {
  task_id: number
  question: string
  planned_queries: string[]
  answer: string
  uncertainty: string
  references: DiagnosisReference[]
}

export async function askKnowledgeQuestion(
  taskId: number,
  question: string,
): Promise<KnowledgeQuestionAnswer> {
  const response = await apiClient.post<KnowledgeQuestionAnswer>(
    `/detections/${taskId}/questions`,
    { question },
  )
  return response.data
}
