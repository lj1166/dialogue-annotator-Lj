import { createRouter, createWebHistory } from 'vue-router'
import AnnotateView from '../views/AnnotateView.vue'
import StatsView from '../views/StatsView.vue'

const routes = [
  { path: '/', redirect: '/annotate' },
  { path: '/annotate', name: 'annotate', component: AnnotateView },
  { path: '/stats', name: 'stats', component: StatsView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
