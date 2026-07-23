<script setup lang="ts">
import { computed } from 'vue'
import type { Detection } from '../api/detections'
import { useDiagnosisStore } from '../stores/diagnosis'
import DiagnosisReportContent from './DiagnosisReportContent.vue'

const props = defineProps<{
  taskId: number
  detections: Detection[]
}>()

const diagnosisStore = useDiagnosisStore()
const eligible = computed(
  () =>
    props.detections.length > 0 &&
    props.detections.every(
      (item) =>
        item.normalization_status === 'verified' &&
        item.knowledge_status === 'reviewed',
    ),
)

const eligibilityMessage = computed(() => {
  if (props.detections.length === 0) {
    return '没有检测到害虫，无法生成知识诊断。'
  }
  if (!eligible.value) {
    return '存在尚未审核的类别映射或知识资料，当前不能生成诊断。'
  }
  return ''
})
</script>

<template>
  <section class="diagnosis-panel">
    <div class="diagnosis-header">
      <div>
        <p class="panel-label">EVIDENCE-BOUND REPORT</p>
        <h2>农业知识诊断</h2>
      </div>
      <button
        type="button"
        class="diagnosis-action"
        :disabled="!eligible || diagnosisStore.state === 'generating'"
        @click="diagnosisStore.generate(taskId)"
      >
        {{
          diagnosisStore.state === 'generating'
            ? '正在检索资料并生成…'
            : diagnosisStore.report
              ? '读取已保存报告'
              : '生成知识诊断'
        }}
      </button>
    </div>

    <p v-if="eligibilityMessage" class="diagnosis-notice">
      {{ eligibilityMessage }}
    </p>
    <p v-if="diagnosisStore.errorMessage" class="form-error">
      {{ diagnosisStore.errorMessage }}
    </p>

    <DiagnosisReportContent
      v-if="diagnosisStore.report"
      :report="diagnosisStore.report"
    />
  </section>
</template>
