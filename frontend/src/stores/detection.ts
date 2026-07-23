import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  uploadPestImage,
  type DetectionResult,
} from '../api/detections'
import { apiErrorMessage } from '../api/http'

type DetectionState = 'idle' | 'submitting' | 'completed' | 'failed'

export const useDetectionStore = defineStore('detection', () => {
  const state = ref<DetectionState>('idle')
  const result = ref<DetectionResult | null>(null)
  const errorMessage = ref('')

  const isSubmitting = computed(() => state.value === 'submitting')

  async function detect(file: File): Promise<void> {
    state.value = 'submitting'
    result.value = null
    errorMessage.value = ''

    try {
      result.value = await uploadPestImage(file)
      state.value = 'completed'
    } catch (error) {
      errorMessage.value = apiErrorMessage(error)
      state.value = 'failed'
    }
  }

  function reset(): void {
    state.value = 'idle'
    result.value = null
    errorMessage.value = ''
  }

  return {
    state,
    result,
    errorMessage,
    isSubmitting,
    detect,
    reset,
  }
})
