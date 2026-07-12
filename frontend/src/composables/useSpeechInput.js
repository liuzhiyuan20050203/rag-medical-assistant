import { ref } from 'vue'

const getSpeechRecognition = () => {
  if (typeof window === 'undefined') return null

  return window.SpeechRecognition || window.webkitSpeechRecognition
}

export const useSpeechInput = (question) => {
  const recognition = ref(null)
  const isListening = ref(false)
  const speechStatus = ref('')
  const speechRecognitionSupported = ref(false)

  const refreshSpeechSupport = () => {
    speechRecognitionSupported.value = Boolean(getSpeechRecognition())
    return speechRecognitionSupported.value
  }

  const setupRecognition = () => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition || recognition.value) return

    const instance = new SpeechRecognition()
    instance.lang = 'zh-CN'
    instance.continuous = true
    instance.interimResults = true

    let finalText = ''

    instance.onstart = () => {
      finalText = question.value.trim() ? `${question.value.trim()} ` : ''
      isListening.value = true
      speechStatus.value = '正在听，请自然说出你的症状。'
    }

    instance.onresult = (event) => {
      let interimText = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        const transcript = result[0]?.transcript || ''
        if (result.isFinal) {
          finalText += transcript
        } else {
          interimText += transcript
        }
      }

      const recognizedText = `${finalText}${interimText}`.trim()
      if (recognizedText) {
        question.value = recognizedText
        speechStatus.value = interimText ? '正在识别...' : '已识别，可继续说或点击停止。'
      }
    }

    instance.onerror = (event) => {
      isListening.value = false
      speechStatus.value = event.error === 'not-allowed'
        ? '麦克风权限被拒绝，请允许浏览器使用麦克风。'
        : `语音识别失败：${event.error || '未知错误'}`
    }

    instance.onend = () => {
      isListening.value = false
      if (!speechStatus.value.includes('失败') && !speechStatus.value.includes('拒绝')) {
        speechStatus.value = question.value.trim()
          ? '识别已结束，可以检查文字后发送。'
          : '识别已结束，未获取到清晰语音。'
      }
      finalText = question.value
    }

    recognition.value = instance
  }

  const toggleVoiceInput = () => {
    if (!refreshSpeechSupport()) {
      speechStatus.value = '当前浏览器不支持语音识别，建议使用 Chrome 或 Edge。'
      return
    }

    setupRecognition()

    if (isListening.value) {
      recognition.value?.stop()
      return
    }

    speechStatus.value = ''
    recognition.value?.start()
  }

  const stopRecognition = () => {
    recognition.value?.stop()
  }

  return {
    isListening,
    speechStatus,
    speechRecognitionSupported,
    refreshSpeechSupport,
    toggleVoiceInput,
    stopRecognition,
  }
}
