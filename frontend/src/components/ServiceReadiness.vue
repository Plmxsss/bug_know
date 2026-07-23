<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchReadiness, type ReadinessResponse } from '../api/health'

type CheckState = 'loading' | 'ready' | 'unavailable'

const state = ref<CheckState>('loading')
const readiness = ref<ReadinessResponse | null>(null)
const errorMessage = ref('')

const statusText = computed(() => {
  if (state.value === 'loading') return '正在连接'
  if (state.value === 'ready') return '服务可用'
  return '暂时不可用'
})

async function checkServices(): Promise<void> {
  state.value = 'loading'
  errorMessage.value = ''

  try {
    readiness.value = await fetchReadiness()
    state.value = 'ready'
  } catch (error) {
    readiness.value = null
    state.value = 'unavailable'
    errorMessage.value =
      error instanceof Error ? error.message : '无法连接 FastAPI'
  }
}

onMounted(checkServices)
</script>

<template>
  <aside class="readiness-card" aria-live="polite">
    <div class="readiness-heading">
      <div>
        <p class="panel-label">SYSTEM READINESS</p>
        <h2>后端服务状态</h2>
      </div>
      <span class="status-pill" :class="`status-${state}`">
        <i aria-hidden="true"></i>
        {{ statusText }}
      </span>
    </div>

    <dl class="service-list">
      <div>
        <dt>FastAPI</dt>
        <dd :class="{ healthy: state === 'ready' }">
          {{ state === 'loading' ? '检查中' : state === 'ready' ? '正常' : '异常' }}
        </dd>
      </div>
      <div>
        <dt>MySQL</dt>
        <dd :class="{ healthy: readiness?.database === 'ok' }">
          {{ readiness?.database === 'ok' ? '已连接' : '等待连接' }}
        </dd>
      </div>
      <div>
        <dt>Qdrant</dt>
        <dd :class="{ healthy: readiness?.vector_database === 'ok' }">
          {{ readiness?.vector_database === 'ok' ? '已连接' : '等待连接' }}
        </dd>
      </div>
    </dl>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <button type="button" class="secondary-action" @click="checkServices">
      重新检查
    </button>
  </aside>
</template>
