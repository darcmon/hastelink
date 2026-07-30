import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from 'vue-router';
import LoginView from '../views/LoginView.vue';
import AuthCallbackView from '../views/AuthCallbackView.vue';
import DashboardView from '../views/DashboardView.vue';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: AuthCallbackView,
    meta: { public: true },
  },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/', redirect: '/dashboard' },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const token = localStorage.getItem('token');
  if (!to.meta.public && !token) {
    return { name: 'login' };
  }
});

export default router;
