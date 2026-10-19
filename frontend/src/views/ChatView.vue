<template>
  <div class="chat-page">
    <!-- 左侧可收缩边栏：新建咨询 + 咨询历史 -->
    <div class="side-panel page-card" :class="{ collapsed: !historyOpen }">
      <template v-if="historyOpen">
        <div class="side-top">
          <el-button type="primary" class="new-chat-btn" @click="newChat">
            <el-icon><Plus /></el-icon>&nbsp;新建咨询
          </el-button>
          <el-tooltip content="收起侧栏" placement="right">
            <el-button text circle size="small" class="fold-btn" @click="historyOpen = false">
              <el-icon><Fold /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div class="history-head">
          <div class="history-title">
            <el-icon><Clock /></el-icon>
            咨询历史
            <span class="history-count">{{ historyList.length }} 条</span>
          </div>
          <el-tooltip content="刷新历史" placement="bottom">
            <el-button text circle size="small" @click="loadHistory(true)">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-loading="historyLoading" class="history-list">
          <div v-if="!historyList.length && !historyLoading" class="history-empty">
            暂无咨询记录<br />提出您的第一个问题吧
          </div>
          <div
            v-for="h in historyList"
            :key="h.id"
            class="history-item"
            @click="resumeChat(h)"
          >
            <div class="history-item-q">{{ h.question }}</div>
            <div class="history-item-meta">
              <span class="history-item-time">{{ fmtTime(h.created_at) }}</span>
              <el-tag size="small" :type="h.used_rag === 'rag' ? 'warning' : 'info'" effect="plain">
                {{ h.used_rag === "rag" ? "知识库检索" : "模型直答" }}
              </el-tag>
              <el-tag v-if="h.from_cache === 'yes'" size="small" type="success" effect="plain">缓存</el-tag>
              <el-tooltip content="查看详情" placement="top">
                <el-button
                  text
                  circle
                  size="small"
                  class="detail-btn"
                  @click.stop="showDetail(h)"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="side-collapsed">
        <el-tooltip content="新建咨询" placement="right">
          <el-button circle type="primary" class="mini-btn" @click="newChat">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="展开咨询历史" placement="right">
          <el-button circle class="mini-btn" @click="openHistory">
            <el-icon><Clock /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <div class="chat-main page-card">
      <div class="msg-list" ref="msgListRef">
        <div v-if="!messages.length" class="empty">
          <img :src="logoUrl" class="empty-logo" />
          <h3 class="serif">您好，我是 alawyer 智能法律顾问</h3>
          <p>我会基于法律知识库增强检索（RAG）为您提供专业解答，回答下方将展示参考出处。</p>
          <div class="suggestions">
            <el-button v-for="s in suggestions" :key="s" size="small" round @click="ask(s)">{{ s }}</el-button>
          </div>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg-row" :class="m.role">
          <el-avatar v-if="m.role === 'user'" :size="36" class="msg-avatar user-avatar">
            {{ (auth.user?.nickname || "我").slice(0, 1) }}
          </el-avatar>
          <img v-else :src="logoUrl" class="msg-avatar ai-avatar" />
          <div class="msg-body">
            <div class="msg-meta">
              <b>{{ m.role === "user" ? auth.user?.nickname : "alawyer 顾问" }}</b>
              <span class="msg-time">{{ m.time }}</span>
            </div>
            <div v-if="m.role === 'user'" class="bubble user-bubble">{{ m.content }}</div>
            <template v-else>
              <div v-if="m.pending" class="bubble ai-bubble pending">
                <span class="typing"><i></i><i></i><i></i></span>
                {{ m.status || "正在思考…" }}
              </div>
              <div v-else class="bubble ai-bubble md-body" v-html="renderMd(m.content)"></div>
              <div v-if="m.pending" class="pipeline">
                <el-tag size="small" type="info" effect="plain">{{ m.status }}</el-tag>
              </div>
              <div v-if="!m.pending && m.meta" class="pipeline">
                <el-tag v-if="m.meta.fromCache" size="small" type="success" effect="plain">
                  <el-icon><Timer /></el-icon>&nbsp;Redis 缓存命中
                </el-tag>
                <el-tag v-if="m.meta.usedRag === 'rag'" size="small" type="warning" effect="plain">
                  知识库增强检索
                </el-tag>
                <el-tag v-else size="small" effect="plain">大模型直答（知识库无直接相关内容）</el-tag>
                <el-tag size="small" type="info" effect="plain">
                  嵌入：{{ m.meta.embedder === "ollama:bge-large-zh-v1.5" ? "bge-large-zh-v1.5" : "本地哈希向量" }}
                </el-tag>
                <el-tag size="small" type="info" effect="plain">
                  精排：{{ rerankLabel(m.meta.reranker) }}
                </el-tag>
              </div>
              <div v-if="!m.pending && m.sources?.length" class="sources">
                <div class="sources-title">
                  <el-icon><Collection /></el-icon>
                  回答出处（{{ m.sources.length }} 条 · 依据相关度排序）
                </div>
                <div class="source-item" v-for="(s, si) in m.sources" :key="si">
                  <div class="source-head">
                    <span class="source-badge">[{{ si + 1 }}]</span>
                    <span class="source-name">《{{ s.doc_name }}》</span>
                    <el-tag size="small" type="success" effect="plain" class="score-tag">
                      相关度 {{ (s.score * 100).toFixed(1) }}%
                    </el-tag>
                  </div>
                  <div class="source-snippet">{{ s.snippet }}…</div>
                  <div class="score-bar">
                    <div class="score-fill" :style="{ width: Math.min(100, s.score * 100) + '%' }"></div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="请输入您的法律问题，例如：劳动合同中约定的试用期最长是多久？"
          :disabled="loading"
          @keydown.enter.exact.prevent="ask(question)"
        />
        <div class="input-actions">
          <span class="input-tip">回答由本地 qwen2.5 大模型生成，仅供参考</span>
          <div class="input-btns">
            <el-button type="primary" :loading="loading" @click="ask(question)">
              <el-icon><Promotion /></el-icon>&nbsp;发送咨询
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="detailVisible" width="720px" top="6vh" class="history-dialog">
      <template #header>
        <div class="detail-header">
          <el-icon><ChatDotRound /></el-icon>
          咨询记录详情
        </div>
      </template>
      <div v-if="detail" class="detail-body">
        <div class="detail-time">
          <el-icon><Clock /></el-icon>
          {{ fmtTimeFull(detail.created_at) }}
          <el-tag size="small" :type="detail.used_rag === 'rag' ? 'warning' : 'info'" effect="plain">
            {{ detail.used_rag === "rag" ? "知识库增强检索" : "大模型直答" }}
          </el-tag>
          <el-tag v-if="detail.from_cache === 'yes'" size="small" type="success" effect="plain">
            Redis 缓存命中
          </el-tag>
        </div>
        <div class="detail-block">
          <div class="detail-label">我的问题</div>
          <div class="detail-question">{{ detail.question }}</div>
        </div>
        <div class="detail-block">
          <div class="detail-label">顾问回答</div>
          <div class="bubble ai-bubble md-body" v-html="renderMd(detail.answer)"></div>
        </div>
        <div v-if="detail.sources?.length" class="detail-block">
          <div class="detail-label">回答出处（{{ detail.sources.length }} 条）</div>
          <div class="source-item" v-for="(s, si) in detail.sources" :key="si">
            <div class="source-head">
              <span class="source-badge">[{{ si + 1 }}]</span>
              <span class="source-name">《{{ s.doc_name }}》</span>
              <el-tag size="small" type="success" effect="plain" class="score-tag">
                相关度 {{ (s.score * 100).toFixed(1) }}%
              </el-tag>
            </div>
            <div class="source-snippet">{{ s.snippet }}…</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import MarkdownIt from "markdown-it";
import hljs from "highlight.js";
import logoUrl from "@/assets/logo.png";
import { chatApi, errMsg, ChatSource } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

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

function renderMd(text: string) {
  return md.render(text || "");
}

const question = ref("");
const loading = ref(false);
const msgListRef = ref<HTMLElement>();
const messages = ref<any[]>([]);

const suggestions = [
  "劳动合同试用期最长多久？",
  "夫妻共同财产包括哪些？",
  "侵犯注册商标权如何赔偿？",
  "股东如何查询公司会计账簿？",
];

interface ChatMeta {
  usedRag: string;
  fromCache: boolean;
  embedder: string;
  reranker: string;
}

interface HistoryItem {
  id: number;
  question: string;
  answer: string;
  sources: ChatSource[];
  used_rag: string;
  from_cache: string;
  created_at: string;
}

function rerankLabel(r: string) {
  if (r === "cross-encoder") return "Cross-Encoder 精排";
  if (r === "llm") return "LLM 逐条打分（降级）";
  return "向量相似度（降级）";
}

function now() {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function fmtTime(t: string) {
  if (!t) return "";
  const d = new Date(t);
  const today = new Date();
  const hm = d.toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit" });
  if (d.toDateString() === today.toDateString()) return "今天 " + hm;
  return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, "0")} ${hm}`;
}

function fmtTimeFull(t: string) {
  if (!t) return "";
  const d = new Date(t);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${d.toLocaleTimeString("zh-CN", { hour12: false })}`;
}

function scrollBottom() {
  nextTick(() => {
    if (msgListRef.value) msgListRef.value.scrollTop = msgListRef.value.scrollHeight;
  });
}

const historyOpen = ref(true);
const historyList = ref<HistoryItem[]>([]);
const historyLoading = ref(false);
const detailVisible = ref(false);
const detail = ref<HistoryItem | null>(null);

async function loadHistory(showTip = false) {
  historyLoading.value = true;
  try {
    historyList.value = await chatApi.history(200);
    if (showTip) ElTip.success(`已刷新，共 ${historyList.value.length} 条咨询记录`);
  } catch (e) {
    if (showTip) ElTip.error(errMsg(e));
  } finally {
    historyLoading.value = false;
  }
}

function openHistory() {
  historyOpen.value = true;
  loadHistory();
}

function showDetail(h: HistoryItem) {
  detail.value = h;
  detailVisible.value = true;
}

function newChat() {
  messages.value = [];
  question.value = "";
  scrollBottom();
}

function resumeChat(h: HistoryItem) {
  messages.value = [
    { role: "user", content: h.question, time: fmtTime(h.created_at) },
    {
      role: "ai",
      content: h.answer,
      pending: false,
      sources: h.sources || [],
      meta: {
        usedRag: h.used_rag,
        fromCache: h.from_cache === "yes",
        embedder: "",
        reranker: "",
      },
      time: fmtTime(h.created_at),
    },
  ];
  question.value = "";
  scrollBottom();
  ElTip.success("已载入该条历史咨询，可直接继续追问");
}

function buildHistoryPayload() {
  return messages.value
    .filter((m) => !m.pending && m.content)
    .slice(-8)
    .map((m) => ({
      role: m.role === "user" ? "user" : "assistant",
      content: String(m.content).slice(0, 8000),
    }));
}

import { ElMessage as ElTip } from "element-plus";

const statusSteps = ["正在检索知识库…", "Cross-Encoder 精排中…", "大模型生成回答…"];
let stepTimer: number | undefined;

async function ask(q: string) {
  const text = (q || "").trim();
  if (!text || loading.value) return;
  question.value = "";
  loading.value = true;

  const aiMsg: any = {
    role: "ai",
    content: "",
    pending: true,
    status: statusSteps[0],
    sources: [],
    meta: null,
    time: now(),
  };
  messages.value.push({ role: "user", content: text, time: now() }, aiMsg);
  scrollBottom();

  let step = 0;
  stepTimer = window.setInterval(() => {
    step = Math.min(step + 1, statusSteps.length - 1);
    aiMsg.status = statusSteps[step];
  }, 2600);

  try {
    const res = await chatApi.ask(text, buildHistoryPayload());
    aiMsg.pending = false;
    aiMsg.content = res.answer;
    aiMsg.sources = res.sources || [];
    aiMsg.meta = {
      usedRag: res.used_rag,
      fromCache: res.from_cache === "yes",
      embedder: res.meta?.embedder || "",
      reranker: res.meta?.reranker || "",
    } as ChatMeta;
    loadHistory();
  } catch (e) {
    aiMsg.pending = false;
    aiMsg.content = "## 咨询失败\n\n" + errMsg(e);
  } finally {
    if (stepTimer) window.clearInterval(stepTimer);
    loading.value = false;
    scrollBottom();
  }
}

onMounted(async () => {
  if (window.innerWidth <= 920) historyOpen.value = false;
  await loadHistory();
  const mine = historyList.value.slice(0, 6).reverse();
  for (const h of mine) {
    messages.value.push({ role: "user", content: h.question, time: "" });
    messages.value.push({
      role: "ai",
      content: h.answer,
      pending: false,
      sources: h.sources || [],
      meta: {
        usedRag: h.used_rag,
        fromCache: h.from_cache === "yes",
        embedder: "",
        reranker: "",
      },
      time: "",
    });
  }
});
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 62px - 44px);
  display: flex;
  gap: 14px;
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--al-text-sub);
}

.empty-logo {
  width: 84px;
  height: 84px;
  border-radius: 20px;
  object-fit: cover;
  border: 1px solid var(--al-border);
  margin-bottom: 14px;
  background: #fff;
}

.empty h3 {
  margin: 0 0 8px;
  color: var(--al-text);
}

.suggestions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  flex-shrink: 0;
  border-radius: 10px;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border: 1px solid var(--al-border);
  background: #fff;
}

.user-avatar {
  background: var(--al-navy-2);
  color: #fff;
  font-weight: 700;
}

.msg-body {
  max-width: 78%;
}

.msg-row.user .msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-meta {
  font-size: 12px;
  color: var(--al-text-sub);
  margin-bottom: 5px;
  display: flex;
  gap: 8px;
}

.bubble {
  border-radius: 12px;
  padding: 12px 16px;
}

.user-bubble {
  background: linear-gradient(135deg, #1b3a63, #2d5b96);
  color: #fff;
  white-space: pre-wrap;
}

.ai-bubble {
  background: var(--al-bg);
  border: 1px solid var(--al-border);
}

.pending {
  color: var(--al-text-sub);
}

.typing i {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--al-gold);
  margin-right: 4px;
  animation: blink 1.2s infinite;
}

.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}

.pipeline {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sources {
  margin-top: 12px;
  border-left: 3px solid var(--al-gold);
  background: rgba(201, 165, 92, 0.06);
  border-radius: 0 10px 10px 0;
  padding: 12px 14px;
}

.sources-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--al-text);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.source-item {
  padding: 8px 0;
  border-bottom: 1px dashed var(--al-border);
}

.source-item:last-child {
  border-bottom: none;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-badge {
  background: var(--al-gold);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  border-radius: 4px;
  padding: 1px 6px;
}

.source-name {
  font-weight: 600;
  font-size: 13.5px;
  color: var(--al-text);
}

.score-tag {
  margin-left: auto;
}

.source-snippet {
  font-size: 12px;
  color: var(--al-text-sub);
  margin-top: 5px;
  line-height: 1.6;
}

.score-bar {
  height: 4px;
  background: var(--al-border);
  border-radius: 2px;
  margin-top: 6px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--al-gold), #8bc34a);
}

.input-area {
  border-top: 1px solid var(--al-border);
  padding: 14px 18px;
  background: var(--al-card);
}

.input-actions {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-btns {
  display: flex;
  gap: 10px;
}

.input-tip {
  font-size: 12px;
  color: var(--al-text-sub);
}

/* ===== 左侧可收缩边栏 ===== */
.side-panel {
  width: 285px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  transition: width 0.25s ease;
}

.side-panel.collapsed {
  width: 56px;
}

.side-top {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 12px 10px;
  border-bottom: 1px solid var(--al-border);
}

.new-chat-btn {
  flex: 1;
  min-width: 0;
  justify-content: center;
}

.side-collapsed {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-top: 14px;
}

.mini-btn {
  width: 36px;
  height: 36px;
  margin-left: 0;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 10px;
  border-bottom: 1px solid var(--al-border);
}

.history-title {
  font-weight: 700;
  font-size: 14.5px;
  color: var(--al-text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.history-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--al-gold);
  background: rgba(201, 165, 92, 0.12);
  border-radius: 10px;
  padding: 1px 8px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.history-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--al-text-sub);
  font-size: 13px;
  line-height: 2;
}

.history-item {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.18s;
}

.history-item:hover {
  background: var(--al-bg);
  border-color: var(--al-border);
}

.history-item + .history-item {
  margin-top: 4px;
}

.history-item-q {
  font-size: 13px;
  color: var(--al-text);
  font-weight: 600;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.history-item-time {
  font-size: 11.5px;
  color: var(--al-text-sub);
}

.history-item .detail-btn {
  margin-left: auto;
  width: 22px;
  height: 22px;
  color: var(--al-text-sub);
  opacity: 0;
  transition: opacity 0.15s;
}

.history-item:hover .detail-btn {
  opacity: 1;
}

.history-item-tip {
  margin: 10px 12px 0;
  font-size: 11.5px;
  color: var(--al-text-sub);
  background: rgba(128, 140, 160, 0.08);
  border-radius: 8px;
  padding: 6px 10px;
}

/* ===== 详情弹窗 ===== */
.detail-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 700;
  color: var(--al-text);
}

.detail-body {
  max-height: calc(88vh - 130px);
  overflow-y: auto;
}

.detail-time {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--al-text-sub);
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.detail-block {
  margin-bottom: 16px;
}

.detail-label {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--al-gold);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.detail-question {
  background: var(--al-bg);
  border: 1px solid var(--al-border);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 600;
  color: var(--al-text);
  line-height: 1.7;
}
</style>
