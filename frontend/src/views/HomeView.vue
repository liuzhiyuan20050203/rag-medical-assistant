<template>
  <div class="home">
    <section class="hero" aria-labelledby="home-title">
      <div class="hero-copy">
        <p class="eyebrow">RAG MEDICAL ASSISTANT</p>
        <h1 id="home-title">医院级导诊与安全用药参考</h1>
        <p>
          面向常见轻微症状，系统会先筛查胸痛、呼吸困难、高热不退等危险信号，
          再结合常见病与药品知识库生成结构化参考建议，帮助用户更快判断下一步。
        </p>

        <div class="actions">
          <RouterLink class="btn primary" to="/chat">开始症状自查</RouterLink>
          <RouterLink class="btn" to="/medicine">进入药品查询</RouterLink>
        </div>

        <div class="hero-tags" aria-label="核心能力">
          <span>危险症状优先分诊</span>
          <span>常见病知识检索</span>
          <span>药师级用药提示</span>
        </div>
      </div>

      <div class="hospital-visual" aria-hidden="true">
        <div class="building">
          <div class="building-top">
            <span>门诊导诊台</span>
            <svg viewBox="0 0 24 24">
              <path d="M9.2 3.8h5.6v5.4h5.4v5.6h-5.4v5.4H9.2v-5.4H3.8V9.2h5.4z" />
            </svg>
          </div>
          <div class="window-grid">
            <i></i>
            <i></i>
            <i></i>
            <i></i>
            <i></i>
            <i></i>
            <i></i>
            <i></i>
            <i></i>
          </div>
        </div>

        <div class="vital-card">
          <span>AI 预问诊</span>
          <strong>风险分级</strong>
          <div class="pulse-line"></div>
        </div>

        <div class="pharmacy-card">
          <span>智慧药房</span>
          <div class="capsules">
            <i></i>
            <i></i>
            <i></i>
          </div>
          <strong>禁忌 / 不良反应 / 注意事项</strong>
        </div>
      </div>
    </section>

    <section class="stats" aria-label="系统数据概览">
      <article class="stat-card">
        <strong>{{ stats.knowledge.disease_count }}</strong>
        <span>常见病知识</span>
      </article>

      <article class="stat-card">
        <strong>{{ stats.knowledge.medicine_count }}</strong>
        <span>常见药品</span>
      </article>

      <article class="stat-card">
        <strong>{{ stats.knowledge.warning_rule_count }}</strong>
        <span>危险症状规则</span>
      </article>

      <article class="stat-card">
        <strong>{{ stats.history.total_history }}</strong>
        <span>累计问答记录</span>
      </article>

      <article class="stat-card warning">
        <strong>{{ stats.history.warning_count }}</strong>
        <span>危险提醒次数</span>
      </article>

      <article class="stat-card">
        <strong>{{ stats.history.rag_count }}</strong>
        <span>RAG 检索问答</span>
      </article>
    </section>

    <section class="workflow">
      <div class="section-heading">
        <p class="eyebrow">CLINICAL WORKFLOW</p>
        <h2>从症状到用药的清晰路径</h2>
      </div>

      <div class="route-grid">
        <article
          v-for="item in clinicalRoutes"
          :key="item.title"
          class="route-card"
        >
          <span>{{ item.step }}</span>
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="pharmacy-band" aria-labelledby="pharmacy-title">
      <div>
        <p class="eyebrow">PHARMACY SAFETY</p>
        <h2 id="pharmacy-title">把药品信息做成可读的安全清单</h2>
        <p>
          查询药品时，页面会把适用情况、禁忌人群、注意事项、不良反应拆开呈现，
          更适合用户和药师快速核对。
        </p>
      </div>

      <div class="pharmacy-list">
        <article
          v-for="item in pharmacyHighlights"
          :key="item.title"
          class="pharmacy-item"
        >
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </article>
      </div>
    </section>

    <section class="notice">
      <strong>安全提示：</strong>
      本系统仅提供健康信息参考，不能替代医生诊断或药师指导。如症状严重或持续加重，请及时就医。
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref({
  knowledge: {
    disease_count: 0,
    medicine_count: 0,
    warning_rule_count: 0,
    total_knowledge_count: 0,
  },
  history: {
    total_history: 0,
    warning_count: 0,
    rag_count: 0,
  },
})

const clinicalRoutes = [
  {
    step: '01',
    title: '危险症状预筛查',
    description: '优先识别胸痛、呼吸困难、意识异常等信号，避免把高风险情况误当作普通咨询。',
  },
  {
    step: '02',
    title: '常见病知识匹配',
    description: '结合症状描述检索疾病知识库，返回可能相关方向、护理建议和就医提醒。',
  },
  {
    step: '03',
    title: '用药安全核对',
    description: '围绕药品类别、禁忌人群和不良反应进行说明，强调遵医嘱和说明书。',
  },
]

const pharmacyHighlights = [
  {
    title: '药品类别',
    description: '解热镇痛、抗过敏、止泻补液等常见类别清晰归档。',
  },
  {
    title: '禁忌人群',
    description: '儿童、孕妇、老人、慢性病患者等特殊人群重点提示。',
  },
  {
    title: '不良反应',
    description: '胃肠不适、嗜睡、过敏等风险按字段单独展示。',
  },
]

const loadStats = async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/stats/summary')
    const data = await response.json()

    stats.value = data
  } catch (error) {
    console.error('统计数据加载失败：', error)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.home {
  display: grid;
  gap: 28px;
}

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
  gap: 36px;
  align-items: center;
  overflow: hidden;
  min-height: 420px;
  padding: clamp(30px, 5vw, 58px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(232, 248, 250, 0.86)),
    radial-gradient(circle at 85% 20%, rgba(37, 99, 235, 0.16), transparent 30%);
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 8px;
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.eyebrow {
  margin-bottom: 10px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.hero h1 {
  max-width: 640px;
  color: var(--text-primary);
  font-size: clamp(34px, 5vw, 56px);
  font-weight: 900;
  line-height: 1.08;
}

.hero-copy > p:not(.eyebrow) {
  max-width: 680px;
  margin-top: 20px;
  color: var(--text-secondary);
  font-size: 17px;
  line-height: 1.9;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 20px;
  color: var(--text-primary);
  text-decoration: none;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  font-weight: 800;
}

.btn.primary {
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--pharmacy-teal));
  border-color: transparent;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.hero-tags span {
  padding: 7px 10px;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #bce7dd;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
}

.hospital-visual {
  position: relative;
  min-height: 340px;
}

.building {
  position: absolute;
  right: 24px;
  bottom: 8px;
  width: min(320px, 82%);
  padding: 18px;
  background: #ffffff;
  border: 1px solid #cfe3ee;
  border-radius: 8px;
  box-shadow: var(--shadow-md);
}

.building-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 8px;
}

.building-top span {
  font-weight: 800;
}

.building-top svg {
  width: 28px;
  height: 28px;
  fill: currentColor;
}

.window-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}

.window-grid i {
  display: block;
  height: 46px;
  background:
    linear-gradient(180deg, rgba(226, 246, 255, 0.95), rgba(202, 232, 246, 0.8)),
    #e7f3f8;
  border: 1px solid #cfe3ee;
  border-radius: 6px;
}

.vital-card,
.pharmacy-card {
  position: absolute;
  left: 4px;
  width: 230px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(14, 116, 144, 0.18);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.vital-card {
  top: 20px;
}

.pharmacy-card {
  bottom: 26px;
}

.vital-card span,
.pharmacy-card span {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.vital-card strong,
.pharmacy-card strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-weight: 900;
}

.pulse-line {
  position: relative;
  height: 46px;
  margin-top: 10px;
  overflow: hidden;
  background: #eef7fb;
  border-radius: 6px;
}

.pulse-line::before {
  position: absolute;
  inset: 11px 10px;
  content: "";
  background:
    linear-gradient(135deg, transparent 0 16%, var(--danger) 17% 20%, transparent 21% 32%, var(--danger) 33% 36%, transparent 37% 50%, var(--danger) 51% 54%, transparent 55% 100%);
}

.capsules {
  display: flex;
  gap: 8px;
  margin: 13px 0 10px;
}

.capsules i {
  display: block;
  width: 42px;
  height: 18px;
  background: linear-gradient(90deg, #22c55e 50%, #f8fafc 50%);
  border: 1px solid #b7d4df;
  border-radius: 999px;
}

.capsules i:nth-child(2) {
  background: linear-gradient(90deg, #38bdf8 50%, #f8fafc 50%);
}

.capsules i:nth-child(3) {
  background: linear-gradient(90deg, #f59e0b 50%, #f8fafc 50%);
}

.stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
}

.stat-card {
  min-height: 112px;
  padding: 20px 16px;
  text-align: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.stat-card strong {
  display: block;
  color: var(--medical-blue);
  font-size: 31px;
  font-weight: 900;
  line-height: 1.15;
}

.stat-card span {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-weight: 800;
}

.stat-card.warning strong {
  color: var(--danger);
}

.workflow,
.pharmacy-band,
.notice {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.workflow {
  padding: 28px;
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h2,
.pharmacy-band h2 {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 900;
  line-height: 1.3;
}

.route-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.route-card {
  padding: 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.route-card span {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  font-weight: 900;
}

.route-card h3 {
  margin-top: 16px;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.route-card p {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.pharmacy-band {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(320px, 1.1fr);
  gap: 28px;
  align-items: center;
  padding: 28px;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.84), rgba(236, 253, 245, 0.84)),
    #ffffff;
}

.pharmacy-band p:not(.eyebrow) {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.85;
}

.pharmacy-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.pharmacy-item {
  min-height: 132px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #cfe3ee;
  border-radius: 8px;
}

.pharmacy-item strong {
  display: block;
  color: var(--pharmacy-teal);
  font-size: 17px;
  font-weight: 900;
}

.pharmacy-item span {
  display: block;
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.notice {
  padding: 18px 22px;
  color: #92400e;
  background: #fff7ed;
  border-color: #fed7aa;
  line-height: 1.8;
}

.notice strong {
  font-weight: 900;
}

@media (max-width: 980px) {
  .hero,
  .pharmacy-band {
    grid-template-columns: 1fr;
  }

  .hospital-visual {
    min-height: 300px;
  }

  .stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .route-grid,
  .pharmacy-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero,
  .workflow,
  .pharmacy-band {
    padding: 22px;
  }

  .hero h1 {
    font-size: 32px;
  }

  .hospital-visual {
    min-height: 330px;
  }

  .building {
    right: 0;
    width: 92%;
  }

  .vital-card,
  .pharmacy-card {
    left: 0;
    width: 210px;
  }

  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
