<template>
  <div class="home">
    <section class="home-hero" aria-labelledby="home-title">
      <div class="hero-copy">
        <span class="eyebrow">AI MEDICAL ASSISTANT</span>
        <h1 id="home-title">多模态医疗健康 Agent</h1>
        <p>
          一个入口完成症状咨询、用药查询、图片识别和语音输入。系统会先筛查危险信号，
          再结合知识库与大模型给出清晰、可追问的健康参考。
        </p>

        <div class="hero-actions">
          <RouterLink class="primary-action" to="/chat">
            <MessageCircle :size="19" aria-hidden="true" />
            开始咨询
          </RouterLink>
          <RouterLink class="secondary-action" to="/history">
            <History :size="18" aria-hidden="true" />
            查看历史
          </RouterLink>
        </div>
      </div>

      <div class="hero-checklist" aria-label="核心能力">
        <div v-for="item in heroChecks" :key="item.title" class="check-item">
          <component :is="item.icon" :size="22" aria-hidden="true" />
          <div>
            <strong>{{ item.title }}</strong>
            <span>{{ item.description }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="quick-entry" aria-label="常用入口">
      <RouterLink
        v-for="item in quickActions"
        :key="item.title"
        class="entry-card"
        :to="item.to"
      >
        <component :is="item.icon" :size="24" aria-hidden="true" />
        <div>
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </div>
      </RouterLink>
    </section>

    <section class="system-strip" aria-label="系统数据概览">
      <article>
        <strong>{{ stats.knowledge.disease_count }}</strong>
        <span>疾病知识</span>
      </article>
      <article>
        <strong>{{ stats.knowledge.medicine_count }}</strong>
        <span>药品说明</span>
      </article>
      <article>
        <strong>{{ stats.knowledge.warning_rule_count }}</strong>
        <span>危险规则</span>
      </article>
      <article>
        <strong>{{ stats.history.total_history }}</strong>
        <span>累计咨询</span>
      </article>
    </section>

    <section class="flow-section" aria-labelledby="flow-title">
      <div class="section-heading">
        <span class="eyebrow">HOW IT WORKS</span>
        <h2 id="flow-title">用户只需要提问，复杂流程交给 Agent</h2>
      </div>

      <div class="flow-grid">
        <article v-for="item in workflow" :key="item.title" class="flow-card">
          <span>{{ item.step }}</span>
          <strong>{{ item.title }}</strong>
          <p>{{ item.description }}</p>
        </article>
      </div>
    </section>

    <section class="safety-note">
      <ShieldAlert :size="20" aria-hidden="true" />
      <p>
        本系统仅提供健康信息参考，不能替代医生诊断或药师指导。出现胸痛、呼吸困难、
        意识异常、高热不退等情况，请及时就医。
      </p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  BookOpen,
  History,
  MessageCircle,
  SearchCheck,
  ShieldAlert,
  ShieldCheck,
} from '@lucide/vue'
import { cachedGetJson } from '../api'

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

const heroChecks = [
  {
    icon: ShieldCheck,
    title: '先做安全分流',
    description: '优先识别危险症状和需要尽快就医的情况。',
  },
  {
    icon: SearchCheck,
    title: '再检索知识库',
    description: '结合疾病、药品和危险规则做 RAG 检索。',
  },
  {
    icon: MessageCircle,
    title: '最后生成回答',
    description: '用更自然的语言整理建议，并支持继续追问。',
  },
]

const quickActions = [
  {
    icon: MessageCircle,
    title: 'AI 健康助手',
    description: '文字、语音、图片都从这里开始。',
    to: '/chat',
  },
  {
    icon: BookOpen,
    title: '知识库',
    description: '查看疾病、药品和危险规则数据。',
    to: '/knowledge',
  },
  {
    icon: History,
    title: '历史记录',
    description: '继续之前的会话或查看回答。',
    to: '/history',
  },
]

const workflow = [
  {
    step: '01',
    title: '输入问题',
    description: '用户可以直接描述症状，也可以上传药盒、药品说明书或症状表面照片。',
  },
  {
    step: '02',
    title: 'Agent 调度',
    description: '统一处理文本、语音转文字和图片识别结果，判断是否需要追问或检索。',
  },
  {
    step: '03',
    title: '给出建议',
    description: '回答会尽量给出下一步行动、风险提醒和可继续补充的问题。',
  },
]

const loadStats = async (force = false) => {
  try {
    stats.value = await cachedGetJson('home:stats', '/api/stats/summary', { force })
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
  gap: 20px;
}

.home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 28px;
  align-items: center;
  padding: clamp(26px, 4vw, 42px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(241, 248, 251, 0.9)),
    var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.hero-copy {
  min-width: 0;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 10px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.hero-copy h1 {
  max-width: 720px;
  color: var(--text-primary);
  font-size: clamp(34px, 5vw, 48px);
  font-weight: 900;
  line-height: 1.14;
}

.hero-copy p {
  max-width: 760px;
  margin-top: 16px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.85;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

.primary-action,
.secondary-action,
.entry-card {
  text-decoration: none;
}

.primary-action,
.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 900;
}

.primary-action {
  color: #ffffff;
  background: var(--medical-blue);
  border: 1px solid var(--medical-blue);
  box-shadow: 0 12px 22px rgba(37, 99, 235, 0.18);
}

.primary-action:hover {
  background: var(--medical-blue-dark);
}

.secondary-action {
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
}

.secondary-action:hover {
  color: var(--medical-blue);
  background: var(--info-soft);
  border-color: var(--info-border);
}

.hero-checklist {
  display: grid;
  gap: 12px;
}

.check-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 14px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.check-item svg {
  display: grid;
  width: 42px;
  height: 42px;
  padding: 9px;
  color: #0f766e;
  background: #ecfdf5;
  border-radius: 8px;
}

.check-item strong,
.check-item span {
  display: block;
}

.check-item strong {
  color: var(--text-primary);
  font-weight: 900;
}

.check-item span {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.quick-entry {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.entry-card {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-height: 104px;
  padding: 18px;
  color: var(--text-primary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.entry-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.entry-card svg {
  width: 46px;
  height: 46px;
  padding: 10px;
  color: var(--medical-blue);
  background: var(--info-soft);
  border-radius: 8px;
}

.entry-card:nth-child(2) svg {
  color: #0f766e;
  background: #ecfdf5;
}

.entry-card:nth-child(3) svg {
  color: #b45309;
  background: #fffbeb;
}

.entry-card strong,
.entry-card span {
  display: block;
}

.entry-card strong {
  font-size: 17px;
  font-weight: 900;
}

.entry-card span {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.system-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.system-strip article {
  min-height: 74px;
  padding: 12px;
  text-align: center;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.system-strip strong {
  display: block;
  color: var(--medical-blue);
  font-size: 26px;
  font-weight: 900;
  line-height: 1.1;
}

.system-strip span {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
}

.flow-section {
  padding: 22px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.section-heading {
  display: grid;
  gap: 4px;
  margin-bottom: 16px;
}

.section-heading h2 {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 900;
  line-height: 1.3;
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.flow-card {
  display: grid;
  gap: 8px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.flow-card > span {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 900;
}

.flow-card strong {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 900;
}

.flow-card p {
  color: var(--text-secondary);
  line-height: 1.75;
}

.safety-note {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 15px 18px;
  color: #92400e;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  line-height: 1.75;
}

.safety-note svg {
  margin-top: 4px;
  color: #d97706;
}

@media (max-width: 920px) {
  .home-hero {
    grid-template-columns: 1fr;
  }

  .quick-entry,
  .flow-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .home-hero,
  .flow-section {
    padding: 18px;
  }

  .hero-copy h1 {
    font-size: 32px;
  }

  .system-strip {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
