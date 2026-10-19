<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand" @click="router.push('/home')">
        <img :src="logoUrl" alt="alawyer logo" class="brand-logo" />
        <div class="brand-text">
          <span class="brand-name serif">alawyer</span>
          <span class="brand-sub">智能法律顾问平台</span>
        </div>
      </div>
      <el-menu :default-active="route.path" router class="sidebar-menu" :collapse="false">
        <el-menu-item index="/home">
          <el-icon><Odometer /></el-icon>
          <span>主页</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 问答</span>
        </el-menu-item>
        <el-menu-item index="/contract">
          <el-icon><DocumentChecked /></el-icon>
          <span>合同审查</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item v-if="auth.user?.role === 'super_admin'" index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>个人设置</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-tag :type="roleTagType" effect="dark" size="small" round>{{ auth.roleLabel }}</el-tag>
        <div class="server-time">{{ nowText }}</div>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="topbar-title serif">{{ route.meta.title || "alawyer" }}</div>
        <div class="topbar-actions">
          <el-tooltip :content="theme.mode === 'dark' ? '切换为浅色模式' : '切换为深色模式'">
            <el-button circle size="default" @click="theme.toggle()">
              <el-icon :size="17">
                <Sunny v-if="theme.mode === 'dark'" />
                <Moon v-else />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown trigger="click" @command="onStatusCommand">
            <div class="avatar-wrap">
              <el-badge :is-dot="auth.user?.status === 'online'" type="success" class="status-dot">
                <el-avatar :size="36" :src="avatarSrc" class="avatar">
                  <span class="avatar-fallback">{{ (auth.user?.nickname || "A").slice(0, 1) }}</span>
                </el-avatar>
              </el-badge>
              <div class="avatar-meta">
                <div class="avatar-name">{{ auth.user?.nickname }}</div>
                <div class="avatar-status">{{ statusText }}</div>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>在线状态</el-dropdown-item>
                <el-dropdown-item command="online">
                  <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>在线
                </el-dropdown-item>
                <el-dropdown-item command="offline">
                  <el-icon color="#909399"><RemoveFilled /></el-icon>离线
                </el-dropdown-item>
                <el-dropdown-item command="invisible">
                  <el-icon color="#e6a23c"><Hide /></el-icon>隐身
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import logoUrl from "@/assets/logo.png";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { userApi, errMsg } from "@/api";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const nowText = ref("");
let timer: number | undefined;

function tick() {
  nowText.value = new Date().toLocaleString("zh-CN", { hour12: false });
}

onMounted(() => {
  tick();
  timer = window.setInterval(tick, 1000);
  auth.refreshMe();
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});

const avatarSrc = computed(() => (auth.user?.avatar ? auth.user.avatar : ""));
const statusText = computed(
  () => ({ online: "在线", offline: "离线", invisible: "隐身" }[auth.user?.status || "offline"] || "离线")
);
const roleTagType = computed(
  () =>
    ({ super_admin: "danger", lawyer: "warning", user: "" } as Record<string, any>)[
      auth.user?.role || "user"
    ]
);

async function onStatusCommand(cmd: string) {
  if (cmd === "logout") {
    auth.logout();
    router.push("/cover");
    return;
  }
  try {
    await userApi.updateStatus(cmd);
    auth.updateUser({ status: cmd });
    ElMessage.success(`已切换为${{ online: "在线", offline: "离线", invisible: "隐身" }[cmd]}`);
  } catch (e) {
    ElMessage.error(errMsg(e));
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 225px;
  flex-shrink: 0;
  background: linear-gradient(180deg, var(--al-navy) 0%, #0b1a30 100%);
  display: flex;
  flex-direction: column;
  padding: 18px 12px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 18px;
  cursor: pointer;
}

.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid rgba(227, 200, 143, 0.4);
  background: #fff;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand-name {
  color: #fff;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand-sub {
  color: var(--al-gold-2);
  font-size: 11px;
  letter-spacing: 1px;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

:deep(.sidebar-menu .el-menu-item) {
  color: #b9c4d4;
  border-radius: 9px;
  margin: 4px 0;
  height: 46px;
}

:deep(.sidebar-menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.07);
  color: #fff;
}

:deep(.sidebar-menu .el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(201, 165, 92, 0.25), rgba(201, 165, 92, 0.08));
  color: var(--al-gold-2);
}

.sidebar-footer {
  padding: 12px 10px 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.09);
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.server-time {
  color: #7d8ea5;
  font-size: 11.5px;
  font-family: Consolas, monospace;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  height: 62px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 26px;
  background: var(--al-card);
  border-bottom: 1px solid var(--al-border);
}

.topbar-title {
  font-size: 19px;
  font-weight: 700;
  color: var(--al-text);
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 18px;
}

.avatar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  transition: background 0.2s;
}

.avatar-wrap:hover {
  background: var(--al-bg);
}

.avatar {
  background: var(--al-navy-2);
  color: #fff;
  font-weight: 700;
}

.avatar-meta {
  line-height: 1.2;
}

.avatar-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--al-text);
}

.avatar-status {
  font-size: 11.5px;
  color: var(--al-text-sub);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 22px 26px;
}
</style>