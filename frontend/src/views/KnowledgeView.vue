<template>
  <div class="knowledge-page">
    <!-- 上传区（律师/管理员） -->
    <div v-if="canManage" class="page-card upload-card">
      <div class="card-title serif">
        <el-icon><Collection /></el-icon>
        导入知识库文档
      </div>
      <div class="upload-row">
        <el-input
          v-model="uploadName"
          placeholder="文档名称（留空将自动生成）"
          style="max-width: 280px"
          clearable
        />
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          :on-change="onFilePicked"
          accept=".txt,.md,.markdown,.pdf,.docx,.doc,.xlsx,.csv,.json,.html"
        >
          <el-button type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon>&nbsp;选择文件并导入
          </el-button>
        </el-upload>
        <span class="upload-tip">
          支持 txt / md / pdf / docx / xlsx / csv / json / html，20MB 以内；
          文档将自动分类法律领域、提取关键词并更新 Neo4j 知识图谱
        </span>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="page-card list-card">
      <div class="list-head">
        <div class="card-title serif" style="margin-bottom: 0">
          <el-icon><FolderOpened /></el-icon>
          知识库文档
          <el-tag size="small" type="info" effect="plain">{{ docs.length }} 份</el-tag>
        </div>
        <div class="list-tools">
          <el-select v-model="domainFilter" placeholder="全部领域" clearable style="width: 160px">
            <el-option v-for="d in domains" :key="d" :label="d" :value="d" />
          </el-select>
          <el-input
            v-model="keyword"
            placeholder="按名称搜索"
            clearable
            style="width: 200px"
            :prefix-icon="Search"
          />
        </div>
      </div>

      <el-table :data="filteredDocs" v-loading="loading" stripe style="width: 100%; margin-top: 12px">
        <el-table-column label="文档名称" min-width="220">
          <template #default="{ row }">
            <div class="doc-name-cell">
              <span class="doc-icon" :class="iconClass(row.file_type)">{{ iconText(row.file_type) }}</span>
              <div>
                <div class="doc-name">{{ row.name }}</div>
                <div class="doc-sub">{{ row.uploader_name || "系统" }} 上传于 {{ fmt(row.created_at) }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="法律领域" width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="dark" :class="domainTag(row.domain)">{{ row.domain }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <span class="mono">{{ (row.file_type || "?").toUpperCase() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ fmtSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="切片数" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain" round>{{ row.chunk_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近更新" width="170">
          <template #default="{ row }">
            <span class="time">{{ fmt(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <div class="op-col">
              <el-button size="small" class="op-btn-item" @click="openContent(row)">查看原文</el-button>
              <el-button v-if="canManage" size="small" type="warning" class="op-btn-item" @click="openEdit(row)">
                <el-icon><Edit /></el-icon>&nbsp;编辑
              </el-button>
              <el-popconfirm v-if="canManage" title="删除后向量库与图谱同步清除，确定？" @confirm="remove(row.id)">
                <template #reference>
                  <el-button size="small" type="danger" class="op-btn-item">
                    <el-icon><Delete /></el-icon>&nbsp;删除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && filteredDocs.length === 0" description="暂无文档，等待导入" />
    </div>

    <!-- 查看原文弹窗 -->
    <el-dialog v-model="contentVisible" :title="contentDoc?.name || '文档原文'" width="860px" top="5vh" class="doc-dialog">
      <template v-if="contentDoc">
        <div class="doc-meta">
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">法律领域</span>
              <el-tag size="small" effect="dark" :class="domainTag(contentDoc.domain)">{{ contentDoc.domain }}</el-tag>
            </div>
            <div class="meta-item">
              <span class="meta-label">文件类型</span>
              <span class="mono">{{ (contentDoc.file_type || "?").toUpperCase() }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">文件大小</span>
              <span>{{ fmtSize(contentDoc.file_size) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">向量切片</span>
              <span>{{ contentDoc.chunk_count }} 块</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">上传人</span>
              <span>{{ contentDoc.uploader_name || "系统" }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">更新时间</span>
              <span>{{ fmt(contentDoc.updated_at) }}</span>
            </div>
          </div>
          <div class="meta-kw" v-if="contentDoc.keywords?.length">
            <span class="meta-label">关键词</span>
            <el-tag v-for="k in contentDoc.keywords" :key="k" size="small" effect="plain" round>{{ k }}</el-tag>
          </div>
        </div>
        <div class="doc-content md-body" v-loading="contentLoading" v-html="renderMd(contentDoc.content)"></div>
        <div class="doc-footer">
          <span class="doc-footer-tip">以上原文已在 AI 问答检索范围内 · Markdown 渲染 · 文档 ID #{{ contentDoc.id }}</span>
          <div class="doc-footer-btns">
            <el-button v-if="canManage" size="small" type="warning" @click="openEdit(contentDoc)">
              <el-icon><Edit /></el-icon>&nbsp;编辑此文档
            </el-button>
            <el-button size="small" @click="contentVisible = false">关闭</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑文档弹窗 -->
    <el-dialog v-model="editVisible" title="编辑知识库文档" width="820px" top="4vh" class="edit-dialog">
      <template v-if="editDoc">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="保存后系统将自动重新分块、向量化并更新知识图谱，AI 问答立即引用新版内容"
          style="margin-bottom: 14px"
        />
        <div class="edit-form">
          <div class="edit-field">
            <span class="edit-label">文档名称</span>
            <el-input v-model="editDoc.name" maxlength="60" show-word-limit placeholder="文档名称" style="max-width: 420px" />
          </div>
          <div class="edit-field">
            <span class="edit-label">法律领域（自动识别）</span>
            <el-tag size="small" effect="dark" :class="domainTag(editDoc.domain)">{{ editDoc.domain }}</el-tag>
            <span class="edit-hint">由文档内容自动判定，保存后更新</span>
          </div>
          <div class="edit-field" style="flex: 1; display: flex; flex-direction: column">
            <span class="edit-label">文档内容（Markdown）</span>
            <el-input
              v-model="editDoc.content"
              type="textarea"
              :rows="16"
              resize="none"
              placeholder="支持 Markdown 格式：# 标题、列表、表格、代码块等"
              style="flex: 1"
            />
          </div>
        </div>
      </template>
      <template #footer>
        <div v-if="editDoc" class="edit-footer">
          <span class="edit-count">{{ (editDoc.content || "").length }} 字符</span>
          <div>
            <el-button @click="editVisible = false">取消</el-button>
            <el-button type="primary" :loading="editSaving" @click="saveEdit">保存修改</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Search, Upload, Delete, Collection, FolderOpened, Edit } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import { kbApi, errMsg } from "@/api";
import { useAuthStore } from "@/stores/auth";

const md = new MarkdownIt({
  breaks: true,
  linkify: true,
  highlight(str: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value;
      } catch {
        /* ignore */
      }
    }
    return "";
  },
});

function renderMd(text?: string) {
  if (!text) return "<p style='color: var(--al-text-sub)'>（无文本内容）</p>";
  return md.render(text);
}

const auth = useAuthStore();
const canManage = computed(() => auth.user?.role === "lawyer" || auth.user?.role === "super_admin");

const docs = ref<any[]>([]);
const loading = ref(false);
const uploading = ref(false);
const uploadName = ref("");
const domainFilter = ref("");
const keyword = ref("");

const domains = [
  "劳动用工", "合同事务", "公司治理", "知识产权", "婚姻家庭", "刑事辩护", "侵权责任", "综合法律",
];

const filteredDocs = computed(() =>
  docs.value.filter(
    (d) =>
      (!domainFilter.value || d.domain === domainFilter.value) &&
      (!keyword.value || (d.name || "").toLowerCase().includes(keyword.value.toLowerCase()))
  )
);

function iconText(t: string) {
  return (t || "txt").replace("markdown", "md").slice(0, 4).toUpperCase();
}
function iconClass(t: string) {
  const map: Record<string, string> = {
    pdf: "t-pdf", docx: "t-doc", doc: "t-doc", xlsx: "t-xls", csv: "t-xls", json: "t-json",
  };
  return map[(t || "").toLowerCase()] || "t-txt";
}
function domainTag(d: string) {
  const idx = domains.indexOf(d);
  return "domain-tag-" + (((idx % 6) + 6) % 6);
}
function fmt(s?: string) {
  if (!s) return "-";
  const d = new Date(s);
  const p = (n: number) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
}
function fmtSize(n?: number) {
  if (!n && n !== 0) return "-";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(1) + " MB";
}

async function load() {
  loading.value = true;
  try {
    docs.value = await kbApi.list();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}

async function onFilePicked(file: UploadFile) {
  if (!file.raw) return;
  uploading.value = true;
  try {
    const doc = await kbApi.upload(file.raw, uploadName.value.trim());
    ElMessage.success("文档「" + doc.name + "」已导入知识库");
    uploadName.value = "";
    await load();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    uploading.value = false;
  }
}

async function remove(id: number) {
  try {
    await kbApi.remove(id);
    ElMessage.success("文档已删除，向量库与图谱同步更新");
    await load();
  } catch (e) {
    ElMessage.error(errMsg(e));
  }
}

const contentVisible = ref(false);
const contentLoading = ref(false);
const contentDoc = ref<any>(null);

async function openContent(row: any) {
  contentDoc.value = { ...row, content: "" };
  contentVisible.value = true;
  contentLoading.value = true;
  try {
    contentDoc.value = await kbApi.content(row.id);
  } catch (e) {
    ElMessage.error(errMsg(e));
    contentVisible.value = false;
  } finally {
    contentLoading.value = false;
  }
}

const editVisible = ref(false);
const editSaving = ref(false);
const editDoc = ref<any>(null);

async function openEdit(row: any) {
  let full = row;
  try {
    full = await kbApi.content(row.id);
  } catch {
    /* 列表行兜底 */
  }
  editDoc.value = { ...full };
  editVisible.value = true;
}

async function saveEdit() {
  if (!editDoc.value) return;
  const name = (editDoc.value.name || "").trim();
  const content = (editDoc.value.content || "").trim();
  if (!name) {
    ElMessage.warning("文档名称不能为空");
    return;
  }
  if (content.length < 20) {
    ElMessage.warning("文档内容过短（至少 20 字符）");
    return;
  }
  editSaving.value = true;
  try {
    await kbApi.update(editDoc.value.id, { name, content });
    ElMessage.success("文档已更新，向量库与知识图谱同步重建");
    editVisible.value = false;
    contentVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    editSaving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 700;
  color: var(--al-text);
  margin-bottom: 14px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.upload-tip {
  font-size: 12.5px;
  color: var(--al-text-sub);
}
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.list-tools {
  display: flex;
  gap: 10px;
}
.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.doc-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.doc-icon.t-txt { background: #5b7da8; }
.doc-icon.t-pdf { background: #c0574f; }
.doc-icon.t-doc { background: #3a6ea5; }
.doc-icon.t-xls { background: #3f8f5f; }
.doc-icon.t-json { background: #8a6bbf; }
.doc-name {
  font-weight: 600;
  color: var(--al-text);
}
.doc-sub,
.time {
  font-size: 12px;
  color: var(--al-text-sub);
  margin-top: 2px;
}
.mono {
  font-family: Consolas, monospace;
  font-size: 13px;
}
.domain-tag-0 { background: #1b3a63; border-color: #1b3a63; }
.domain-tag-1 { background: #6d552f; border-color: #6d552f; }
.domain-tag-2 { background: #2f5d50; border-color: #2f5d50; }
.domain-tag-3 { background: #5a3d5f; border-color: #5a3d5f; }
.domain-tag-4 { background: #7a4a3a; border-color: #7a4a3a; }
.domain-tag-5 { background: #3d5a75; border-color: #3d5a75; }
:deep(.el-table) {
  --el-table-border-color: var(--al-border);
  --el-table-header-bg-color: rgba(128, 140, 160, 0.08);
}

.op-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}
.op-btn-item {
  width: 96px;
  margin-left: 0;
  justify-content: center;
}

:deep(.doc-dialog .el-dialog__body) {
  padding-top: 12px;
}
.doc-meta {
  border: 1px solid var(--al-border);
  border-radius: 10px;
  padding: 12px 16px;
  background: rgba(128, 140, 160, 0.06);
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px 16px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--al-text);
}
.meta-label {
  font-size: 12px;
  color: var(--al-text-sub);
  flex-shrink: 0;
}
.meta-kw {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.doc-content {
  margin-top: 14px;
  border: 1px solid var(--al-border);
  border-radius: 10px;
  padding: 16px 20px;
  max-height: 52vh;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--al-text);
  overscroll-behavior: contain;
}
.doc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.doc-footer-tip {
  font-size: 12px;
  color: var(--al-text-sub);
}
.doc-footer-btns {
  display: flex;
  gap: 10px;
}
.doc-content.md-body {
  font-size: 13.5px;
  line-height: 1.85;
}
.doc-content.md-body :deep(h1) { font-size: 19px; margin: 14px 0 10px; }
.doc-content.md-body :deep(h2) { font-size: 17px; margin: 12px 0 8px; }
.doc-content.md-body :deep(h3) { font-size: 15px; margin: 10px 0 6px; }
.doc-content.md-body :deep(p) { margin: 6px 0; }
.doc-content.md-body :deep(ul), .doc-content.md-body :deep(ol) { padding-left: 22px; margin: 6px 0; }
.doc-content.md-body :deep(li) { margin: 3px 0; }
.doc-content.md-body :deep(table) { border-collapse: collapse; margin: 10px 0; width: 100%; }
.doc-content.md-body :deep(th), .doc-content.md-body :deep(td) {
  border: 1px solid var(--al-border);
  padding: 6px 10px;
  font-size: 12.5px;
}
.doc-content.md-body :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 14px;
  border-left: 3px solid rgba(140, 160, 190, 0.6);
  color: var(--al-text-sub);
  background: rgba(128, 140, 160, 0.08);
  border-radius: 0 6px 6px 0;
}
.doc-content.md-body :deep(code) {
  background: rgba(128, 140, 160, 0.15);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12.5px;
}
.doc-content.md-body :deep(pre) {
  background: rgba(30, 40, 55, 0.92);
  padding: 12px 14px;
  border-radius: 8px;
  overflow-x: auto;
}
.doc-content.md-body :deep(pre code) {
  background: none;
  padding: 0;
  color: #e8eef6;
}
.doc-content.md-body :deep(strong) { color: var(--al-text); }
.doc-content.md-body :deep(hr) { border: none; border-top: 1px solid var(--al-border); margin: 12px 0; }

:deep(.edit-dialog .el-dialog__body) {
  padding-top: 12px;
  max-height: calc(82vh - 110px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.edit-field {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.edit-label {
  font-size: 13px;
  color: var(--al-text-sub);
  flex-shrink: 0;
  min-width: 140px;
}
.edit-hint {
  font-size: 12px;
  color: var(--al-text-sub);
}
.edit-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.edit-count {
  font-size: 12px;
  color: var(--al-text-sub);
}
</style>