<script setup lang="ts">
import { RouterLink } from 'vue-router'
import ServiceReadiness from '../components/ServiceReadiness.vue'

const stages = [
  {
    number: '01',
    title: '上传虫害图像',
    description: '校验图片内容，并为本次分析建立可追踪任务。',
  },
  {
    number: '02',
    title: 'YOLO 目标检测',
    description: '返回害虫类别、置信度、位置和标注后的图片。',
  },
  {
    number: '03',
    title: '知识检索与诊断',
    description: '只使用已审核资料，由 Qwen 生成带来源的结构化报告。',
  },
]
</script>

<template>
  <section class="hero-section">
    <div class="hero-copy">
      <p class="eyebrow">IP102 · YOLO · RAG · QWEN</p>
      <h1>让每一次识别，<br />都有资料可追溯。</h1>
      <p class="hero-description">
        从害虫目标检测到农业知识检索，再到结构化诊断报告。
        检测事实、知识来源和模型总结始终清晰分离。
      </p>
      <RouterLink class="primary-action" to="/detect">
        开始害虫识别
        <span aria-hidden="true">→</span>
      </RouterLink>
    </div>

    <ServiceReadiness />
  </section>

  <section class="workflow-section">
    <div class="section-heading">
      <p class="eyebrow">WORKFLOW</p>
      <h2>一次分析如何完成</h2>
    </div>

    <ol class="stage-grid">
      <li v-for="stage in stages" :key="stage.number" class="stage-card">
        <span class="stage-number">{{ stage.number }}</span>
        <h3>{{ stage.title }}</h3>
        <p>{{ stage.description }}</p>
      </li>
    </ol>
  </section>
</template>
