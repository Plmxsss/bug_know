<script setup lang="ts">
import ServiceReadiness from './components/ServiceReadiness.vue'

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
  <div class="page-shell">
    <header class="site-header">
      <a class="brand" href="/" aria-label="AgriGuard AI 首页">
        <span class="brand-mark" aria-hidden="true">AG</span>
        <span>
          <strong>AgriGuard AI</strong>
          <small>农业害虫智能分析平台</small>
        </span>
      </a>
      <span class="stage-badge">开发阶段 · 系统基线</span>
    </header>

    <main>
      <section class="hero-section">
        <div class="hero-copy">
          <p class="eyebrow">IP102 · YOLO · RAG · QWEN</p>
          <h1>让每一次识别，<br />都有资料可追溯。</h1>
          <p class="hero-description">
            从害虫目标检测到农业知识检索，再到结构化诊断报告。
            检测事实、知识来源和模型总结始终清晰分离。
          </p>
          <a class="primary-action" href="#workflow">
            查看分析流程
            <span aria-hidden="true">→</span>
          </a>
        </div>

        <ServiceReadiness />
      </section>

      <section id="workflow" class="workflow-section">
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
    </main>

    <footer>
      <span>AgriGuard AI</span>
      <span>结果仅供农业生产参考</span>
    </footer>
  </div>
</template>
