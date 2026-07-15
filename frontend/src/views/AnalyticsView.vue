<template>
  <div class="analytics-page">
    <section class="analytics-hero">
      <div>
        <p class="eyebrow">DATA COMMAND CENTER</p>
        <h2>数据分析</h2>
        <p>
          所有使用量和质量比例统一基于同一批问答样本。{{ scopeText }}
        </p>
      </div>

      <div class="hero-actions">
        <button type="button" @click="loadAnalytics(true, false)" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新历史统计' }}
        </button>
        <button type="button" class="secondary-action" @click="loadAnalytics(true, true)" :disabled="loading">
          使用当前知识库重新检索
        </button>
      </div>
    </section>

    <section class="kpi-grid">
      <article v-for="card in overviewCards" :key="card.label" :class="['kpi-card', card.tone]">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </article>
    </section>

    <nav class="analytics-tabs" aria-label="数据分析分区">
      <button
        v-for="section in analyticsSections"
        :key="section.value"
        type="button"
        :class="{ active: activeSection === section.value }"
        @click="activeSection = section.value"
      >
        {{ section.label }}
      </button>
    </nav>

    <p v-if="message" class="status-message">{{ message }}</p>

    <section class="section-brief">
      <div>
        <p class="eyebrow">{{ activeSectionMeta.eyebrow }}</p>
        <h3>{{ activeSectionMeta.title }}</h3>
        <span>{{ activeSectionMeta.description }}</span>
      </div>
      <div class="brief-points">
        <span v-for="point in activeSectionMeta.points" :key="point">{{ point }}</span>
      </div>
    </section>

    <section v-if="activeSection === 'overview'" class="section-grid overview-layout">
      <article class="panel wide">
        <div class="section-title">
          <div>
            <p class="eyebrow">OPERATING SIGNALS</p>
            <h3>系统健康信号</h3>
          </div>
          <span>优先看需要处理的异常，而不是把所有图表一次性铺开。</span>
        </div>

        <div class="signal-grid">
          <article v-for="item in signalCards" :key="item.label" :class="['signal-card', item.tone]">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </article>
        </div>
      </article>

      <article class="panel">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">RISK MIX</p>
            <h3>风险分布</h3>
          </div>
        </div>

        <div class="donut-wrap">
          <div class="donut" :style="{ background: riskGradient }">
            <span>{{ totalRisk }}</span>
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

      <article class="panel">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">TREND</p>
            <h3>最近提问趋势</h3>
          </div>
        </div>

        <div v-if="analytics.daily_questions.length" class="trend-bars">
          <div v-for="item in analytics.daily_questions" :key="item.date">
            <i :style="{ height: trendHeight(item) }"></i>
            <span>{{ item.date }}</span>
          </div>
        </div>
        <p v-else class="empty-state">暂无趋势数据。</p>
      </article>

      <article class="panel wide">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">QUESTION MAP</p>
            <h3>用户关注词云</h3>
          </div>
          <span>仅统计用户原始文字中的症状、药品和风险关键词。</span>
        </div>

        <div v-if="analytics.word_cloud.length" class="word-cloud">
          <span v-for="item in analytics.word_cloud" :key="item.text" :style="wordStyle(item)">
            {{ item.text }}
          </span>
        </div>
        <p v-else class="empty-state">暂无词云数据。</p>
      </article>
    </section>

    <section v-if="activeSection === 'questions'" class="section-grid">
      <article class="panel wide">
        <div class="section-title">
          <div>
            <p class="eyebrow">SYMPTOMS</p>
            <h3>症状提问排行</h3>
          </div>
          <span>统计当前肯定症状，同一会话重复提及同一症状只计一次。</span>
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
        <p v-else class="empty-state">暂无症状命中数据。</p>
      </article>

      <article class="panel">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">RAG RETRIEVAL</p>
            <h3>RAG 疾病召回排行</h3>
          </div>
        </div>

        <p class="panel-note">统计历史回答中疾病知识被 RAG 引用的次数，不代表诊断结果或患病人数。</p>

        <div v-if="analytics.disease_stats.length" class="rank-list">
          <div v-for="(item, index) in analytics.disease_stats" :key="item.name" class="rank-item">
            <span>{{ index + 1 }}</span>
            <strong>{{ item.name }}</strong>
            <i>召回 {{ item.count }} 次</i>
          </div>
        </div>
        <p v-else class="empty-state">暂无疾病知识召回记录。</p>
      </article>

      <article class="panel">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">MEDICINES</p>
            <h3>药品咨询排行</h3>
          </div>
        </div>

        <p class="panel-note">统计用户明确咨询并成功匹配的药品，同一会话重复咨询同一药品只计一次。</p>

        <div v-if="analytics.medicine_stats.length" class="rank-list">
          <div v-for="(item, index) in analytics.medicine_stats" :key="item.name" class="rank-item medicine">
            <span>{{ index + 1 }}</span>
            <strong>{{ item.name }}</strong>
            <i>{{ item.count }} 次</i>
          </div>
        </div>
        <p v-else class="empty-state">暂无药品查询记录。</p>
      </article>
    </section>

    <section v-if="activeSection === 'agent'" class="section-grid">
      <article class="panel wide">
        <div class="section-title">
          <div>
            <p class="eyebrow">AGENT FLOW</p>
            <h3>Agent 调度分布</h3>
          </div>
          <span>观察 Agent 是在回答、追问、查药品库，还是频繁进入低置信状态。</span>
        </div>

        <div v-if="analytics.action_distribution.length" class="action-grid">
          <article v-for="item in analytics.action_distribution" :key="item.action" class="action-card">
            <div>
              <strong>{{ item.label }}</strong>
              <span>{{ item.count }} 次</span>
            </div>
            <div class="meter-track">
              <i :style="{ width: actionWidth(item) }"></i>
            </div>
            <small>
              平均可靠性 {{ formatPercent(item.average_confidence) }} · 低置信 {{ item.low_confidence_count }} · 无召回 {{ item.no_retrieval_count }}
            </small>
          </article>
        </div>
        <p v-else class="empty-state">暂无 Agent 调度记录。</p>
      </article>

      <article class="panel">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">RAG QUALITY</p>
            <h3>RAG 检索质量</h3>
          </div>
        </div>

        <div class="metric-stack">
          <div>
            <span>参与评估</span>
            <strong>{{ analytics.rag_quality.total_cases }}</strong>
          </div>
          <div>
            <span>平均召回文档</span>
            <strong>{{ analytics.rag_quality.average_retrieved_count }}</strong>
          </div>
          <div>
            <span>低分召回</span>
            <strong>{{ analytics.rag_quality.low_score_count }}</strong>
          </div>
          <div>
            <span>无召回</span>
            <strong>{{ analytics.rag_quality.no_retrieval_count }}</strong>
          </div>
        </div>
        <p class="panel-note">仅统计实际进入 RAG 症状问答流程的样本，不包含药品查询、追问和危险提醒。</p>
      </article>

      <article class="panel">
        <div class="section-title compact review-title">
          <div>
            <p class="eyebrow">REVIEW</p>
            <h3>审核状态</h3>
          </div>
          <RouterLink class="review-entry" to="/admin?section=review">查看复核样本</RouterLink>
        </div>

        <div class="metric-stack">
          <div>
            <span>待管理员处理</span>
            <strong>{{ analytics.quality_overview.current_unresolved_count }}</strong>
          </div>
          <div>
            <span>低置信回答</span>
            <strong>{{ analytics.quality_overview.low_confidence_count }}</strong>
          </div>
          <div>
            <span>药品知识缺口</span>
            <strong>{{ analytics.quality_overview.medicine_gap_count }}</strong>
          </div>
        </div>
        <p class="panel-note">这里只展示数量，具体问题、完整回答和处理操作统一放在复核样本页面。</p>
      </article>
    </section>

    <section v-if="activeSection === 'agent' && isCurrentRecheck" class="section-grid">
      <article class="panel wide">
        <div class="section-title compact">
          <div>
            <p class="eyebrow">IMPROVED</p>
            <h3>{{ isCurrentRecheck ? '召回已改善样本' : '历史异常尚未重新检索' }}</h3>
          </div>
        </div>

        <div v-if="analytics.improved_cases.length" class="case-list">
          <div v-for="item in analytics.improved_cases.slice(0, 6)" :key="item.record_id" class="case-item improved">
            <div class="improvement-head">
              <b>{{ item.keyword }}</b>
              <span>{{ item.status_label }}</span>
            </div>
            <p>{{ item.question }}</p>
            <div class="improvement-comparison">
              <span>
                最高匹配分
                <strong>{{ formatScore(item.previous_top_score) }}</strong>
                →
                <strong>{{ formatScore(item.current_top_score) }}</strong>
                <i>({{ formatSignedScore(item.score_change) }})</i>
              </span>
              <span>
                召回条目
                <strong>{{ item.previous_retrieved_count }}</strong>
                →
                <strong>{{ item.current_retrieved_count }}</strong>
              </span>
            </div>
            <p v-if="item.added_titles?.length" class="retrieval-change added">
              新增召回：{{ item.added_titles.join('、') }}
            </p>
            <p v-if="item.removed_titles?.length" class="retrieval-change removed">
              不再召回：{{ item.removed_titles.join('、') }}
            </p>
            <p v-if="!item.added_titles?.length && !item.removed_titles?.length" class="retrieval-change">
              召回条目没有变化，主要改善来自匹配分提高。
            </p>
            <small>这里只表示知识检索结果改善，原回答和复核样本不会自动变更。</small>
          </div>
        </div>
        <p v-else class="empty-state">
          {{ isCurrentRecheck ? '暂无召回已改善记录。' : '点击“使用当前知识库重新检索”后查看结果。' }}
        </p>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { cachedGetJson } from '../api'

const loading = ref(false)
const message = ref('')
const activeSection = ref('overview')

const analyticsSections = [
  { label: '总览', value: 'overview' },
  { label: '用户需求', value: 'questions' },
  { label: '质量监控', value: 'agent' },
]

const sectionMeta = {
  overview: {
    eyebrow: 'EXECUTIVE VIEW',
    title: '先看系统是否健康',
    description: '这个分区只保留最关键的运行信号，适合快速判断系统有没有风险、缺口或异常波动。',
    points: ['健康信号', '风险结构', '提问趋势', '关注词云'],
  },
  questions: {
    eyebrow: 'USER DEMAND',
    title: '看用户真正关心什么',
    description: '把症状、疾病和药品需求拆开看，方便决定知识库下一步补什么。',
    points: ['症状排行', '疾病排行', '药品排行'],
  },
  agent: {
    eyebrow: 'AGENT QUALITY',
    title: '看 Agent 调度是否可靠',
    description: '重点观察低置信、无召回、工具调用分布，定位回答变笨或检索失败的原因。',
    points: ['调度分布', 'RAG 质量', '审核状态'],
  },
}

const activeSectionMeta = computed(() => sectionMeta[activeSection.value] || sectionMeta.overview)

const analytics = ref({
  analysis_mode: 'historical_snapshot',
  scope: {
    history_limit: 200,
    sample_count: 0,
    start_time: '',
    end_time: '',
  },
  overview: {
    total_questions: 0,
    warning_count: 0,
    knowledge_count: 0,
    disease_count: 0,
    medicine_count: 0,
    medicine_search_count: 0,
    error_count: 0,
  },
  symptom_stats: [],
  disease_stats: [],
  medicine_stats: [],
  risk_distribution: [],
  word_cloud: [],
  daily_questions: [],
  quality_overview: {
    rechecked_count: 0,
    review_count: 0,
    current_unresolved_count: 0,
    improved_count: 0,
    low_confidence_count: 0,
    medicine_gap_count: 0,
  },
  rag_quality: {
    total_cases: 0,
    average_top_score: 0,
    average_retrieved_count: 0,
    no_retrieval_count: 0,
    low_score_count: 0,
  },
  action_distribution: [],
  knowledge_gaps: [],
  review_suggestions: [],
  improved_cases: [],
  low_confidence_cases: [],
  medicine_gap_stats: [],
})

const isCurrentRecheck = computed(() => analytics.value.analysis_mode === 'current_recheck')

const scopeText = computed(() => {
  const scope = analytics.value.scope || {}
  const count = safeNumber(scope.sample_count)
  const start = String(scope.start_time || '').slice(0, 10)
  const end = String(scope.end_time || '').slice(0, 10)
  const dateRange = start && end ? `，时间 ${start} 至 ${end}` : ''
  return `当前统计最近 ${count} 条问答${dateRange}。`
})

const safeNumber = (value) => {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number : 0
}

const safeDivide = (value, total) => {
  const number = safeNumber(value)
  const base = safeNumber(total)
  if (base <= 0) return 0
  return Math.max(0, Math.min(number / base, 1))
}

const knowledgeTotal = computed(() => {
  const diseaseCount = safeNumber(analytics.value.overview.disease_count)
  const medicineCount = safeNumber(analytics.value.overview.medicine_count)
  return diseaseCount + medicineCount || safeNumber(analytics.value.overview.knowledge_count)
})

const totalRisk = computed(() => {
  return analytics.value.risk_distribution.reduce((sum, item) => sum + safeNumber(item.count), 0)
})

const totalActionCount = computed(() => {
  return analytics.value.action_distribution.reduce((sum, item) => sum + safeNumber(item.count), 0)
})

const warningRatio = computed(() => safeDivide(analytics.value.overview.warning_count, analytics.value.overview.total_questions))

const medicineSearchRatio = computed(() => safeDivide(analytics.value.overview.medicine_search_count, analytics.value.overview.total_questions))

const overviewCards = computed(() => [
  {
    label: '问答样本',
    value: analytics.value.overview.total_questions,
    hint: `最近最多 ${analytics.value.scope?.history_limit || 200} 条`,
    tone: 'primary',
  },
  {
    label: '高风险提醒',
    value: analytics.value.overview.warning_count,
    hint: formatPercent(warningRatio.value),
    tone: 'danger',
  },
  {
    label: '药品查询',
    value: analytics.value.overview.medicine_search_count,
    hint: formatPercent(medicineSearchRatio.value),
    tone: 'medicine',
  },
  {
    label: '知识总量',
    value: knowledgeTotal.value,
    hint: `${analytics.value.overview.disease_count} 疾病 / ${analytics.value.overview.medicine_count} 药品`,
    tone: 'success',
  },
  {
    label: '待复核',
    value: analytics.value.quality_overview.current_unresolved_count,
    hint: '需要管理员处理',
    tone: 'warning',
  },
])

const signalCards = computed(() => {
  const unresolved = safeNumber(analytics.value.quality_overview.current_unresolved_count)
  const lowConfidence = safeNumber(analytics.value.quality_overview.low_confidence_count)
  const noRetrieval = safeNumber(analytics.value.rag_quality.no_retrieval_count)
  const medicineGaps = safeNumber(analytics.value.quality_overview.medicine_gap_count)

  return [
    {
      label: '质量闭环',
      value: `${analytics.value.quality_overview.improved_count}/${analytics.value.quality_overview.review_count}`,
      tone: unresolved > 0 ? 'warning' : 'good',
      hint: unresolved > 0 ? '仍有待复核样本，需要补知识库或调整 Agent。' : '当前没有明显待复核样本。',
    },
    {
      label: '低置信',
      value: lowConfidence,
      tone: lowConfidence > 0 ? 'warning' : 'good',
      hint: lowConfidence > 0 ? '优先检查 RAG 召回、追问策略和文本模型输出。' : '近期可靠性表现稳定。',
    },
    {
      label: '无召回',
      value: noRetrieval,
      tone: noRetrieval > 0 ? 'danger' : 'good',
      hint: noRetrieval > 0 ? '说明知识库覆盖不足或检索关键词需要优化。' : 'RAG 召回覆盖较好。',
    },
    {
      label: '药品缺口',
      value: medicineGaps,
      tone: medicineGaps > 0 ? 'medicine' : 'good',
      hint: medicineGaps > 0 ? '建议补充常见药品说明书和禁忌人群。' : '暂无明显药品库缺口。',
    },
  ]
})

const maxCount = (items) => {
  const values = (items || []).map((item) => safeNumber(item.count || item.value))
  return Math.max(...values, 1)
}

const ratioWidth = (ratio) => {
  const number = Number(ratio || 0)
  if (!Number.isFinite(number) || number <= 0) return '0%'
  return `${Math.max(Math.min(number * 100, 100), 5)}%`
}

const barWidth = (item, items) => {
  const percent = safeDivide(item.count, maxCount(items)) * 100
  return `${Math.max(percent, item.count > 0 ? 7 : 0)}%`
}

const actionWidth = (item) => ratioWidth(safeDivide(item.count, totalActionCount.value))

const trendHeight = (item) => {
  const percent = safeDivide(item.count, maxCount(analytics.value.daily_questions)) * 100
  return `${Math.max(percent, item.count > 0 ? 8 : 0)}%`
}

const formatPercent = (value) => {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return '0%'
  return `${Math.round(number * 100)}%`
}

const formatScore = (value) => safeNumber(value).toFixed(3)

const formatSignedScore = (value) => {
  const number = safeNumber(value)
  return `${number >= 0 ? '+' : ''}${number.toFixed(3)}`
}

const riskColor = (name = '') => {
  if (name.includes('高风险') || name.includes('楂橀')) return 'var(--danger)'
  if (name.includes('不足') || name.includes('无召回') || name.includes('涓嶈冻') || name.includes('鏃犲彫')) {
    return 'var(--medicine-amber)'
  }
  return 'var(--clinical-green)'
}

const riskGradient = computed(() => {
  if (!totalRisk.value) {
    return 'conic-gradient(#e2e8f0 0deg 360deg)'
  }

  let current = 0
  const parts = analytics.value.risk_distribution.map((item) => {
    const start = current
    const end = current + safeDivide(item.count, totalRisk.value) * 360
    current = end
    return `${riskColor(item.name)} ${start}deg ${end}deg`
  })

  return `conic-gradient(${parts.join(', ')})`
})

const wordStyle = (item) => {
  const ratio = safeDivide(item.value, maxCount(analytics.value.word_cloud))
  return {
    fontSize: `${14 + ratio * 18}px`,
    color: ratio > 0.62 ? 'var(--medical-blue)' : ratio > 0.32 ? 'var(--pharmacy-teal)' : 'var(--text-secondary)',
    borderColor: ratio > 0.45 ? '#bfdbfe' : 'var(--border)',
    background: ratio > 0.62 ? '#eff6ff' : '#ffffff',
  }
}

const loadAnalytics = async (force = false, deepRecheck = false) => {
  loading.value = true
  message.value = ''

  try {
    const cacheKey = deepRecheck ? 'analytics:summary:current-recheck' : 'analytics:summary'
    const path = deepRecheck ? '/api/analytics/summary?deep_recheck=true' : '/api/analytics/summary'
    analytics.value = await cachedGetJson(cacheKey, path, {
      force,
      timeoutMs: deepRecheck ? 45000 : 15000,
      fetchOptions: {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('ragToken') || ''}`,
        },
      },
    })
    message.value = deepRecheck
      ? '已使用当前知识库重新检索历史异常样本；结果只表示召回变化，不代表回答已经通过医学复核。'
      : ''
  } catch (error) {
    if (error?.message?.includes('403')) {
      message.value = '管理员登录已失效或权限不足，请重新登录。'
    } else {
      if (error?.name !== 'AbortError') {
        console.error(error)
      }
      message.value = error?.name === 'AbortError'
        ? '分析数据加载超时，请稍后刷新。'
        : '分析数据加载失败，请检查后端服务是否正常运行。'
    }
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
  gap: 22px;
}

.analytics-hero,
.panel,
.analytics-tabs,
.kpi-card {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.hero-actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.secondary-action {
  color: var(--medical-blue);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.review-entry {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 7px 11px;
  color: var(--medical-blue);
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 900;
  text-decoration: none;
}

.analytics-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: clamp(24px, 4vw, 40px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.97), rgba(239, 246, 255, 0.9)),
    #ffffff;
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.analytics-hero h2 {
  color: var(--text-primary);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 900;
  line-height: 1.12;
}

.analytics-hero p {
  max-width: 760px;
  margin-top: 12px;
  color: var(--text-secondary);
  line-height: 1.85;
}

button {
  min-height: 42px;
  padding: 0 16px;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
  transition: transform 0.16s ease, opacity 0.16s ease, background 0.16s ease;
}

button:not(:disabled):active {
  transform: translateY(1px);
}

button:disabled {
  opacity: 0.72;
  background: #94a3b8;
  cursor: not-allowed;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.kpi-card {
  display: grid;
  gap: 8px;
  min-height: 126px;
  padding: 18px;
  border-top: 4px solid var(--medical-blue);
}

.kpi-card span,
.kpi-card small {
  color: var(--text-muted);
  font-weight: 900;
}

.kpi-card strong {
  color: var(--medical-blue);
  font-size: 32px;
  font-weight: 900;
  line-height: 1.1;
}

.kpi-card.danger {
  border-top-color: var(--danger);
}

.kpi-card.danger strong {
  color: var(--danger);
}

.kpi-card.medicine {
  border-top-color: var(--medicine-amber);
}

.kpi-card.medicine strong {
  color: var(--medicine-amber);
}

.kpi-card.success {
  border-top-color: var(--clinical-green);
}

.kpi-card.success strong {
  color: var(--clinical-green);
}

.kpi-card.warning {
  border-top-color: var(--pharmacy-teal);
}

.analytics-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px;
}

.analytics-tabs button {
  min-height: 38px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid var(--border);
}

.analytics-tabs button.active {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.status-message {
  padding: 13px 16px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-weight: 800;
}

.section-brief {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-left: 5px solid var(--pharmacy-teal);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.section-brief h3 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.section-brief span {
  display: block;
  margin-top: 6px;
  color: var(--text-secondary);
  line-height: 1.7;
  font-weight: 800;
}

.brief-points {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 480px;
}

.brief-points span {
  margin: 0;
  padding: 6px 10px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 900;
}

.section-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.overview-layout {
  align-items: stretch;
}

.panel {
  min-height: 300px;
  padding: 22px;
}

.panel.wide {
  grid-column: span 2;
}

.section-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.section-title h3 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.section-title > span {
  max-width: 500px;
  color: var(--text-muted);
  line-height: 1.7;
  font-weight: 800;
}

.section-title.compact {
  margin-bottom: 14px;
}

.panel-note {
  margin: -4px 0 14px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.65;
}

.signal-grid,
.risk-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.signal-card,
.risk-summary article {
  display: grid;
  gap: 8px;
  min-height: 156px;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.signal-card span,
.risk-summary span {
  color: var(--text-muted);
  font-weight: 900;
}

.signal-card strong,
.risk-summary strong {
  color: var(--medical-blue);
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.signal-card p,
.risk-summary p {
  color: var(--text-secondary);
  line-height: 1.65;
}

.signal-card.good {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.signal-card.warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.signal-card.danger {
  background: #fef2f2;
  border-color: #fecaca;
}

.signal-card.medicine {
  background: #fff7ed;
  border-color: #fed7aa;
}

.donut-wrap {
  display: grid;
  grid-template-columns: 178px minmax(0, 1fr);
  gap: 22px;
  align-items: center;
}

.donut {
  position: relative;
  display: grid;
  width: 178px;
  height: 178px;
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
}

.donut span {
  position: relative;
  z-index: 1;
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 900;
}

.legend,
.metric-stack,
.case-list,
.gap-list,
.rank-list,
.action-grid,
.bar-list {
  display: grid;
  gap: 12px;
}

.legend div {
  display: grid;
  grid-template-columns: 14px 1fr auto;
  gap: 10px;
  align-items: center;
  color: var(--text-secondary);
  font-weight: 800;
}

.legend i {
  width: 14px;
  height: 14px;
  border-radius: 4px;
}

.trend-bars {
  display: flex;
  align-items: end;
  gap: 10px;
  min-height: 220px;
  padding-top: 16px;
}

.trend-bars div {
  display: grid;
  flex: 1;
  align-items: end;
  gap: 8px;
  min-width: 34px;
  height: 220px;
}

.trend-bars i {
  display: block;
  min-height: 8px;
  background: linear-gradient(180deg, var(--clinical-green), var(--medical-blue));
  border-radius: 8px 8px 3px 3px;
}

.trend-bars span {
  color: var(--text-muted);
  text-align: center;
  font-size: 12px;
  font-weight: 800;
}

.word-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-content: center;
  min-height: 210px;
}

.word-cloud span {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-weight: 900;
}

.bar-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) 44px;
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

.bar-track,
.meter-track {
  height: 14px;
  overflow: hidden;
  background: #eef4f8;
  border-radius: 999px;
}

.bar-track i,
.meter-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--medical-blue), var(--pharmacy-teal));
  border-radius: inherit;
}

.rank-item {
  display: grid;
  grid-template-columns: 34px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 13px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.rank-item span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  font-weight: 900;
}

.rank-item.medicine span {
  background: var(--medicine-amber);
}

.rank-item strong,
.gap-item b,
.case-item b,
.action-card strong {
  color: var(--text-primary);
  font-weight: 900;
}

.rank-item i {
  color: var(--text-muted);
  font-style: normal;
  font-weight: 800;
}

.action-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.action-card,
.gap-item,
.case-item,
.metric-stack div {
  display: grid;
  gap: 8px;
  padding: 14px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.action-card > div:first-child,
.gap-item div,
.metric-stack div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.action-card span,
.action-card small,
.gap-item span,
.gap-item small,
.case-item small,
.metric-stack span {
  color: var(--text-muted);
  line-height: 1.6;
  font-weight: 800;
}

.metric-stack strong {
  color: var(--medical-blue);
  font-size: 24px;
  font-weight: 900;
}

.split-meter {
  display: flex;
  height: 22px;
  margin-bottom: 18px;
  overflow: hidden;
  background: #eef4f8;
  border-radius: 999px;
}

.split-meter i {
  display: block;
  height: 100%;
}

.split-meter .disease {
  background: var(--medical-blue);
}

.split-meter .medicine {
  background: var(--medicine-amber);
}

.gap-item p,
.case-item p {
  color: var(--text-secondary);
  line-height: 1.7;
}

.case-item.improved {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.improvement-head,
.improvement-comparison {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 18px;
}

.improvement-head span {
  color: #166534;
  font-size: 12px;
  font-weight: 900;
}

.improvement-comparison {
  justify-content: flex-start;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #d1fae5;
  border-radius: 8px;
}

.improvement-comparison span {
  color: var(--text-secondary);
  line-height: 1.7;
}

.improvement-comparison strong {
  margin: 0 4px;
  color: var(--text-primary);
}

.improvement-comparison i {
  color: #166534;
  font-style: normal;
  font-weight: 900;
}

.retrieval-change {
  font-size: 13px;
}

.retrieval-change.added {
  color: #166534;
}

.retrieval-change.removed {
  color: #9a3412;
}

.empty-state {
  padding: 18px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  line-height: 1.8;
}

@media (max-width: 1080px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .signal-grid,
  .risk-summary,
  .action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 780px) {
  .analytics-hero,
  .section-brief,
  .section-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .brief-points {
    justify-content: flex-start;
    max-width: none;
  }

  .kpi-grid,
  .section-grid,
  .signal-grid,
  .risk-summary,
  .action-grid {
    grid-template-columns: 1fr;
  }

  .panel.wide {
    grid-column: span 1;
  }

  .donut-wrap {
    grid-template-columns: 1fr;
    justify-items: center;
  }
}

@media (max-width: 560px) {
  .bar-row {
    grid-template-columns: 1fr;
  }

  .bar-row strong {
    text-align: left;
  }

  .trend-bars {
    overflow-x: auto;
  }

  .trend-bars div {
    flex: 0 0 44px;
  }
}
</style>
