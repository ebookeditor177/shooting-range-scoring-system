import { createRouter, createWebHistory } from 'vue-router'
import ClientView from '@/views/ClientView.vue'
import AdminView from '@/views/AdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/client/1'
    },
    {
      path: '/client/:lane',
      name: 'client',
      component: ClientView,
      props: true
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView
    }
  ]
})

export default router
