import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { uploadPestImage, type DetectionResult } from '../src/api/detections'
import { useDetectionStore } from '../src/stores/detection'

vi.mock('../src/api/detections', () => ({
  uploadPestImage: vi.fn(),
}))

const completedResult: DetectionResult = {
  task_id: 7,
  status: 'completed',
  detections: [
    {
      class_id: 0,
      class_name: 'rice leaf folder',
      confidence: 0.91,
      bbox: { x1: 1, y1: 2, x2: 30, y2: 40 },
      normalization_status: 'verified',
      normalized_entity_id: 1,
      entity_code: 'ip102-class-000',
      common_name: '稻纵卷叶螟',
      knowledge_status: 'reviewed',
    },
  ],
  annotated_image_url: '/media/annotated/result.jpg',
  inference_ms: 18.5,
  device: '0',
}

describe('detection store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('stores a completed API result', async () => {
    vi.mocked(uploadPestImage).mockResolvedValue(completedResult)
    const store = useDetectionStore()
    const file = new File(['image'], 'pest.jpg', { type: 'image/jpeg' })

    await store.detect(file)

    expect(uploadPestImage).toHaveBeenCalledWith(file)
    expect(store.state).toBe('completed')
    expect(store.result?.task_id).toBe(7)
    expect(store.errorMessage).toBe('')
  })

  it('keeps a readable failure and clears stale results', async () => {
    vi.mocked(uploadPestImage).mockRejectedValue(
      new Error('模型暂时不可用'),
    )
    const store = useDetectionStore()
    const file = new File(['image'], 'pest.jpg', { type: 'image/jpeg' })

    await store.detect(file)

    expect(store.state).toBe('failed')
    expect(store.result).toBeNull()
    expect(store.errorMessage).toBe('模型暂时不可用')
  })
})
