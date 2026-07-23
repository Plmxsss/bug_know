import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  generateDiagnosis,
  type DiagnosisReport,
} from '../api/diagnosis'
import { apiErrorMessage } from '../api/http'

type DiagnosisState = 'idle' | 'generating' | 'completed' | 'failed'

export const useDiagnosisStore = defineStore('diagnosis', () => {
  const state = ref<DiagnosisState>('idle')
  const report = ref<DiagnosisReport | null>(null)
  const errorMessage = ref('')

  async function generate(taskId: number): Promise<void> {
    state.value = 'generating'
    report.value = null
    errorMessage.value = ''

    try {
      report.value = await generateDiagnosis(taskId)
      state.value = 'completed'
    } catch (error) {
      errorMessage.value = apiErrorMessage(error)
      state.value = 'failed'
    }
  }

  function reset(): void {
    state.value = 'idle'
    report.value = null
    errorMessage.value = ''
  }

  return {
    state,
    report,
    errorMessage,
    generate,
    reset,
  }
})
