import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  generateDiagnosis,
  type DiagnosisReport,
} from '../src/api/diagnosis'
import { useDiagnosisStore } from '../src/stores/diagnosis'

vi.mock('../src/api/diagnosis', () => ({
  generateDiagnosis: vi.fn(),
}))

const completedReport: DiagnosisReport = {
  id: 1,
  task_id: 7,
  status: 'completed',
  llm_provider: 'ollama',
  llm_model: 'qwen3:4b',
  prompt_version: 'diagnosis-entity-v1',
  report: {
    summary: '检测到稻纵卷叶螟。',
    detected_entities: [],
    references: [],
    disclaimer: '结果仅供参考。',
  },
  usage: {
    prompt_tokens: 10,
    completion_tokens: 20,
    total_tokens: 30,
  },
  created_at: '2026-07-23T12:00:00Z',
  completed_at: '2026-07-23T12:00:01Z',
}

describe('diagnosis store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('stores a completed evidence-bound report', async () => {
    vi.mocked(generateDiagnosis).mockResolvedValue(completedReport)
    const store = useDiagnosisStore()

    await store.generate(7)

    expect(generateDiagnosis).toHaveBeenCalledWith(7)
    expect(store.state).toBe('completed')
    expect(store.report?.usage.total_tokens).toBe(30)
  })

  it('preserves a readable provider failure', async () => {
    vi.mocked(generateDiagnosis).mockRejectedValue(
      new Error('本地模型暂时不可用'),
    )
    const store = useDiagnosisStore()

    await store.generate(7)

    expect(store.state).toBe('failed')
    expect(store.report).toBeNull()
    expect(store.errorMessage).toBe('本地模型暂时不可用')
  })
})
