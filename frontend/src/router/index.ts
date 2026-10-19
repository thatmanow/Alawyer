import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/cover" },
    { path: "/cover", name: "cover", component: () => import("@/views/CoverView.vue") },
    {
      path: "/",
      component: () => import("@/components/AppLayout.vue"),
      children: [
        { path: "home", name: "home", component: () => import("@/views/HomeView.vue"), meta: { title: "主页" } },
        { path: "chat", name: "chat", component: () => import("@/views/ChatView.vue"), meta: { title: "AI 问答" } },
        { path: "contract", name: "contract", component: () => import("@/views/ContractView.vue"), meta: { title: "合同审查" } },
        { path: "knowledge", name: "knowledge", component: () => import("@/views/KnowledgeView.vue"), meta: { title: "知识库" } },
        { path: "users", name: "users", component: () => import("@/views/UserManageView.vue"), meta: { title: "用户管理", adminOnly: true } },
        { path: "settings", name: "settings", component: () => import("@/views/SettingsView.vue"), meta: { title: "个人设置" } },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/cover" },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.name !== "cover" && !auth.isLoggedIn) {
    return { name: "cover" };
  }
  if (to.meta.adminOnly && auth.user?.role !== "super_admin") {
    return { name: "home" };
  }
});

export default router;