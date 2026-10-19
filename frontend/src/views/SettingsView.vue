<template>
  <div class="settings-page">
    <div class="settings-grid">
      <!-- 个人信息 -->
      <div class="page-card profile-card">
        <div class="card-title serif">
          <el-icon><User /></el-icon>
          个人信息
        </div>
        <div class="avatar-block">
          <el-avatar :size="88" :src="auth.user?.avatar || ''" class="big-avatar">
            {{ (auth.user?.nickname || auth.user?.username || "?").slice(0, 1) }}
          </el-avatar>
          <div class="avatar-side">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="onAvatarPicked" accept=".png,.jpg,.jpeg,.gif,.webp,.svg">
              <el-button size="small" :loading="avatarUploading">
                <el-icon><Picture /></el-icon>&nbsp;更换头像
              </el-button>
            </el-upload>
            <span class="avatar-tip">支持 png / jpg / gif / webp / svg，5MB 以内</span>
            <el-tag size="small" effect="dark" :type="statusTag" round>
              {{ statusLabel }}
            </el-tag>
          </div>
        </div>
        <el-form label-width="90px" class="profile-form" @submit.prevent>
          <el-form-item label="用户名">
            <el-input :model-value="auth.user?.username" disabled />
          </el-form-item>
          <el-form-item label="当前身份">
            <el-input :model-value="auth.roleLabel" disabled />
          </el-form-item>
          <el-form-item label="注册时间">
            <el-input :model-value="fmt(auth.user?.created_at)" disabled />
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="nickname" maxlength="20" show-word-limit placeholder="设置展示昵称" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存昵称</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 修改密码 -->
      <div class="page-card pwd-card">
        <div class="card-title serif">
          <el-icon><Lock /></el-icon>
          修改密码
        </div>
        <el-alert type="info" :closable="false" show-icon title="修改密码需提供原密码，新密码长度不少于 6 位" class="pwd-alert" />
        <el-form label-width="90px" class="pwd-form" @submit.prevent>
          <el-form-item label="原密码">
            <el-input v-model="pwdOld" type="password" show-password placeholder="请输入原密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwdNew" type="password" show-password placeholder="请输入新密码" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="pwdConfirm" type="password" show-password placeholder="再次输入新密码" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changingPwd" @click="changePwd">确认修改</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { User, Lock, Picture } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";
import { userApi, errMsg } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const nickname = ref(auth.user?.nickname || "");
const savingProfile = ref(false);
const avatarUploading = ref(false);

const pwdOld = ref("");
const pwdNew = ref("");
const pwdConfirm = ref("");
const changingPwd = ref(false);

const statusLabel = computed(() => ({ online: "在线", offline: "离线", invisible: "隐身" }[auth.user?.status || "offline"] || "离线"));
const statusTag = computed(() => (auth.user?.status === "online" ? "success" : auth.user?.status === "invisible" ? "info" : "warning"));

function fmt(s?: string) {
  if (!s) return "-";
  const d = new Date(s);
  const p = (n: number) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}

async function saveProfile() {
  const name = nickname.value.trim();
  if (!name) {
    ElMessage.warning("昵称不能为空");
    return;
  }
  savingProfile.value = true;
  try {
    const u = await userApi.updateMe({ nickname: name });
    auth.updateUser(u);
    ElMessage.success("个人信息已保存");
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    savingProfile.value = false;
  }
}

async function onAvatarPicked(file: UploadFile) {
  if (!file.raw) return;
  avatarUploading.value = true;
  try {
    const res = await userApi.uploadAvatar(file.raw);
    const u = await userApi.updateMe({ avatar: res.avatar });
    auth.updateUser(u);
    ElMessage.success("头像已更新");
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    avatarUploading.value = false;
  }
}

async function changePwd() {
  if (!pwdOld.value || !pwdNew.value) {
    ElMessage.warning("请填写完整");
    return;
  }
  if (pwdNew.value.length < 6) {
    ElMessage.warning("新密码长度不少于 6 位");
    return;
  }
  if (pwdNew.value !== pwdConfirm.value) {
    ElMessage.warning("两次输入的新密码不一致");
    return;
  }
  changingPwd.value = true;
  try {
    const u = await userApi.changePassword({ old_password: pwdOld.value, new_password: pwdNew.value });
    auth.updateUser(u);
    pwdOld.value = "";
    pwdNew.value = "";
    pwdConfirm.value = "";
    ElMessage.success("密码修改成功，下次登录请使用新密码");
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    changingPwd.value = false;
  }
}
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 1000px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 700;
  color: var(--al-text);
  margin-bottom: 16px;
}
.avatar-block {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 18px;
}
.big-avatar {
  background: linear-gradient(135deg, var(--al-navy), var(--al-navy-2));
  color: var(--al-gold-2);
  font-size: 34px;
  font-weight: 700;
  flex-shrink: 0;
}
.avatar-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
.avatar-tip {
  font-size: 12px;
  color: var(--al-text-sub);
}
.pwd-alert {
  margin-bottom: 14px;
}
</style>