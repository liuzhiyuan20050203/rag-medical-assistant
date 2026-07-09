<template>
  <div class="analytics-page">
    <section class="analytics-hero ui-card">
      <div>
        <p class="eyebrow">DATA ANALYTICS</p>
        <h2>可视化分析</h2>
        <p>
          汇总用户症状提问、疾病检索、药品查询、风险等级和回答反馈，体现系统的数据分析能力。
        </p>
      </div>

      <button class="ui-button ui-button--primary" type="button" @click="loadAnalytics(true)" :disabled="loading">
        {{ loading ? '加载中...' : '刷新分析' }}
      </button>
    </section>

    <section class="overview-grid">
      <article class="ui-card">
        <strong>{{ analytics.overview.total_questions }}</strong>
        <span>用户提问</span>
      </article>
      <article class="ui-card">
        <strong>{{ analytics.overview.warning_count }}</strong>
        <span>高风险提醒</span>
      </article>
      <article class="ui-card">
        <strong>{{ analytics.overview.medicine_search_count }}</strong>
        <span>药品查询</span>
      </article>
      <article class="ui-card">
        <strong>{{ analytics.overview.error_count }}</strong>
        <span>错误标记</span>
      </article>
      <article class="ui-card">
        <strong>{{ analytics.overview.average_rating || 0 }}</strong>
        <span>平均评分</span>
      </article>
      <article class="ui-card">
        <strong>{{ analytics.overview.knowledge_count }}</strong>
        <span>知识总量</span>
      </article>
    </section>

    <section class="chart-grid">
      <article class="chart-card wide ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">SYMPTOMS</p>
            <h3>常见症状统计</h3>
          </div>
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

      <article class="chart-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">DISEASES</p>
            <h3>高频疾病查询统计</h3>
          </div>
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

      <article class="chart-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">MEDICINES</p>
            <h3>高频药品查询统计</h3>
          </div>
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

      <article class="chart-card wide ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">WORD CLOUD</p>
            <h3>用户提问词云</h3>
          </div>
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

      <article class="chart-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">SATISFACTION</p>
            <h3>系统回答满意度统计</h3>
          </div>
        </div>

        <div class="satisfaction-list">
          <div v-for="item in analytics.satisfaction" :key="item.name">
            <span>{{ item.name }}</span>
            <div>
              <i :style="{ width: barWidth(item, analytics.satisfaction), background: satisfactionColor(item.name) }"></i>
            </div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
      </article>

      <article class="chart-card ui-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">TREND</p>
            <h3>提问趋势</h3>
          </div>
        </div>

        <div v-if="analytics.daily_questions.length" class="trend-bars">
          <div v-for="item in analytics.daily_questions" :key="item.date">
            <i :style="{ height: trendHeight(item) }"></i>
            <span>{{ item.date }}</span>
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
import { cachedGetJson } from '../api'

const loading = ref(false)
const message = ref('')

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

const loadAnalytics = async (force = false) => {
  loading.value = true
  message.value = ''

  try {
    analytics.value = await cachedGetJson('analytics:summary', '/api/analytics/summary', { force })
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
  gap: 24px;
}

.analytics-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: clamp(24px, 4vw, 42px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(236, 253, 245, 0.86)),
    var(--surface);
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
  max-width: 720px;
  margin-top: 12px;
  color: var(--text-secondary);
  line-height: 1.9;
}

.analytics-hero .ui-button {
  flex: 0 0 auto;
  min-height: var(--control-height-lg);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
}

.overview-grid article {
  min-height: 108px;
  padding: 20px 14px;
  text-align: center;
}

.overview-grid strong {
  display: block;
  color: var(--medical-blue);
  font-size: 30px;
  font-weight: 900;
  line-height: 1.15;
}

.overview-grid span {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-weight: 800;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.chart-card {
  min-height: 340px;
  padding: 22px;
}

.chart-card.wide {
  grid-column: span 2;
}

.section-title {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-title h3 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
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
  height: 16px;
  overflow: hidden;
  background: var(--surface-soft);
  border-radius: var(--radius-pill);
}

.bar-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--medical-blue), var(--clinical-green));
  border-radius: inherit;
}

.donut-wrap {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 24px;
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
  background: var(--surface);
  border-radius: 50%;
}

.donut span {
  position: relative;
  z-index: 1;
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 900;
}

.legend {
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
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
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
  min-height: 210px;
}

.word-cloud span {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 4px 12px;
  background: #f8fbfd;
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
  height: 16px;
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
  min-height: 210px;
  padding-top: 16px;
}

.trend-bars div {
  display: grid;
  flex: 1;
  align-items: end;
  gap: 8px;
  min-width: 42px;
  height: 210px;
}

.trend-bars i {
  display: block;
  min-height: 10px;
  background: linear-gradient(180deg, var(--clinical-green), var(--medical-blue));
  border-radius: 8px 8px 3px 3px;
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

@media (max-width: 980px) {
  .analytics-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .overview-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-card.wide {
    grid-column: span 1;
  }
}

@media (max-width: 640px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .bar-row,
  .satisfaction-list > div,
  .rank-item {
    grid-template-columns: 1fr;
  }

  .bar-row strong,
  .satisfaction-list strong {
    text-align: left;
  }

  .donut-wrap {
    grid-template-columns: 1fr;
  }
}
</style>
