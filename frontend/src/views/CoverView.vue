<template>
  <div class="cover-root" @wheel="onWheel" tabindex="0" ref="rootEl">
    <div class="slider" :class="{ moved: moved }">
      <section class="section hero">
        <div class="hero-inner">
          <img :src="logoUrl" class="hero-logo" alt="alawyer logo" />
          <h1 class="hero-title serif">alawyer</h1>
          <p class="hero-sub serif">融汇法学之严谨 · 智启顾问之未来</p>
          <div class="hero-divider"></div>
          <p class="hero-desc">
            学术级法律知识库 × 本地大模型增强检索 × 多智能体合同审查
          </p>
          <div class="hero-badges">
            <span class="badge">RAG 知识增强</span>
            <span class="badge">Neo4j 知识图谱</span>
            <span class="badge">多智能体辩论</span>
            <span class="badge">Cross-Encoder 精排</span>
          </div>
        </div>
        <div class="scroll-hint" @click="moveTo(1)">
          <span>滚动鼠标滚轮 或 按 ↓ 方向键</span>
          <el-icon class="bounce"><ArrowDownBold /></el-icon>
        </div>
        <div class="hero-footer">
          <span>© 2026 alawyer 智能法律顾问平台</span>
          <span>本平台内容仅供学习研究参考，不构成正式法律意见</span>
        </div>
      </section>

      <section class="section login-section">
        <div class="login-panel">
          <div class="login-left">
            <img :src="logoUrl" class="login-logo" alt="logo" />
            <h2 class="serif">欢迎来到 alawyer</h2>
            <p>登录或注册，开启您的智能法律顾问之旅</p>
            <ul class="login-tips">
              <li>用户名以 <b>admin</b> 开头注册为超级管理员</li>
              <li>用户名以 <b>lawyer</b> 开头注册为律师</li>
              <li>其他用户名为普通用户</li>
            </ul>
            <el-button text class="back-btn" @click="moveTo(0)">
              <el-icon><ArrowUpBold /></el-icon>&nbsp;返回封面
            </el-button>
          </div>
          <div class="login-right">
            <el-tabs v-model="tab" stretch>
              <el-tab-pane label="登录" name="login">
                <el-form :model="loginForm" label-position="top" size="large" @keyup.enter="doLogin">
                  <el-form-item label="用户名">
                    <el-input v-model="loginForm.username" placeholder="如 user01 / lawyer01 / admin" clearable>
                      <template #prefix><el-icon><User /></el-icon></template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="密码">
                    <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码">
                      <template #prefix><el-icon><Lock /></el-icon></template>
                    </el-input>
                  </el-form-item>
                  <el-button type="primary" class="submit-btn" :loading="loading" @click="doLogin">
                    登 录
                  </el-button>
                </el-form>
              </el-tab-pane>
              <el-tab-pane label="注册" name="register">
                <el-form :model="regForm" label-position="top" size="large" @keyup.enter="doRegister">
                  <el-form-item label="用户名">
                    <el-input v-model="regForm.username" placeholder="admin* 超管 / lawyer* 律师 / 其他为用户" clearable>
                      <template #prefix><el-icon><User /></el-icon></template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="昵称（可选）">
                    <el-input v-model="regForm.nickname" placeholder="展示昵称，默认同用户名" clearable>
                      <template #prefix><el-icon><Postcard /></el-icon></template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="密码（至少6位）">
                    <el-input v-model="regForm.password" type="password" show-password placeholder="请设置密码">
                      <template #prefix><el-icon><Lock /></el-icon></template>
                    </el-input>
                  </el-form-item>
                  <el-button type="primary" class="submit-btn" :loading="loading" @click="doRegister">
                    注册并登录
                  </el-button>
                </el-form>
              </el-tab-pane>
            </el-tabs>
            <div class="demo-accounts">
              <span>演示账号：</span>
              <el-tag size="small" @click="fill('admin', 'admin123')" class="tag-btn">admin / admin123</el-tag>
              <el-tag size="small" type="warning" @click="fill('lawyer01', 'lawyer123')" class="tag-btn">lawyer01 / lawyer123</el-tag>
              <el-tag size="small" type="success" @click="fill('user01', 'user123')" class="tag-btn">user01 / user123</el-tag>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import logoUrl from "@/assets/logo.png";
import { useAuthStore } from "@/stores/auth";
import { authApi, errMsg } from "@/api";

const router = useRouter();
const auth = useAuthStore();
const moved = ref(false);
const rootEl = ref<HTMLElement | null>(null);
const tab = ref("login");
const loading = ref(false);
const loginForm = ref({ username: "", password: "" });
const regForm = ref({ username: "", password: "", nickname: "" });
let lock = false;

function moveTo(target: number) {
  if (lock) return;
  lock = true;
  moved.value = target === 1;
  setTimeout(() => (lock = false), 900);
}

function onWheel(e: WheelEvent) {
  if (e.deltaY > 12) moveTo(1);
  else if (e.deltaY < -12) moveTo(0);
}

function onKey(e: KeyboardEvent) {
  const keysDown = ["ArrowDown", "PageDown", " ", "Enter"];
  const keysUp = ["ArrowUp", "PageUp"];
  if (keysDown.includes(e.key)) {
    if (!moved.value) {
      e.preventDefault();
      moveTo(1);
    }
  } else if (keysUp.includes(e.key)) {
    e.preventDefault();
    moveTo(0);
  }
}

onMounted(() => {
  window.addEventListener("keydown", onKey);
  if (auth.isLoggedIn) router.push("/home");
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey);
});

function fill(u: string, p: string) {
  loginForm.value = { username: u, password: p };
  tab.value = "login";
}

async function doLogin() {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const res = await authApi.login(loginForm.value);
    auth.setSession(res.access_token, res.user);
    ElMessage.success(`欢迎回来，${res.user.nickname}`);
    router.push("/home");
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}

async function doRegister() {
  if (!regForm.value.username || !regForm.value.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    await authApi.register({
      username: regForm.value.username,
      password: regForm.value.password,
      nickname: regForm.value.nickname || undefined,
    });
    const res = await authApi.login({
      username: regForm.value.username,
      password: regForm.value.password,
    });
    auth.setSession(res.access_token, res.user);
    ElMessage.success(`注册成功，欢迎加入 alawyer，${res.user.nickname}`);
    router.push("/home");
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.cover-root {
  height: 100vh;
  overflow: hidden;
  outline: none;
  position: relative;
}

.slider {
  height: 200vh;
  transition: transform 0.85s cubic-bezier(0.77, 0, 0.18, 1);
}

.slider.moved {
  transform: translateY(-100vh);
}

.section {
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.hero {
  background:
    radial-gradient(1000px 500px at 80% -10%, rgba(59, 108, 176, 0.45), transparent),
    radial-gradient(800px 460px at 8% 110%, rgba(201, 165, 92, 0.22), transparent),
    linear-gradient(160deg, #0e2038 0%, #10233f 55%, #0b1a30 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-inner {
  text-align: center;
  color: #fff;
  animation: fadeUp 1s ease both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(26px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-logo {
  width: 128px;
  height: 128px;
  border-radius: 26px;
  object-fit: cover;
  border: 2px solid rgba(227, 200, 143, 0.55);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
  background: #fff;
}

.hero-title {
  margin: 22px 0 6px;
  font-size: 58px;
  letter-spacing: 4px;
  color: #fff;
}

.hero-sub {
  font-size: 19px;
  color: var(--al-gold-2);
  letter-spacing: 6px;
  margin: 0;
}

.hero-divider {
  width: 72px;
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--al-gold), transparent);
  margin: 26px auto;
}

.hero-desc {
  color: #c3cedd;
  font-size: 15px;
  letter-spacing: 2px;
}

.hero-badges {
  margin-top: 18px;
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.badge {
  border: 1px solid rgba(227, 200, 143, 0.4);
  color: var(--al-gold-2);
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12.5px;
  background: rgba(201, 165, 92, 0.08);
}

.scroll-hint {
  position: absolute;
  bottom: 56px;
  left: 50%;
  transform: translateX(-50%);
  color: #9fb0c5;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.bounce {
  animation: bounce 1.6s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(9px); }
}

.hero-footer {
  position: absolute;
  bottom: 16px;
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0 26px;
  color: #64788f;
  font-size: 11.5px;
}

.login-section {
  background: var(--al-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-panel {
  display: flex;
  width: min(940px, 92vw);
  min-height: 560px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(10, 22, 40, 0.22);
  border: 1px solid var(--al-border);
}

.login-left {
  flex: 1.05;
  background: linear-gradient(165deg, #14294a 0%, #0d1c33 100%);
  color: #fff;
  padding: 46px 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-logo {
  width: 62px;
  height: 62px;
  border-radius: 14px;
  object-fit: cover;
  border: 1px solid rgba(227, 200, 143, 0.5);
  background: #fff;
}

.login-left h2 {
  margin: 20px 0 8px;
  font-size: 26px;
}

.login-left p {
  color: #b9c4d4;
  font-size: 14px;
  margin: 0 0 20px;
}

.login-tips {
  list-style: none;
  padding: 0;
  margin: 0 0 26px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.login-tips li {
  color: var(--al-gold-2);
  font-size: 13px;
  padding-left: 16px;
  position: relative;
}

.login-tips li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 7px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--al-gold);
}

.back-btn {
  color: #93a7c4;
  align-self: flex-start;
}

.login-right {
  flex: 1.3;
  background: var(--al-card);
  padding: 38px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.submit-btn {
  width: 100%;
  margin-top: 6px;
  height: 44px;
  font-size: 15px;
  letter-spacing: 6px;
  background: linear-gradient(90deg, #1b3a63, #2d5b96);
  border: none;
}

.demo-accounts {
  margin-top: 22px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: var(--al-text-sub);
  font-size: 12.5px;
}

.tag-btn {
  cursor: pointer;
}

@media (max-width: 820px) {
  .login-left { display: none; }
}
</style>