import { apiClient } from './http'

export interface BoundingBox {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface Detection {
  class_id: number
  class_name: string
  confidence: number
  bbox: BoundingBox
  normalization_status: 'unmapped' | 'needs_review' | 'verified'
  normalized_entity_id: number | null
  entity_code: string | null
  common_name: string | null
  knowledge_status: 'missing' | 'draft' | 'reviewed' | null
}

export interface DetectionResult {
  task_id: number
  status: 'completed'
  detections: Detection[]
  annotated_image_url: string
  inference_ms: number
  device: string
}

export async function uploadPestImage(file: File): Promise<DetectionResult> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await apiClient.post<DetectionResult>(
    '/detections',
    formData,
  )
  return response.data
}
