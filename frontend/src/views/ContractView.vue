<template>
  <div class="contract-page">
    <div class="page-card upload-card">
      <div class="card-title serif">
        <el-icon><Upload /></el-icon>
        上传待审合同
      </div>
      <div class="upload-row">
        <el-input v-model="uploadName" placeholder="合同名称（留空自动识别）" style="max-width: 260px" clearable />
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          :on-change="onFilePicked"
          accept=".txt,.md,.pdf,.docx,.doc,.xlsx,.csv"
        >
          <el-button type="primary">
            <el-icon><DocumentAdd /></el-icon>&nbsp;选择文件并上传
          </el-button>
        </el-upload>
        <span class="upload-tip">支持 txt / md / pdf / docx / xlsx / csv，20MB 以内</span>
        <el-button text type="primary" @click="useSample">使用示例合同</el-button>
      </div>
    </div>

    <div class="page-card">
      <div class="card-title serif">
        <el-icon><DocumentChecked /></el-icon>
        合同审查列表
        <span class="card-sub" v-if="auth.user?.role === 'super_admin'">（超级管理员可见所有用户的合同）</span>
        <span class="card-sub" v-else-if="auth.user?.role === 'lawyer'">（律师可见所有用户的合同，并可修改审查结果）</span>
      </div>
      <el-table :data="contracts" v-loading="listLoading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="合同名称" min-width="170" show-overflow-tooltip />
        <el-table-column label="上传人" width="110">
          <template #default="{ row }">{{ row.owner_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="info">待审查</el-tag>
            <el-tag v-else-if="row.status === 'reviewed'" type="warning">AI 已审查</el-tag>
            <el-tag v-else type="success">律师已复核</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="90">
          <template #default="{ row }">
            <b v-if="row.score != null" :style="{ color: scoreColor(row.score) }">{{ row.score }}</b>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.verdict" :type="verdictType(row.verdict)" effect="plain">{{ verdictLabel(row.verdict) }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="复核律师" width="100">
          <template #default="{ row }">{{ row.reviewer_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="165">
          <template #default="{ row }">{{ fmtTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <el-button size="small" class="op-btn-item" @click="openDetail(row)">查看</el-button>
            <el-button size="small" type="primary" class="op-btn-item" :loading="reviewingId === row.id" @click="doReview(row)" :disabled="!canReview">
              智能审查
            </el-button>
            <el-button v-if="canDelete(row)" size="small" type="danger" class="op-btn-item" @click="doDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" :title="detail?.name || '合同详情'" width="960px" top="4vh" class="detail-dialog">
      <template v-if="detail">
        <div v-if="detail.status === 'pending'" class="pending-box">
          <el-empty description="该合同尚未审查，点击下方按钮启动多智能体审查">
            <el-button type="primary" :loading="reviewingId === detail.id" @click="doReview(detail)">
              启动多智能体审查
            </el-button>
          </el-empty>
        </div>

        <template v-else>
          <div class="score-zone">
            <div ref="gaugeRef" class="gauge"></div>
            <div ref="radarRef" class="radar"></div>
            <div class="verdict-box">
              <div class="verdict-title">综合结论</div>
              <div class="verdict-value" :style="{ color: scoreColor(detail.score || 0) }">
                {{ verdictLabel(detail.verdict) }}
              </div>
              <div class="verdict-score">{{ detail.score }} 分 / 100</div>
              <div class="verdict-note" v-if="detail.status === 'lawyer_reviewed'">
                律师 {{ detail.reviewer_name }} 已复核
              </div>
              <el-button type="warning" round class="opt-btn" @click="optVisible = true">
                <el-icon><View /></el-icon>&nbsp;查看优化方案
              </el-button>
              <el-button
                v-if="auth.user?.role === 'lawyer'"
                type="primary"
                round
                class="opt-btn"
                @click="openLawyerReview(detail)"
              >
                <el-icon><Edit /></el-icon>&nbsp;修改审查结果
              </el-button>
            </div>
          </div>

          <div class="agents-zone" v-if="detail.agent_report?.agents?.length">
            <div class="zone-title serif">多智能体辩论过程</div>
            <el-timeline>
              <el-timeline-item
                v-for="(a, i) in detail.agent_report.agents"
                :key="i"
                :timestamp="`第 1 轮独立意见 · 评分 ${a.score}`"
                placement="top"
                :color="scoreColor(a.score)"
              >
                <div class="agent-card">
                  <div class="agent-head">
                    <el-avatar :size="34" :style="{ background: agentColors[i % agentColors.length] }">
                      {{ a.name.slice(0, 1) }}
                    </el-avatar>
                    <div>
                      <div class="agent-name">{{ a.name }}</div>
                      <div class="agent-focus">{{ a.focus }}</div>
                    </div>
                    <div class="agent-score" :style="{ color: scoreColor(a.score) }">{{ a.score }}</div>
                  </div>
                  <div class="agent-opinion">{{ a.opinion }}</div>
                  <div class="agent-points" v-if="a.points?.length">
                    <el-tag v-for="(p, pi) in a.points" :key="pi" size="small" effect="plain" class="point-tag">{{ p }}</el-tag>
                  </div>
                </div>
              </el-timeline-item>
              <el-timeline-item timestamp="首席仲裁官 · 综合裁决" placement="top" color="#c9a55c">
                <div class="agent-card judge-card">
                  <div class="agent-head">
                    <el-avatar :size="34" style="background: linear-gradient(135deg, #c9a55c, #a07d33)">裁</el-avatar>
                    <div>
                      <div class="agent-name">首席仲裁官</div>
                      <div class="agent-focus">综合三位专家两轮辩论得出最终结论</div>
                    </div>
                  </div>
                  <div class="agent-opinion">{{ detail.agent_report.summary }}</div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>

          <div class="kb-zone" v-if="detail.agent_report?.kb_sources?.length">
            <div class="zone-title serif">审查依据（知识库检索）</div>
            <div class="kb-chips">
              <el-tag v-for="(k, i) in detail.agent_report.kb_sources" :key="i" effect="plain" class="kb-chip">
                《{{ k.doc_name }}》 · 相关度 {{ (k.score * 100).toFixed(1) }}%
              </el-tag>
            </div>
          </div>

          <div class="lawyer-box" v-if="detail.lawyer_comment">
            <div class="zone-title serif">律师复核意见</div>
            <el-alert type="warning" :closable="false">
              {{ detail.lawyer_comment }}
            </el-alert>
          </div>

          <el-collapse class="raw-collapse">
            <el-collapse-item title="查看合同原文" name="raw">
              <pre class="raw-text">{{ detail.content_text }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
      </template>
    </el-dialog>

    <div v-if="optVisible" class="opt-modal-mask" @click.self="optVisible = false">
      <div class="opt-modal">
        <div class="opt-modal-head">
          <div class="opt-modal-title serif">合同优化方案</div>
          <el-button circle size="small" @click="optVisible = false"><el-icon><Close /></el-icon></el-button>
        </div>
        <div class="opt-modal-body md-body" v-html="renderMd(detail?.optimization || '')"></div>
      </div>
    </div>

    <el-dialog v-model="lawyerVisible" title="律师人工复核" width="520px" class="lawyer-dialog">
      <el-form label-position="top" v-if="lawyerTarget">
        <el-form-item label="审查结论">
          <el-radio-group v-model="lawyerForm.verdict">
            <el-radio-button value="compliant">符合要求</el-radio-button>
            <el-radio-button value="needs_revision">需要修改</el-radio-button>
            <el-radio-button value="non_compliant">不符合要求</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="`综合评分：${lawyerForm.score} 分`">
          <el-slider v-model="lawyerForm.score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="复核意见（基于多智能体分析结果进行修正说明）">
          <el-input v-model="lawyerForm.comment" type="textarea" :rows="4" placeholder="请输入您的专业复核意见" />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="lawyerSubmitting" @click="submitLawyerReview">
          提交复核结果
        </el-button>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import * as echarts from "echarts";
import MarkdownIt from "markdown-it";
import { contractApi, errMsg } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const md = new MarkdownIt({ breaks: true });
const renderMd = (t: string) => md.render(t || "");

const uploadName = ref("");
const contracts = ref<any[]>([]);
const listLoading = ref(false);
const reviewingId = ref<number | null>(null);
const detailVisible = ref(false);
const detail = ref<any>(null);
const optVisible = ref(false);
const lawyerVisible = ref(false);
const lawyerTarget = ref<any>(null);
const lawyerSubmitting = ref(false);
const lawyerForm = ref({ verdict: "needs_revision", score: 60, comment: "" });
const gaugeRef = ref<HTMLElement>();
const radarRef = ref<HTMLElement>();
let gaugeChart: echarts.ECharts | null = null;
let radarChart: echarts.ECharts | null = null;

const agentColors = ["linear-gradient(135deg,#3a6db3,#1b3a63)", "linear-gradient(135deg,#b06161,#8a3d3d)", "linear-gradient(135deg,#5aa17f,#357155)"];

const canReview = computed(() => ["user", "lawyer", "super_admin"].includes(auth.user?.role || ""));

function verdictLabel(v: string) {
  return { compliant: "符合要求", needs_revision: "需要修改", non_compliant: "不符合要求" }[v] || v;
}

function verdictType(v: string) {
  return { compliant: "success", needs_revision: "warning", non_compliant: "danger" }[v] || "info";
}

function scoreColor(s: number) {
  if (s >= 80) return "#5aa17f";
  if (s >= 60) return "#c9a55c";
  return "#c45656";
}

function fmtTime(t: string) {
  if (!t) return "-";
  const d = new Date(t);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}/${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function canDelete(row: any) {
  if (!auth.user) return false;
  return auth.user.role === "super_admin" || row.owner_id === auth.user.id;
}

async function loadList() {
  listLoading.value = true;
  try {
    contracts.value = await contractApi.list();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    listLoading.value = false;
  }
}

async function onFilePicked(file: any) {
  const raw: File = file.raw;
  if (!raw) return;
  try {
    const res = await contractApi.upload(raw, uploadName.value);
    ElMessage.success(`合同《${res.name}》已上传`);
    uploadName.value = "";
    await loadList();
    openDetail(res);
  } catch (e) {
    ElMessage.error(errMsg(e));
  }
}

function useSample() {
  ElMessageBox.confirm(
    "将使用内置的《房屋租赁合同》示例（含多处典型法律问题）进行演示，是否继续？",
    "使用示例合同",
    { confirmButtonText: "继续", cancelButtonText: "取消", type: "info" }
  ).then(async () => {
    const text = `# 房屋租赁合同

出租方（甲方）：李某
承租方（乙方）：王某

## 第一条 租赁标的
甲方将位于本市朝阳区的房屋一套出租给乙方居住使用，建筑面积90平方米。

## 第二条 租赁期限
租赁期限为2年，自2026年1月1日起至2027年12月31日止。

## 第三条 租金及支付
月租金为人民币5000元。乙方需在签订本合同时一次性支付甲方定金20000元，定金不予退还。押金10000元，退租时甲方有权以房屋磨损为由扣除全部押金。

## 第四条 甲方权利义务
甲方有权随时进入房屋检查，无需提前通知乙方。租赁期间甲方可以随时收回房屋，乙方不得有异议。

## 第五条 乙方权利义务
乙方不得转租、转让房屋。乙方违约的，甲方有权解除合同并没收全部已付租金。

## 第六条 维修责任
房屋及其设施的一切维修费用均由乙方承担，包括房屋主体结构损坏的修缮费用。

## 第七条 争议解决
因本合同产生的争议，由甲方所在地法院管辖，乙方放弃管辖异议权。

## 第八条 其他
本合同一式一份，由甲方保管，解释权归甲方所有。`;
    const blob = new Blob([text], { type: "text/plain" });
    const f = new File([blob], "房屋租赁合同示例.txt", { type: "text/plain" });
    try {
      const res = await contractApi.upload(f, "房屋租赁合同（示例）");
      ElMessage.success("示例合同已上传");
      await loadList();
      openDetail(res);
    } catch (e) {
      ElMessage.error(errMsg(e));
    }
  }).catch(() => {});
}

async function doReview(row: any) {
  reviewingId.value = row.id;
  const msg = ElMessage({
    message: "多智能体审查进行中：三位专家独立分析 → 相互辩论 → 首席仲裁官裁决，约需 20-60 秒",
    type: "info",
    duration: 0,
  });
  try {
    const res = await contractApi.review(row.id);
    detail.value = res;
    await loadList();
    ElMessage.success("多智能体审查完成");
    await nextTick();
    renderScoreCharts();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    msg.close();
    reviewingId.value = null;
  }
}

async function openDetail(row: any) {
  try {
    detail.value = await contractApi.detail(row.id);
    detailVisible.value = true;
    await nextTick();
    if (detail.value.status !== "pending") renderScoreCharts();
  } catch (e) {
    ElMessage.error(errMsg(e));
  }
}

function renderScoreCharts() {
  const d = detail.value;
  if (!d) return;
  if (gaugeRef.value) {
    gaugeChart = gaugeChart || echarts.init(gaugeRef.value);
    const s = d.score ?? 0;
    gaugeChart.setOption({
      series: [
        {
          type: "gauge",
          min: 0,
          max: 100,
          startAngle: 210,
          endAngle: -30,
          progress: { show: true, width: 14, itemStyle: { color: scoreColor(s) } },
          axisLine: { lineStyle: { width: 14, color: [[1, "rgba(128,128,128,0.18)"]] } },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          pointer: { show: false },
          anchor: { show: false },
          title: { show: true, offsetCenter: [0, "32%"], fontSize: 13, color: "#8a95a5" },
          detail: {
            valueAnimation: true,
            formatter: "{value}",
            fontSize: 44,
            fontWeight: 800,
            color: scoreColor(s),
            offsetCenter: [0, 0],
          },
          data: [{ value: s, name: "综合合规评分" }],
        },
      ],
    });
  }
  if (radarRef.value) {
    radarChart = radarChart || echarts.init(radarRef.value);
    const dims = d.dimensions || {};
    radarChart.setOption({
      tooltip: {},
      radar: {
        indicator: Object.keys(dims).map((k) => ({ name: k, max: 100 })),
        radius: "62%",
        axisName: { color: "#8a95a5", fontSize: 11.5 },
        splitArea: { areaStyle: { color: ["rgba(128,128,128,0.04)", "rgba(128,128,128,0.08)"] } },
        splitLine: { lineStyle: { color: "rgba(128,128,128,0.25)" } },
        axisLine: { lineStyle: { color: "rgba(128,128,128,0.25)" } },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: Object.values(dims),
              name: "维度评分",
              areaStyle: { color: "rgba(201,165,92,0.35)" },
              lineStyle: { color: "#c9a55c", width: 2 },
              itemStyle: { color: "#c9a55c" },
            },
          ],
        },
      ],
    });
  }
}

async function doDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除合同《${row.name}》及其审查结果吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    await contractApi.remove(row.id);
    ElMessage.success("已删除");
    if (detail.value?.id === row.id) detailVisible.value = false;
    await loadList();
  } catch (e) {
    if (e !== "cancel" && (e as any)?.message !== "cancel") {
      if ((e as any)?.toString?.().includes("cancel")) return;
      try {
        if ((e as any)?.message) ElMessage.error(errMsg(e));
      } catch {
        /* ignore */
      }
    }
  }
}

function openLawyerReview(row: any) {
  lawyerTarget.value = row;
  lawyerForm.value = {
    verdict: row.verdict || "needs_revision",
    score: row.score ?? 60,
    comment: "",
  };
  lawyerVisible.value = true;
}

async function submitLawyerReview() {
  if (!lawyerTarget.value) return;
  lawyerSubmitting.value = true;
  try {
    const res = await contractApi.lawyerReview(lawyerTarget.value.id, lawyerForm.value);
    ElMessage.success("律师复核结果已提交");
    lawyerVisible.value = false;
    detail.value = res;
    await loadList();
    await nextTick();
    renderScoreCharts();
  } catch (e) {
    ElMessage.error(errMsg(e));
  } finally {
    lawyerSubmitting.value = false;
  }
}

function onResize() {
  gaugeChart?.resize();
  radarChart?.resize();
}

onMounted(() => {
  loadList();
  window.addEventListener("resize", onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
  gaugeChart?.dispose();
  radarChart?.dispose();
});
</script>

<style scoped>
.contract-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.card-title {
  font-size: 16.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.card-sub {
  font-size: 12px;
  color: var(--al-text-sub);
  font-weight: 400;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.upload-tip {
  font-size: 12px;
  color: var(--al-text-sub);
}

.op-btn-item {
  min-width: 72px;
  justify-content: center;
}

.op-btn-item + .op-btn-item {
  margin-left: 10px;
}

.pending-box {
  padding: 30px 0;
}

.score-zone {
  display: grid;
  grid-template-columns: 300px 1fr 230px;
  gap: 10px;
  align-items: center;
  background: var(--al-bg);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 18px;
}

.gauge {
  height: 210px;
}

.radar {
  height: 230px;
}

.verdict-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
}

.verdict-title {
  color: var(--al-text-sub);
  font-size: 12.5px;
}

.verdict-value {
  font-size: 23px;
  font-weight: 800;
}

.verdict-score {
  font-size: 13px;
  color: var(--al-text-sub);
}

.opt-btn {
  margin-top: 8px;
  margin-left: 0;
  width: 100%;
  justify-content: center;
}

.zone-title {
  font-size: 15.5px;
  font-weight: 700;
  margin: 16px 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-card {
  background: var(--al-bg);
  border: 1px solid var(--al-border);
  border-radius: 12px;
  padding: 14px 16px;
}

.judge-card {
  background: rgba(201, 165, 92, 0.07);
  border-color: rgba(201, 165, 92, 0.4);
}

.agent-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-head > div {
  flex: 1;
}

.agent-name {
  font-weight: 700;
  font-size: 14.5px;
}

.agent-focus {
  font-size: 11.5px;
  color: var(--al-text-sub);
}

.agent-score {
  font-size: 24px;
  font-weight: 800;
  font-family: Georgia, serif;
}

.agent-opinion {
  margin-top: 10px;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--al-text);
}

.agent-points {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.point-tag {
  max-width: 100%;
}

.kb-chips {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.kb-chip {
  font-size: 12px;
}

.raw-collapse {
  margin-top: 16px;
}

.raw-text {
  white-space: pre-wrap;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--al-text-sub);
  max-height: 300px;
  overflow-y: auto;
  font-family: inherit;
}

.opt-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(8, 14, 24, 0.55);
  backdrop-filter: blur(3px);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.opt-modal {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(720px, 92vw);
  max-height: 80vh;
  background: var(--al-card);
  border: 1px solid var(--al-gold);
  border-radius: 16px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  z-index: 3001;
  overflow: hidden;
  animation: optIn 0.28s ease;
}

@keyframes optIn {
  from { opacity: 0; transform: translate(-50%, -47%) scale(0.96); }
  to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}

.opt-modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 22px;
  border-bottom: 1px solid var(--al-border);
  background: linear-gradient(120deg, rgba(201, 165, 92, 0.12), transparent);
}

.opt-modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--al-text);
}

.opt-modal-body {
  padding: 18px 24px;
  overflow-y: auto;
}

:deep(.detail-dialog .el-dialog__body) {
  max-height: calc(88vh - 70px);
  overflow-y: auto;
  overscroll-behavior: contain;
}

:deep(.lawyer-dialog .el-dialog__body) {
  max-height: calc(80vh - 60px);
  overflow-y: auto;
}

@media (max-width: 900px) {
  .score-zone {
    grid-template-columns: 1fr;
  }
}
</style>