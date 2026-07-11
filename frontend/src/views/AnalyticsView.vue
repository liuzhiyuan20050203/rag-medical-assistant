<template>
  <div class="analytics-page">
    <section class="analytics-hero ui-card" :aria-busy="loading">
      <div class="hero-copy">
        <div class="hero-kicker-row">
          <p class="eyebrow">MEDICAL DATA CENTER</p>
          <span class="status-pill"><i></i> 数据已连接</span>
        </div>
        <h2>数据分析中心</h2>
        <p>从咨询趋势、风险分诊、知识检索与用户反馈中提取关键指标，帮助快速判断系统服务质量。</p>
      </div>

      <div class="hero-actions">
        <span>{{ updatedLabel }}</span>
        <button class="ui-button ui-button--primary" type="button" @click="loadAnalytics(true)" :disabled="loading">
          <RefreshCw :class="{ spin: loading }" :size="17" aria-hidden="true" />
          {{ loading ? '正在刷新' : '刷新数据' }}
        </button>
      </div>
    </section>

    <section class="overview-grid" aria-label="核心数据指标">
      <article class="metric-card metric-blue ui-card">
        <div class="metric-head">
          <span class="metric-icon"><MessagesSquare :size="19" aria-hidden="true" /></span>
          <i>累计</i>
        </div>
        <strong>{{ analytics.overview.total_questions }}</strong>
        <span>用户咨询量</span>
        <small>全部有效咨询记录</small>
      </article>
      <article class="metric-card metric-red ui-card">
        <div class="metric-head">
          <span class="metric-icon"><ShieldAlert :size="19" aria-hidden="true" /></span>
          <i>{{ warningRate }}%</i>
        </div>
        <strong>{{ analytics.overview.warning_count }}</strong>
        <span>高风险提醒</span>
        <small>占全部咨询的 {{ warningRate }}%</small>
      </article>
      <article class="metric-card metric-amber ui-card">
        <div class="metric-head">
          <span class="metric-icon"><Star :size="19" aria-hidden="true" /></span>
          <i>5 分制</i>
        </div>
        <strong>{{ averageRatingLabel }}</strong>
        <span>平均评分</span>
        <small>{{ analytics.overview.feedback_count || 0 }} 条有效反馈</small>
      </article>
      <article class="metric-card metric-teal ui-card">
        <div class="metric-head">
          <span class="metric-icon"><BookOpenCheck :size="19" aria-hidden="true" /></span>
          <i>知识覆盖</i>
        </div>
        <strong>{{ analytics.overview.knowledge_count }}</strong>
        <span>知识总量</span>
        <small>{{ analytics.overview.disease_count }} 疾病 · {{ analytics.overview.medicine_count }} 药品</small>
      </article>
    </section>

    <section class="insight-panel ui-card" aria-label="数据洞察摘要">
      <span class="insight-icon"><Sparkles :size="21" aria-hidden="true" /></span>
      <div class="insight-copy">
        <strong>数据洞察</strong>
        <p>{{ insightSummary }}</p>
      </div>
      <div class="quick-metrics">
        <span><Pill :size="16" aria-hidden="true" />药品查询 <strong>{{ analytics.overview.medicine_search_count }}</strong></span>
        <span><CircleAlert :size="16" aria-hidden="true" />错误标记 <strong>{{ analytics.overview.error_count }}</strong></span>
      </div>
    </section>

    <section class="chart-grid">
      <article class="chart-card symptoms-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">SYMPTOMS</p>
            <h3>常见症状统计</h3>
          </div>
          <span>按提及次数排序</span>
        </div>

        <div v-if="analytics.symptom_stats.length" class="bar-list">
          <div v-for="item in analytics.symptom_stats" :key="item.name" class="bar-row">
            <span>{{ item.name }}</span>
            <div class="bar-track">
              <i :style="{ width: barWidth(item, analytics.symptom_stats) }"></i>
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>

        <p v-else class="empty-state ui-empty">暂无症状命中数据，完成几次 AI 助手咨询后会自动生成。</p>
      </article>

      <article class="chart-card risk-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">RISK</p>
            <h3>风险等级分布</h3>
          </div>
          <span>共 {{ totalRisk }} 次</span>
        </div>

        <div class="donut-wrap">
          <div class="donut" :style="{ background: riskGradient }">
            <span><strong>{{ totalRisk }}</strong><small>风险事件</small></span>
          </div>

          <div class="legend">
            <div v-for="item in analytics.risk_distribution" :key="item.name">
              <i :style="{ background: riskColor(item.name) }"></i>
              <span>{{ item.name }}</span>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
        </div>
      </article>

      <article class="chart-card disease-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">DISEASES</p>
            <h3>高频疾病查询统计</h3>
          </div>
          <span>TOP {{ analytics.disease_stats.length }}</span>
        </div>

        <div v-if="analytics.disease_stats.length" class="rank-list">
          <div v-for="(item, index) in analytics.disease_stats" :key="item.name" class="rank-item">
            <span>{{ index + 1 }}</span>
            <strong>{{ item.name }}</strong>
            <i>{{ item.count }} 次</i>
          </div>
        </div>

        <p v-else class="empty-state ui-empty">暂无疾病检索记录。</p>
      </article>

      <article class="chart-card medicine-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">MEDICINES</p>
            <h3>高频药品查询统计</h3>
          </div>
          <span>TOP {{ analytics.medicine_stats.length }}</span>
        </div>

        <div v-if="analytics.medicine_stats.length" class="rank-list">
          <div v-for="(item, index) in analytics.medicine_stats" :key="item.name" class="rank-item medicine">
            <span>{{ index + 1 }}</span>
            <strong>{{ item.name }}</strong>
            <i>{{ item.count }} 次</i>
          </div>
        </div>

        <p v-else class="empty-state ui-empty">暂无药品查询记录。</p>
      </article>

      <article class="chart-card word-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">WORD CLOUD</p>
            <h3>用户提问词云</h3>
          </div>
          <span>高频关键词</span>
        </div>

        <div v-if="analytics.word_cloud.length" class="word-cloud">
          <span
            v-for="item in analytics.word_cloud"
            :key="item.text"
            :style="wordStyle(item)"
          >
            {{ item.text }}
          </span>
        </div>

        <p v-else class="empty-state ui-empty">暂无词云数据。</p>
      </article>

      <article class="chart-card satisfaction-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">SATISFACTION</p>
            <h3>系统回答满意度统计</h3>
          </div>
          <span>{{ analytics.overview.feedback_count || 0 }} 条反馈</span>
        </div>

        <div v-if="analytics.satisfaction.length" class="satisfaction-list">
          <div v-for="item in analytics.satisfaction" :key="item.name">
            <span>{{ item.name }}</span>
            <div>
              <i :style="{ width: barWidth(item, analytics.satisfaction), background: satisfactionColor(item.name) }"></i>
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>

        <p v-else class="empty-state ui-empty">暂无用户评分数据。</p>
      </article>

      <article class="chart-card trend-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">TREND</p>
            <h3>提问趋势</h3>
          </div>
          <span>最近 {{ analytics.daily_questions.length }} 个记录日</span>
        </div>

        <div v-if="analytics.daily_questions.length" class="trend-bars">
          <div v-for="item in analytics.daily_questions" :key="item.date">
            <b>{{ item.count }}</b>
            <i :style="{ height: trendHeight(item) }"></i>
            <span>{{ shortDate(item.date) }}</span>
          </div>
        </div>

        <p v-else class="empty-state ui-empty">暂无趋势数据。</p>
      </article>
    </section>

    <p v-if="message" class="message ui-alert ui-alert--error">{{ message }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BookOpenCheck,
  CircleAlert,
  MessagesSquare,
  Pill,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Star,
} from '@lucide/vue'
import { cachedGetJson } from '../api'

const loading = ref(false)
const message = ref('')
const lastUpdatedAt = ref(null)

const analytics = ref({
  overview: {
    total_questions: 0,
    warning_count: 0,
    knowledge_count: 0,
    disease_count: 0,
    medicine_count: 0,
    medicine_search_count: 0,
    error_count: 0,
    feedback_count: 0,
    average_rating: 0,
  },
  symptom_stats: [],
  disease_stats: [],
  medicine_stats: [],
  risk_distribution: [],
  word_cloud: [],
  satisfaction: [],
  daily_questions: [],
})

const totalRisk = computed(() => {
  return analytics.value.risk_distribution.reduce((sum, item) => sum + item.count, 0)
})

const warningRate = computed(() => {
  const total = Number(analytics.value.overview.total_questions || 0)
  if (!total) return 0
  return Math.round((Number(analytics.value.overview.warning_count || 0) / total) * 100)
})

const averageRatingLabel = computed(() => {
  const value = Number(analytics.value.overview.average_rating || 0)
  return value ? value.toFixed(1) : '0.0'
})

const updatedLabel = computed(() => {
  if (!lastUpdatedAt.value) return '等待首次同步'
  return `更新于 ${lastUpdatedAt.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
})

const insightSummary = computed(() => {
  const symptom = analytics.value.symptom_stats[0]
  const disease = analytics.value.disease_stats[0]

  if (!symptom && !disease) {
    return '完成更多咨询后，这里会自动总结症状热点、风险比例与知识检索趋势。'
  }

  const parts = []
  if (symptom) parts.push(`“${symptom.name}”是当前提及最多的症状，共 ${symptom.count} 次`)
  if (disease) parts.push(`疾病检索以“${disease.name}”最为集中`)
  parts.push(`高风险提醒占全部咨询的 ${warningRate.value}%`)
  return `${parts.join('；')}。`
})

const riskGradient = computed(() => {
  if (!totalRisk.value) {
    return 'conic-gradient(var(--border) 0deg 360deg)'
  }

  let current = 0
  const parts = analytics.value.risk_distribution.map((item) => {
    const start = current
    const end = current + (item.count / totalRisk.value) * 360
    current = end
    return `${riskColor(item.name)} ${start}deg ${end}deg`
  })

  return `conic-gradient(${parts.join(', ')})`
})

const maxCount = (items) => {
  return Math.max(...items.map((item) => item.count), 1)
}

const barWidth = (item, items) => {
  const percent = (item.count / maxCount(items)) * 100
  return `${Math.max(percent, item.count > 0 ? 8 : 0)}%`
}

const riskColor = (name) => {
  if (name.includes('高风险')) {
    return 'var(--danger)'
  }

  if (name.includes('信息不足')) {
    return 'var(--medicine-amber)'
  }

  return 'var(--clinical-green)'
}

const satisfactionColor = (name) => {
  if (name === '5星' || name === '4星') {
    return 'var(--clinical-green)'
  }

  if (name === '3星') {
    return 'var(--medicine-amber)'
  }

  if (name === '2星' || name === '1星') {
    return 'var(--danger)'
  }

  return 'var(--text-muted)'
}

const wordStyle = (item) => {
  const max = maxCount(analytics.value.word_cloud.map((word) => ({
    count: word.value,
  })))
  const ratio = item.value / max

  return {
    fontSize: `${14 + ratio * 20}px`,
    color: ratio > 0.66 ? 'var(--medical-blue)' : ratio > 0.35 ? 'var(--pharmacy-teal)' : 'var(--text-secondary)',
    borderColor: ratio > 0.45 ? 'var(--info-border)' : 'var(--border)',
  }
}

const trendHeight = (item) => {
  const max = maxCount(analytics.value.daily_questions)
  const percent = (item.count / max) * 100
  return `${Math.max(percent, 8)}%`
}

const shortDate = (value = '') => {
  const text = String(value)
  const parts = text.split('-')
  return parts.length >= 2 ? parts.slice(-2).join('/') : text
}

const loadAnalytics = async (force = false) => {
  loading.value = true
  message.value = ''

  try {
    analytics.value = await cachedGetJson('analytics:summary', '/api/analytics/summary', { force })
    lastUpdatedAt.value = new Date()
  } catch (error) {
    console.error(error)
    message.value = '分析数据加载失败，请检查后端服务是否正常运行。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnalytics()
})
</script>

<style scoped>
.analytics-page {
  display: grid;
  gap: 20px;
}

.analytics-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  padding: clamp(26px, 3vw, 36px);
  overflow: hidden;
  background:
    radial-gradient(circle at 92% 0%, rgba(37, 99, 235, 0.13), transparent 34%),
    radial-gradient(circle at 70% 100%, rgba(13, 148, 136, 0.11), transparent 38%),
    linear-gradient(135deg, rgba(248, 251, 255, 0.98), rgba(255, 255, 255, 0.98));
  border-color: #d9e5f1;
  border-radius: 22px;
  box-shadow: 0 18px 46px rgba(27, 57, 91, 0.07);
}

.hero-copy {
  min-width: 0;
}

.hero-kicker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding: 0 9px;
  color: var(--success-text);
  background: rgba(240, 253, 244, 0.92);
  border: 1px solid var(--success-border);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.status-pill i {
  width: 7px;
  height: 7px;
  background: var(--success);
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.1);
}

.eyebrow {
  margin-bottom: 6px;
  color: var(--pharmacy-teal);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.analytics-hero h2 {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: clamp(30px, 4vw, 42px);
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: -0.04em;
}

.analytics-hero .hero-copy > p:not(.eyebrow) {
  max-width: 680px;
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.75;
}

.hero-actions {
  display: flex;
  align-items: flex-end;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 9px;
}

.hero-actions > span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.hero-actions .ui-button {
  flex: 0 0 auto;
  min-height: var(--control-height-lg);
  border-radius: 12px;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.2);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  position: relative;
  min-height: 164px;
  padding: 18px 20px;
  overflow: hidden;
  background: linear-gradient(145deg, #ffffff, #fbfdff);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card::after {
  position: absolute;
  inset: auto 0 0;
  height: 3px;
  content: '';
  background: var(--metric-color);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.metric-blue { --metric-color: var(--primary); --metric-soft: var(--primary-soft); }
.metric-red { --metric-color: var(--danger); --metric-soft: var(--danger-soft); }
.metric-amber { --metric-color: var(--warning); --metric-soft: var(--warning-soft); }
.metric-teal { --metric-color: var(--teal); --metric-soft: var(--teal-soft); }

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 13px;
}

.metric-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: var(--metric-color);
  background: var(--metric-soft);
  border-radius: 11px;
}

.metric-head i {
  color: var(--text-muted);
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.metric-card > strong {
  display: block;
  color: var(--text-primary);
  font-size: 32px;
  font-weight: 900;
  line-height: 1.05;
}

.metric-card > span {
  display: block;
  margin-top: 7px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 800;
}

.metric-card > small {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 11.5px;
  font-weight: 700;
}

.insight-panel {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 17px 20px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.78), rgba(255, 255, 255, 0.96));
  border-color: #dbeafe;
}

.insight-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #7c3aed;
  background: #f5f3ff;
  border-radius: 13px;
}

.insight-copy strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 900;
}

.insight-copy p {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.quick-metrics {
  display: flex;
  gap: 8px;
}

.quick-metrics > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 11px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.quick-metrics strong {
  color: var(--text-primary);
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}

.chart-card {
  min-height: 320px;
  padding: 21px;
  background: rgba(255, 255, 255, 0.94);
  border-color: #dee7f0;
  box-shadow: 0 10px 30px rgba(27, 57, 91, 0.05);
}

.symptoms-card { grid-column: span 8; }
.risk-card { grid-column: span 4; }
.disease-card,
.medicine-card { grid-column: span 6; }
.word-card { grid-column: span 7; }
.satisfaction-card { grid-column: span 5; }
.trend-card { grid-column: span 12; }

.section-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-title h3 {
  color: var(--text-primary);
  font-size: 19px;
  font-weight: 900;
}

.section-title > span {
  padding: 3px 8px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 800;
  white-space: nowrap;
}

.bar-list {
  display: grid;
  gap: 13px;
}

.bar-row {
  display: grid;
  grid-template-columns: 108px minmax(0, 1fr) 42px;
  gap: 12px;
  align-items: center;
}

.bar-row span,
.bar-row strong {
  color: var(--text-secondary);
  font-weight: 900;
}

.bar-row strong {
  text-align: right;
}

.bar-track {
  height: 12px;
  overflow: hidden;
  background: var(--surface-soft);
  border-radius: var(--radius-pill);
}

.bar-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--medical-blue), var(--clinical-green));
  border-radius: inherit;
  transition: width 0.45s ease;
}

.donut-wrap {
  display: flex;
  flex-direction: column;
  gap: 22px;
  align-items: center;
}

.donut {
  position: relative;
  display: grid;
  width: 180px;
  height: 180px;
  place-items: center;
  border-radius: 50%;
}

.donut::after {
  position: absolute;
  width: 110px;
  height: 110px;
  content: "";
  background: #ffffff;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px var(--border);
}

.donut span {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  color: var(--text-primary);
}

.donut span strong {
  font-size: 29px;
  font-weight: 900;
  line-height: 1;
}

.donut span small {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 10.5px;
  font-weight: 800;
}

.legend {
  width: 100%;
  display: grid;
  gap: 9px;
}

.legend div {
  display: grid;
  grid-template-columns: 14px 1fr auto;
  gap: 10px;
  align-items: center;
  color: var(--text-secondary);
  font-weight: 800;
  padding: 8px 10px;
  background: var(--surface-soft);
  border-radius: 9px;
}

.legend i {
  width: 14px;
  height: 14px;
  border-radius: 4px;
}

.rank-list {
  display: grid;
  gap: 12px;
}

.rank-item {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.rank-item:hover {
  background: var(--primary-soft);
  border-color: #dbeafe;
}

.rank-item span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  color: var(--surface);
  background: var(--medical-blue);
  border-radius: var(--radius-sm);
  font-weight: 900;
}

.rank-item.medicine span {
  background: var(--medicine-amber);
}

.rank-item strong {
  color: var(--text-primary);
  font-weight: 900;
}

.rank-item i {
  color: var(--text-muted);
  font-style: normal;
  font-weight: 800;
}

.word-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-content: center;
  min-height: 220px;
  padding: 8px;
  background: radial-gradient(circle at 50% 50%, rgba(239, 246, 255, 0.8), transparent 68%);
  border-radius: 14px;
}

.word-cloud span {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-weight: 900;
}

.satisfaction-list {
  display: grid;
  gap: 14px;
}

.satisfaction-list > div {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) 42px;
  gap: 12px;
  align-items: center;
}

.satisfaction-list span,
.satisfaction-list strong {
  color: var(--text-secondary);
  font-weight: 900;
}

.satisfaction-list div div {
  height: 12px;
  overflow: hidden;
  background: var(--surface-soft);
  border-radius: var(--radius-pill);
}

.satisfaction-list i {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.trend-bars {
  display: flex;
  align-items: end;
  gap: 12px;
  min-height: 230px;
  padding: 28px 10px 0;
  background:
    repeating-linear-gradient(to top, transparent 0 52px, rgba(226, 232, 240, 0.7) 53px 54px);
  border-radius: 12px;
}

.trend-bars div {
  position: relative;
  display: grid;
  flex: 1;
  align-items: end;
  gap: 8px;
  min-width: 42px;
  height: 210px;
}

.trend-bars b {
  position: absolute;
  top: -20px;
  left: 50%;
  color: var(--text-secondary);
  font-size: 10.5px;
  transform: translateX(-50%);
}

.trend-bars i {
  display: block;
  min-height: 10px;
  background: linear-gradient(180deg, var(--clinical-green), var(--medical-blue));
  border-radius: 8px 8px 3px 3px;
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.12);
  transition: height 0.45s ease;
}

.trend-bars span {
  color: var(--text-muted);
  text-align: center;
  font-size: 12px;
  font-weight: 800;
}

.empty-state {
  border-style: dashed;
  box-shadow: none;
  line-height: 1.8;
}

.message {
  font-weight: 800;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 980px) {
  .analytics-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-actions {
    align-items: flex-start;
  }

  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .insight-panel {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .quick-metrics {
    grid-column: 1 / -1;
    padding-left: 56px;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .analytics-hero {
    padding: 22px;
  }

  .hero-kicker-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .hero-actions,
  .hero-actions .ui-button {
    width: 100%;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 150px;
  }

  .insight-panel {
    align-items: flex-start;
    grid-template-columns: auto minmax(0, 1fr);
  }

  .quick-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    width: 100%;
    padding-left: 0;
  }

  .quick-metrics > span {
    white-space: normal;
  }

  .chart-card {
    min-height: 0;
    padding: 18px;
  }

  .section-title {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .bar-row {
    grid-template-columns: 78px minmax(0, 1fr) 30px;
    gap: 8px;
  }

  .satisfaction-list > div {
    grid-template-columns: 52px minmax(0, 1fr) 28px;
    gap: 8px;
  }

  .rank-item {
    grid-template-columns: 32px minmax(0, 1fr) auto;
    gap: 8px;
  }

  .trend-bars {
    min-width: 520px;
  }

  .trend-card {
    overflow-x: auto;
  }
}
</style>
