<script setup lang="ts">
import { computed } from 'vue'
import type { Detection } from '../api/detections'
import { useDiagnosisStore } from '../stores/diagnosis'

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

    <template v-if="diagnosisStore.report">
      <p class="report-summary">
        {{ diagnosisStore.report.report.summary }}
      </p>

      <article
        v-for="entity in diagnosisStore.report.report.detected_entities"
        :key="entity.entity_id"
        class="entity-report"
      >
        <div class="entity-report-heading">
          <div>
            <span>识别实体</span>
            <h3>{{ entity.name }}</h3>
          </div>
          <strong>{{ (entity.confidence * 100).toFixed(1) }}%</strong>
        </div>

        <dl class="report-fields">
          <div>
            <dt>基本介绍</dt>
            <dd>{{ entity.introduction }}</dd>
          </div>
          <div>
            <dt>典型特征</dt>
            <dd>{{ entity.typical_features }}</dd>
          </div>
          <div>
            <dt>主要危害</dt>
            <dd>{{ entity.damage }}</dd>
          </div>
          <div>
            <dt>发生条件</dt>
            <dd>{{ entity.environmental_conditions }}</dd>
          </div>
          <div>
            <dt>寄主植物</dt>
            <dd>{{ entity.host_plants.join('、') }}</dd>
          </div>
          <div>
            <dt>不确定性</dt>
            <dd>{{ entity.uncertainty }}</dd>
          </div>
        </dl>

        <div class="recommendation-grid">
          <div>
            <h4>预防措施</h4>
            <ul>
              <li v-for="item in entity.prevention" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div>
            <h4>防治建议</h4>
            <ul>
              <li v-for="item in entity.control_methods" :key="item">
                {{ item }}
              </li>
            </ul>
          </div>
        </div>
      </article>

      <section class="reference-section">
        <h3>资料来源</h3>
        <ol>
          <li
            v-for="reference in diagnosisStore.report.report.references"
            :key="reference.point_id"
          >
            <a
              v-if="reference.source_url"
              :href="reference.source_url"
              target="_blank"
              rel="noreferrer"
            >
              {{ reference.title }}
            </a>
            <strong v-else>{{ reference.title }}</strong>
            <span>
              {{ reference.source_organization }} · {{ reference.locator }}
            </span>
          </li>
        </ol>
      </section>

      <p class="report-disclaimer">
        {{ diagnosisStore.report.report.disclaimer }}
      </p>
    </template>
  </section>
</template>
