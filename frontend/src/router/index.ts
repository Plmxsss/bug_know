import { createRouter, createWebHistory } from 'vue-router'
import DetectionView from '../views/DetectionView.vue'
import HistoryView from '../views/HistoryView.vue'
import HomeView from '../views/HomeView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/detect',
      name: 'detection',
      component: DetectionView,
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView,
    },
  ],
})
