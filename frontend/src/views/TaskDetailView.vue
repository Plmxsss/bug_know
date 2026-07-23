<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchDiagnosis, type DiagnosisReport } from '../api/diagnosis'
import {
  fetchDetectionTask,
  type DetectionTaskDetail,
} from '../api/detections'
import { apiErrorCode, apiErrorMessage } from '../api/http'
import DiagnosisReportContent from '../components/DiagnosisReportContent.vue'

const route = useRoute()
const task = ref<DetectionTaskDetail | null>(null)
const report = ref<DiagnosisReport | null>(null)
const loading = ref(true)
const errorMessage = ref('')

function statusText(status: DetectionTaskDetail['status']): string {
  const labels: Record<DetectionTaskDetail['status'], string> = {
    pending: '等待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  }
  return labels[status]
}

async function loadTask(): Promise<void> {
  const taskId = Number(route.params.taskId)
  if (!Number.isInteger(taskId) || taskId < 1) {
    errorMessage.value = '任务编号无效。'
    loading.value = false
    return
  }

  try {
    task.value = await fetchDetectionTask(taskId)
    try {
      report.value = await fetchDiagnosis(taskId)
    } catch (error) {
      if (apiErrorCode(error) !== 'DIAGNOSIS_REPORT_NOT_FOUND') {
        throw error
      }
    }
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    loading.value = false
  }
}

onMounted(loadTask)
</script>

<template>
  <section class="task-detail-page">
    <RouterLink class="back-link" to="/history">← 返回历史记录</RouterLink>

    <div v-if="loading" class="history-empty">正在读取任务详情…</div>
    <p v-else-if="errorMessage" class="form-error">{{ errorMessage }}</p>

    <template v-else-if="task">
      <div class="task-detail-heading">
        <div>
          <p class="eyebrow">DETECTION TASK</p>
          <h1>任务 #{{ task.id }}</h1>
        </div>
        <span class="task-status" :class="`task-${task.status}`">
          {{ statusText(task.status) }}
        </span>
      </div>

      <div class="task-detail-grid">
        <div class="task-detail-image">
          <img
            v-if="task.annotated_image_url"
            :src="task.annotated_image_url"
            :alt="`任务 ${task.id} 的标注结果`"
          />
          <span v-else>该任务没有标注图</span>
        </div>

        <div class="task-object-panel">
          <h2>检测目标</h2>
          <p v-if="task.detections.length === 0">没有检测到目标。</p>
          <ul v-else>
            <li v-for="item in task.detections" :key="item.object_id">
              <div>
                <strong>{{ item.raw_class_name }}</strong>
                <small>
                  框坐标 {{ item.bbox.x1.toFixed(0) }},
                  {{ item.bbox.y1.toFixed(0) }} -
                  {{ item.bbox.x2.toFixed(0) }},
                  {{ item.bbox.y2.toFixed(0) }}
                </small>
              </div>
              <span>{{ (item.confidence * 100).toFixed(1) }}%</span>
            </li>
          </ul>
        </div>
      </div>

      <section v-if="report" class="diagnosis-panel">
        <div class="diagnosis-header">
          <div>
            <p class="panel-label">PERSISTED REPORT</p>
            <h2>已保存的农业知识诊断</h2>
          </div>
          <span class="stored-report-meta">
            {{ report.llm_provider }} · {{ report.llm_model }}
          </span>
        </div>
        <DiagnosisReportContent :report="report" />
      </section>

      <p v-else class="diagnosis-notice">该任务尚未生成知识诊断报告。</p>
    </template>
  </section>
</template>
