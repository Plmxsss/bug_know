<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDetectionTasks,
  type DetectionTask,
} from '../api/detections'
import { apiErrorMessage } from '../api/http'

const pageSize = 9
const tasks = ref<DetectionTask[]>([])
const currentPage = ref(1)
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
)

function statusText(status: DetectionTask['status']): string {
  const labels: Record<DetectionTask['status'], string> = {
    pending: '等待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

async function loadPage(page: number): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    const result = await fetchDetectionTasks(page, pageSize)
    tasks.value = result.items
    total.value = result.total
    currentPage.value = result.page
  } catch (error) {
    tasks.value = []
    errorMessage.value = apiErrorMessage(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => loadPage(1))
</script>

<template>
  <section class="history-page">
    <div class="history-heading">
      <div>
        <p class="eyebrow">DETECTION HISTORY</p>
        <h1>历史检测记录</h1>
        <p>数据来自 MySQL，刷新页面后仍然可以查询。</p>
      </div>
      <span>{{ total }} 条记录</span>
    </div>

    <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

    <div v-if="loading" class="history-empty">正在读取检测记录…</div>
    <div v-else-if="tasks.length === 0" class="history-empty">
      暂无检测记录，请先上传一张图片。
    </div>

    <ul v-else class="history-grid">
      <li v-for="task in tasks" :key="task.id" class="history-card">
        <div class="history-image">
          <img
            v-if="task.annotated_image_url"
            :src="task.annotated_image_url"
            :alt="`任务 ${task.id} 的标注结果`"
          />
          <span v-else>暂无标注图</span>
        </div>
        <div class="history-card-body">
          <div>
            <strong>任务 #{{ task.id }}</strong>
            <span class="task-status" :class="`task-${task.status}`">
              {{ statusText(task.status) }}
            </span>
          </div>
          <time :datetime="task.created_at">{{ formatTime(task.created_at) }}</time>
          <small>模型版本 ID {{ task.model_version_id }}</small>
          <p v-if="task.status === 'failed'">
            任务执行失败，请查看后端日志了解详细原因。
          </p>
        </div>
      </li>
    </ul>

    <nav v-if="totalPages > 1" class="pagination" aria-label="历史记录分页">
      <button
        type="button"
        :disabled="currentPage <= 1 || loading"
        @click="loadPage(currentPage - 1)"
      >
        上一页
      </button>
      <span>{{ currentPage }} / {{ totalPages }}</span>
      <button
        type="button"
        :disabled="currentPage >= totalPages || loading"
        @click="loadPage(currentPage + 1)"
      >
        下一页
      </button>
    </nav>
  </section>
</template>
