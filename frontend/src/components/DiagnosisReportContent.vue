<script setup lang="ts">
import type { DiagnosisReport } from '../api/diagnosis'

defineProps<{
  report: DiagnosisReport
}>()
</script>

<template>
  <p class="report-summary">{{ report.report.summary }}</p>

  <article
    v-for="entity in report.report.detected_entities"
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
          <li v-for="item in entity.control_methods" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </article>

  <section class="reference-section">
    <h3>资料来源</h3>
    <ol>
      <li
        v-for="reference in report.report.references"
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
        <span>{{ reference.source_organization }} · {{ reference.locator }}</span>
      </li>
    </ol>
  </section>

  <p class="report-disclaimer">{{ report.report.disclaimer }}</p>
</template>
