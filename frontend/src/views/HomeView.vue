<template>
  <div class="home">
    <div class="greeting page-card">
      <div class="greet-text">
        <h2 class="serif">{{ greeting }}，{{ auth.user?.nickname }}</h2>
        <p>{{ greetSub }} · 现在是 {{ nowText }}（{{ weekday }}）</p>
      </div>
      <div class="greet-right">
        <div class="greet-services">
          <el-tooltip v-for="(ok, name) in summary.services" :key="name" :content="serviceNames[name] || name">
            <span class="dot" :class="ok ? 'ok' : 'bad'"></span>
          </el-tooltip>
          <span class="services-label">服务状态</span>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat-card page-card" v-for="s in statCards" :key="s.label">
        <div class="stat-icon" :style="{ background: s.bg }">
          <el-icon :size="26" color="#fff"><component :is="s.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="charts-row">
      <div class="page-card chart-card">
        <div class="card-title serif">法律领域分布</div>
        <div ref="pieRef" class="chart-body"></div>
      </div>
      <div class="page-card chart-card wide">
        <div class="card-title serif">近 7 日咨询趋势</div>
        <div ref="trendRef" class="chart-body"></div>
      </div>
    </div>

    <div class="page-card kg-card">
      <div class="card-title serif">
        法律知识图谱
        <span class="card-sub">基于 Neo4j 5 · 知识库文档 / 领域 / 关键词</span>
      </div>
      <div ref="graphRef" class="kg-body"></div>
    </div>

    <div class="feature-blocks">
      <div class="feature page-card" v-for="f in features" :key="f.title" @click="router.push(f.path)">
        <div class="feature-head">
          <div class="feature-icon" :style="{ background: f.bg }">
            <el-icon :size="22" color="#fff"><component :is="f.icon" /></el-icon>
          </div>
          <div class="feature-count" v-if="f.count !== null">{{ f.count }}</div>
        </div>
        <div class="feature-title serif">{{ f.title }}</div>
        <div class="feature-desc">{{ f.desc }}</div>
        <div class="feature-enter">进入模块 <el-icon><ArrowRight /></el-icon></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import * as echarts from "echarts";
import { dashboardApi, errMsg } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";

const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const summary = ref<any>({ services: {} });
const nowText = ref("");
let clockTimer: number | undefined;

const serviceNames: Record<string, string> = {
  mysql: "MySQL",
  redis: "Redis 缓存",
  neo4j: "Neo4j 图谱",
  ollama: "Ollama 大模型",
  chroma: "Chroma 向量库",
};

const pieRef = ref<HTMLElement>();
const trendRef = ref<HTMLElement>();
const graphRef = ref<HTMLElement>();
let pieChart: echarts.ECharts | null = null;
let trendChart: echarts.ECharts | null = null;
let graphChart: echarts.ECharts | null = null;

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 9) return "早上好";
  if (h < 12) return "上午好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});

const greetSub = computed(() => {
  const role = auth.user?.role;
  if (role === "super_admin") return "您正在以超级管理员身份统揽平台全貌";
  if (role === "lawyer") return "您正在以律师身份提供专业支持";
  return "愿 alawyer 成为您的贴心法律顾问";
});

const weekday = computed(() => "星期" + "日一二三四五六"[new Date().getDay()]);

const statCards = computed(() => [
  { label: "今日咨询次数", value: summary.value.today_consultations ?? 0, icon: "ChatDotRound", bg: "linear-gradient(135deg,#3a6db3,#1b3a63)" },
  { label: "合同审核数", value: summary.value.contract_reviewed ?? 0, icon: "DocumentChecked", bg: "linear-gradient(135deg,#c9a55c,#a07d33)" },
  { label: "知识库文档数", value: summary.value.kb_docs ?? 0, icon: "Collection", bg: "linear-gradient(135deg,#5aa17f,#357155)" },
  { label: "平台总用户数", value: summary.value.total_users ?? 0, icon: "User", bg: "linear-gradient(135deg,#8a6bb5,#5d4391)" },
]);

const features = computed(() => [
  {
    title: "AI 智能问答",
    desc: "基于本地大模型与知识库增强检索（RAG），回答附权威出处",
    icon: "ChatDotRound",
    bg: "linear-gradient(135deg,#3a6db3,#1b3a63)",
    path: "/chat",
    count: summary.value.today_consultations ?? 0,
  },
  {
    title: "合同智能审查",
    desc: "多智能体辩论式审查，量化评分与优化方案",
    icon: "DocumentChecked",
    bg: "linear-gradient(135deg,#c9a55c,#a07d33)",
    path: "/contract",
    count: summary.value.contract_reviewed ?? 0,
  },
  {
    title: "法律知识库",
    desc: "多格式文档导入，向量化入库并构建知识图谱",
    icon: "Collection",
    bg: "linear-gradient(135deg,#5aa17f,#357155)",
    path: "/knowledge",
    count: summary.value.kb_docs ?? 0,
  },
  ...(auth.user?.role === "super_admin"
    ? [
        {
          title: "用户管理",
          desc: "查看全部用户，分块分页查询并调整职位",
          icon: "UserFilled",
          bg: "linear-gradient(135deg,#b3566a,#8f3548)",
          path: "/users",
          count: summary.value.total_users ?? 0,
        },
      ]
    : []),
  {
    title: "个人设置",
    desc: "管理头像、密码与在线状态等个人信息",
    icon: "Setting",
    bg: "linear-gradient(135deg,#8a6bb5,#5d4391)",
    path: "/settings",
    count: null,
  },
]);

function isDark() {
  return theme.mode.value === "dark";
}

function textColor() {
  return isDark() ? "#c8d2e0" : "#4a5768";
}

function axisColor() {
  return isDark() ? "#3a4658" : "#e4e9f2";
}

function renderCharts() {
  const dark = isDark();

  if (pieRef.value && summary.value.domain_distribution?.length) {
    pieChart = pieChart || echarts.init(pieRef.value);
    pieChart.setOption({
      tooltip: { trigger: "item", formatter: "{b}: {c} 篇（{d}%）" },
      legend: { bottom: 0, textStyle: { color: textColor(), fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
      series: [
        {
          type: "pie",
          radius: ["42%", "68%"],
          center: ["50%", "44%"],
          itemStyle: { borderRadius: 6, borderColor: dark ? "#16202f" : "#fff", borderWidth: 2 },
          label: { show: false },
          data: summary.value.domain_distribution,
        },
      ],
      color: ["#1b3a63", "#c9a55c", "#5aa17f", "#8a6bb5", "#b06161", "#3a8bb3", "#a07d33", "#6d8a4e"],
    });
  }

  if (trendRef.value) {
    trendChart = trendChart || echarts.init(trendRef.value);
    trendChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 40, right: 20, top: 26, bottom: 30 },
      xAxis: { type: "category", data: (summary.value.consultation_trend || []).map((t: any) => t.date), axisLine: { lineStyle: { color: axisColor() } }, axisLabel: { color: textColor() } },
      yAxis: { type: "value", minInterval: 1, axisLabel: { color: textColor() }, splitLine: { lineStyle: { color: axisColor() } } },
      series: [
        {
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 8,
          data: (summary.value.consultation_trend || []).map((t: any) => t.value),
          lineStyle: { width: 3, color: "#c9a55c" },
          itemStyle: { color: "#c9a55c" },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(201,165,92,0.35)" },
            { offset: 1, color: "rgba(201,165,92,0.02)" },
          ]) },
        },
      ],
    });
  }

  if (graphRef.value && summary.value.graph?.nodes?.length) {
    graphChart = graphChart || echarts.init(graphRef.value);
    const colorMap: Record<string, string> = {
      Domain: "#c9a55c",
      Document: "#3a6db3",
      Keyword: "#5aa17f",
      Root: "#b06161",
    };
    const sizeMap: Record<string, number> = { Domain: 34, Document: 22, Keyword: 12, Root: 40 };
    graphChart.setOption({
      tooltip: { formatter: (p: any) => `${p.data.label || ""} · ${p.data.name}` },
      series: [
        {
          type: "graph",
          layout: "force",
          roam: true,
          draggable: true,
          data: summary.value.graph.nodes.map((n: any) => ({
            id: n.id,
            name: n.name.length > 12 ? n.name.slice(0, 12) + "…" : n.name,
            label: n.label,
            symbolSize: sizeMap[n.label] || 16,
            itemStyle: { color: colorMap[n.label] || "#8a93a5" },
          })),
          links: summary.value.graph.links.map((l: any) => ({ source: l.source, target: l.target, value: l.type })),
          label: { show: true, color: textColor(), fontSize: 10.5, position: "right" },
          lineStyle: { color: isDark() ? "#3a4658" : "#c9d4e4", width: 1.2, curveness: 0.12 },
          force: { repulsion: 210, edgeLength: [55, 110], gravity: 0.08 },
          emphasis: { focus: "adjacency", lineStyle: { width: 2.5 } },
        },
      ],
    });
  }
}

async function load() {
  try {
    summary.value = await dashboardApi.summary();
    renderCharts();
  } catch (e) {
    console.error(errMsg(e));
  }
}

onMounted(() => {
  nowText.value = new Date().toLocaleString("zh-CN", { hour12: false });
  clockTimer = window.setInterval(() => {
    nowText.value = new Date().toLocaleString("zh-CN", { hour12: false });
  }, 1000);
  load();
  window.addEventListener("resize", onResize);
});

function onResize() {
  pieChart?.resize();
  trendChart?.resize();
  graphChart?.resize();
}

onBeforeUnmount(() => {
  if (clockTimer) window.clearInterval(clockTimer);
  window.removeEventListener("resize", onResize);
  pieChart?.dispose();
  trendChart?.dispose();
  graphChart?.dispose();
});
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.greeting {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(120deg, var(--al-navy) 0%, #1e3f6e 70%, #27508a 100%);
  border: none;
  color: #fff;
  padding: 26px 30px;
}

.greet-text h2 {
  margin: 0 0 8px;
  font-size: 25px;
  color: #fff;
}

.greet-text p {
  margin: 0;
  color: #c3cedd;
  font-size: 13.5px;
}

.greet-services {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  display: inline-block;
}

.dot.ok {
  background: #58d08a;
  box-shadow: 0 0 8px rgba(88, 208, 138, 0.8);
}

.dot.bad {
  background: #e06c6c;
  box-shadow: 0 0 8px rgba(224, 108, 108, 0.8);
}

.services-label {
  color: #c3cedd;
  font-size: 12.5px;
  margin-left: 4px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
  gap: 18px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(16, 35, 63, 0.14);
}

.stat-icon {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  font-size: 27px;
  font-weight: 800;
  color: var(--al-text);
  font-family: Georgia, serif;
}

.stat-label {
  color: var(--al-text-sub);
  font-size: 13px;
  margin-top: 2px;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 18px;
}

.chart-card {
  min-height: 300px;
}

.card-title {
  font-size: 16.5px;
  font-weight: 700;
  color: var(--al-text);
  margin-bottom: 6px;
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.card-sub {
  font-size: 12px;
  color: var(--al-text-sub);
  font-weight: 400;
}

.chart-body {
  height: 250px;
}

.kg-card {
  min-height: 420px;
}

.kg-body {
  height: 360px;
}

.feature-blocks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 18px;
}

.feature {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.feature:hover {
  transform: translateY(-4px);
  box-shadow: 0 14px 34px rgba(16, 35, 63, 0.16);
  border-color: var(--al-gold);
}

.feature-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-count {
  font-size: 24px;
  font-weight: 800;
  color: var(--al-gold);
  font-family: Georgia, serif;
}

.feature-title {
  font-size: 17px;
  font-weight: 700;
  margin: 14px 0 6px;
  color: var(--al-text);
}

.feature-desc {
  font-size: 12.5px;
  color: var(--al-text-sub);
  line-height: 1.65;
  min-height: 42px;
}

.feature-enter {
  margin-top: 10px;
  color: var(--al-primary);
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 1100px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>