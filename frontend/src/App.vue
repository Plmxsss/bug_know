<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="page-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/" aria-label="AgriGuard AI 首页">
        <span class="brand-mark" aria-hidden="true">AG</span>
        <span>
          <strong>AgriGuard AI</strong>
          <small>农业害虫智能分析平台</small>
        </span>
      </RouterLink>

      <nav class="site-nav" aria-label="主要导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/detect">害虫识别</RouterLink>
        <RouterLink to="/history">历史记录</RouterLink>
      </nav>
    </header>

    <main>
      <RouterView />
    </main>

    <footer>
      <span>AgriGuard AI</span>
      <span>结果仅供农业生产参考</span>
    </footer>
  </div>
</template>
