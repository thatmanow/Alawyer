<template>
  <div class="usermanage-page">
    <!-- 概览统计 -->
    <div class="stat-row">
      <div class="page-card stat-card">
        <div class="stat-icon bg-user"><el-icon :size="26"><User /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ userBlock.total }}</div>
          <div class="stat-label">普通用户</div>
        </div>
      </div>
      <div class="page-card stat-card">
        <div class="stat-icon bg-lawyer"><el-icon :size="26"><Suitcase /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ lawyerBlock.total }}</div>
          <div class="stat-label">执业律师</div>
        </div>
      </div>
      <div class="page-card stat-card">
        <div class="stat-icon bg-admin"><el-icon :size="26"><UserFilled /></el-icon></div>
        <div class="stat-info">
          <div class="stat-value">{{ adminBlock.total }}</div>
          <div class="stat-label">超级管理员</div>
        </div>
      </div>
    </div>

    <!-- 用户管理主卡（分块 / 分页 / 查询） -->
    <div class="page-card manage-card">
      <div class="card-title serif">
        <el-icon><UserFilled /></el-icon>
        用户管理
        <span class="manage-tip">律师与普通用户分块展示 · 每页 8 人 · 支持按用户名查询与职位调整</span>
      </div>
      <el-tabs v-model="activeBlock" @tab-change="onBlockChange">
        <el-tab-pane name="user">
          <template #label>
            <el-icon><User /></el-icon>&nbsp;普通用户（{{ userBlock.total }}）
          </template>
          <div class="block-panel">
            <div class="block-toolbar">
              <el-input
                v-model="userBlock.search"
                placeholder="按用户名查询"
                clearable
                style="width: 260px"
                :prefix-icon="Search"
                @keyup.enter="searchUsers('user')"
              />
              <el-button type="primary" @click="searchUsers('user')">查询</el-button>
            </div>
            <el-table :data="userBlock.items" v-loading="userBlock.loading" stripe>
              <el-table-column label="用户" min-width="180">
                <template #default="{ row }">
                  <div class="ut-user">
                    <img class="ut-avatar" :src="row.avatar || ''" onerror="this.style.visibility='hidden'" />
                    <span class="ut-nick">{{ row.nickname || row.username }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="username" label="用户名" width="140" />
              <el-table-column label="当前职位" width="120">
                <template #default="{ row }">
                  <el-tag size="small" effect="dark" :class="'ut-role-' + row.role">{{ roleNames[row.role] || row.role }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="在线状态" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="statusTagType(row.status)" effect="plain">{{ statusNames[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="注册时间" width="130">
                <template #default="{ row }">{{ String(row.created_at || "").slice(0, 10) }}</template>
              </el-table-column>
              <el-table-column label="调整职位" width="160">
                <template #default="{ row }">
                  <el-select :model-value="row.role" size="small" @change="(v: string) => onRoleChange(row, v)">
                    <el-option v-for="v in roleOptions" :key="v" :value="v" :label="roleNames[v]" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>
            <div class="pager-row">
              <el-pagination
                background
                layout="total, prev, pager, next"
                :total="userBlock.total"
                :page-size="8"
                :current-page="userBlock.page"
                @current-change="(p: number) => turnPage('user', p)"
              />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane name="lawyer">
          <template #label>
            <el-icon><Suitcase /></el-icon>&nbsp;律师（{{ lawyerBlock.total }}）
          </template>
          <div class="block-panel">
            <div class="block-toolbar">
              <el-input
                v-model="lawyerBlock.search"
                placeholder="按用户名查询"
                clearable
                style="width: 260px"
                :prefix-icon="Search"
                @keyup.enter="searchUsers('lawyer')"
              />
              <el-button type="primary" @click="searchUsers('lawyer')">查询</el-button>
            </div>
            <el-table :data="lawyerBlock.items" v-loading="lawyerBlock.loading" stripe>
              <el-table-column label="用户" min-width="180">
                <template #default="{ row }">
                  <div class="ut-user">
                    <img class="ut-avatar" :src="row.avatar || ''" onerror="this.style.visibility='hidden'" />
                    <span class="ut-nick">{{ row.nickname || row.username }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="username" label="用户名" width="140" />
              <el-table-column label="当前职位" width="120">
                <template #default="{ row }">
                  <el-tag size="small" effect="dark" :class="'ut-role-' + row.role">{{ roleNames[row.role] || row.role }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="在线状态" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="statusTagType(row.status)" effect="plain">{{ statusNames[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="注册时间" width="130">
                <template #default="{ row }">{{ String(row.created_at || "").slice(0, 10) }}</template>
              </el-table-column>
              <el-table-column label="调整职位" width="160">
                <template #default="{ row }">
                  <el-select :model-value="row.role" size="small" @change="(v: string) => onRoleChange(row, v)">
                    <el-option v-for="v in roleOptions" :key="v" :value="v" :label="roleNames[v]" />
                  </el-select>
                </template>
              </el-table-column>
            </el-table>
            <div class="pager-row">
              <el-pagination
                background
                layout="total, prev, pager, next"
                :total="lawyerBlock.total"
                :page-size="8"
                :current-page="lawyerBlock.page"
                @current-change="(p: number) => turnPage('lawyer', p)"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Search, User, UserFilled, Suitcase } from "@element-plus/icons-vue";
import { userApi, errMsg } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

const roleNames: Record<string, string> = { super_admin: "超级管理员", lawyer: "律师", user: "普通用户" };
const statusNames: Record<string, string> = { online: "在线", offline: "离线", invisible: "隐身" };
const roleOptions = ["user", "lawyer", "super_admin"];

function statusTagType(s: string) {
  return s === "online" ? "success" : s === "invisible" ? "info" : "warning";
}

interface BlockState {
  search: string;
  page: number;
  total: number;
  items: any[];
  loading: boolean;
}

const activeBlock = ref<"user" | "lawyer">("user");
const userBlock = reactive<BlockState>({ search: "", page: 1, total: 0, items: [], loading: false });
const lawyerBlock = reactive<BlockState>({ search: "", page: 1, total: 0, items: [], loading: false });
const adminBlock = reactive<BlockState>({ search: "", page: 1, total: 0, items: [], loading: false });

function blockOf(b: "user" | "lawyer") {
  return b === "user" ? userBlock : lawyerBlock;
}

async function loadBlock(b: "user" | "lawyer") {
  const blk = blockOf(b);
  blk.loading = true;
  try {
    const res = await userApi.list(b, blk.page, blk.search.trim());
    blk.total = res.total;
    blk.items = res.items;
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    blk.loading = false;
  }
}

async function loadAdminTotal() {
  try {
    const res = await userApi.list("super_admin", 1, "");
    adminBlock.total = res.total;
  } catch {
    adminBlock.total = 0;
  }
}

function searchUsers(b: "user" | "lawyer") {
  const blk = blockOf(b);
  blk.page = 1;
  loadBlock(b);
}

function turnPage(b: "user" | "lawyer", p: number) {
  const blk = blockOf(b);
  blk.page = p;
  loadBlock(b);
}

function onBlockChange() {
  loadBlock(activeBlock.value);
}

async function onRoleChange(row: any, role: string) {
  try {
    await userApi.updateRole(row.id, role);
    ElMessage.success("用户 " + row.username + " 的职位已调整为 " + roleNames[role]);
    loadBlock(activeBlock.value);
  } catch (e) {
    ElMessage.error(errMsg(e));
    loadBlock(activeBlock.value);
  }
}

onMounted(() => {
  if (auth.user?.role !== "super_admin") return;
  loadBlock("user");
  loadBlock("lawyer");
  loadAdminTotal();
});
</script>

<style scoped>
.usermanage-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 900px) {
  .stat-row {
    grid-template-columns: 1fr;
  }
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-icon.bg-user { background: linear-gradient(135deg, #3a6db3, #1b3a63); }
.stat-icon.bg-lawyer { background: linear-gradient(135deg, #c9a55c, #a07d33); }
.stat-icon.bg-admin { background: linear-gradient(135deg, #b3566a, #8f3548); }
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--al-text);
  font-family: Georgia, serif;
}
.stat-label {
  font-size: 12.5px;
  color: var(--al-text-sub);
  margin-top: 2px;
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
.manage-tip {
  font-size: 12px;
  font-weight: 400;
  color: var(--al-text-sub);
  margin-left: 6px;
}
.manage-card :deep(.el-tabs__nav-wrap::after) {
  background: var(--al-border);
}
.block-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.block-toolbar {
  display: flex;
  gap: 10px;
}
.pager-row {
  display: flex;
  justify-content: flex-end;
}
.ut-user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ut-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--al-navy-2);
  flex-shrink: 0;
}
.ut-nick {
  font-weight: 600;
}
.ut-role {
  color: #fff;
  border: none;
}
.ut-role-user { background: #5b7da8; }
.ut-role-lawyer { background: #6d552f; }
.ut-role-super_admin { background: #7a3a4a; }
:deep(.el-table) {
  --el-table-border-color: var(--al-border);
  --el-table-header-bg-color: rgba(128, 140, 160, 0.08);
}
</style>