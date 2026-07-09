<template>
  <section v-if="docs.length" class="source-list">
    <div class="panel-heading">
      <span>参考来源</span>
      <b>{{ docs.length }} 条</b>
    </div>
    <details class="source-details">
      <summary>展开知识片段</summary>
      <div
        v-for="(doc, index) in docs"
        :key="sourceKey(doc, index)"
        class="source-card"
      >
        <strong>{{ index + 1 }}. {{ doc.title || '知识片段' }}</strong>
        <span>{{ doc.doc_type === 'medicine' ? '药品' : '常见病' }}</span>
        <p>{{ doc.content }}</p>
      </div>
    </details>
  </section>
</template>

<script setup>
defineProps({
  docs: {
    type: Array,
    default: () => [],
  },
})

const sourceKey = (doc, index) => `${doc?.title || 'source'}-${index}`
</script>

<style scoped>
.source-list {
  display: grid;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-heading span {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 900;
}

.panel-heading b {
  flex: 0 0 auto;
  padding: 2px 8px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.source-details summary {
  color: #1d4ed8;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.source-card {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding: 12px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.source-card span {
  width: fit-content;
  padding: 2px 8px;
  color: #ffffff;
  background: var(--pharmacy-teal);
  border-radius: 999px;
  font-size: 12px;
}
</style>
