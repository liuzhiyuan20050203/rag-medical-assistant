<template>
  <details v-if="message?.trace" class="agent-panel">
    <summary>
      <span>Agent 调度</span>
      <b>{{ labelAction(message.action) }}</b>
    </summary>

    <p class="agent-decision">{{ agentDecisionSummary }}</p>

    <div class="agent-metrics">
      <div>
        <small>意图</small>
        <b>{{ labelIntent(message.intent) }}</b>
      </div>
      <div>
        <small>综合可靠性</small>
        <b>{{ formatConfidence(message.reliability?.final_score ?? message.confidence) }}</b>
      </div>
      <div v-if="message.reliability">
        <small>安全风险</small>
        <b>{{ safetyLevelLabels[message.reliability.safety_level] || message.reliability.safety_level }}</b>
      </div>
    </div>

    <div v-if="message.reliability?.components" class="reliability-breakdown">
      <div v-for="item in reliabilityComponents" :key="item.key">
        <span>{{ item.label }}</span>
        <b>{{ formatConfidence(item.value) }}</b>
      </div>
    </div>

    <p v-if="message.reliability?.method" class="reliability-method">
      {{ message.reliability.method }}
    </p>

    <p>{{ message.trace.summary || message.trace.reason }}</p>

    <div v-if="usedTools.length" class="tool-list">
      <span v-for="tool in usedTools" :key="tool">{{ labelTool(tool) }}</span>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const actionLabels = {
  danger_alert: '危险症状提醒',
  ask_followup: '追问关键信息',
  rag_answer: '症状知识库问答',
  medicine_query: '药品知识库查询',
  image_assist: '图片线索辅助分析',
  empty_input: '等待补充输入',
  agent_error: 'Agent 调度异常',
}

const intentLabels = {
  unknown: '未知输入',
  danger_alert: '疑似危险症状',
  followup: '信息不足需要追问',
  medicine_query: '药品用药咨询',
  image_assist: '图片相关健康咨询',
  symptom_query: '常见症状咨询',
  symptom_image: '症状图片咨询',
  general_health: '一般健康咨询',
}

const toolLabels = {
  normalize_input: '整理文字/语音/图片输入',
  warning_check: '危险症状规则检查',
  rule_planner: '规则意图判断',
  llm_planner: '大模型意图规划',
  medicine_search: '药品知识库查询',
  rag_search: 'RAG 知识库检索',
  llm_answer: '大模型生成回答',
  local_fallback: '本地模板兜底回答',
  agent_chat: 'Agent 统一调度入口',
}

const reliabilityComponentLabels = {
  knowledge_match: '知识库匹配',
  faithfulness: '回答支撑度',
  answer_relevance: '问题相关度',
  input_completeness: '输入完整度',
  consistency: '多轮一致性',
  source_authority: '来源权威度',
}

const safetyLevelLabels = {
  high: '高',
  medium: '中',
  low: '低',
}

const usedTools = computed(() => props.message.trace?.used_tools || [])

const labelAction = (action) => actionLabels[action] || action || '未判断'

const labelIntent = (intent) => intentLabels[intent] || intent || '未识别'

const labelTool = (tool) => toolLabels[tool] || tool

const formatConfidence = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '暂无'
  }

  return `${Math.round(Number(value) * 100)}%`
}

const reliabilityComponents = computed(() => Object.entries(props.message.reliability?.components || {})
  .map(([key, value]) => ({
    key,
    label: reliabilityComponentLabels[key] || key,
    value,
  })))

const agentDecisionSummary = computed(() => {
  const action = labelAction(props.message.action)
  const intent = labelIntent(props.message.intent)
  const tools = usedTools.value.map(labelTool)

  if (props.message.action === 'danger_alert') {
    return 'Agent 决策：识别到可能的危险症状，优先触发安全提醒，并跳过普通咨询流程。'
  }

  if (props.message.action === 'medicine_query') {
    return 'Agent 决策：识别为药品或用药问题，优先调用药品知识库，再组织安全回答。'
  }

  if (props.message.action === 'ask_followup') {
    return 'Agent 决策：当前信息不足，先追问关键症状、持续时间或特殊人群信息。'
  }

  if (props.message.action === 'rag_answer') {
    return 'Agent 决策：识别为常见症状咨询，调用 RAG 知识库检索相关依据后生成回答。'
  }

  if (props.message.action === 'image_assist') {
    return 'Agent 决策：将图片识别结果作为辅助线索，并结合文字描述和知识库进行判断。'
  }

  return `Agent 决策：识别意图为“${intent}”，执行“${action}”${tools.length ? `，调用了${tools.join('、')}` : ''}。`
})
</script>

<style scoped>
.agent-panel {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding: 0;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px dashed #94a3b8;
  border-radius: 8px;
  overflow: hidden;
}

.agent-panel summary,
.agent-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.agent-panel summary {
  min-height: 42px;
  padding: 0 12px;
  color: var(--text-primary);
  cursor: pointer;
  list-style: none;
  font-weight: 900;
}

.agent-panel summary::-webkit-details-marker {
  display: none;
}

.agent-panel summary::after {
  content: '展开';
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.agent-panel[open] summary::after {
  content: '收起';
}

.agent-panel summary b,
.tool-list span {
  padding: 4px 9px;
  border-radius: 999px;
  color: #0f766e;
  background: #ccfbf1;
  font-size: 12px;
  font-weight: 800;
}

.agent-decision {
  margin: 0 12px;
  padding: 10px 12px;
  color: #155e75;
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.6;
}

.agent-metrics div {
  display: grid;
  gap: 2px;
  min-width: 120px;
}

.agent-metrics,
.reliability-breakdown,
.agent-panel > p,
.tool-list {
  margin-right: 12px;
  margin-left: 12px;
}

.agent-panel > .tool-list {
  margin-bottom: 12px;
}

.agent-metrics small {
  color: var(--text-muted);
}

.reliability-breakdown {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.reliability-breakdown div {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-height: 34px;
  padding: 6px 8px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.reliability-breakdown span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.reliability-breakdown b {
  color: var(--text-primary);
  font-size: 13px;
}

.reliability-method {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.tool-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tool-list span {
  color: #4338ca;
  background: #eef2ff;
}
</style>
