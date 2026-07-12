const DEFAULT_API_BASE_URL = 'http://localhost:8000'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
const memoryCache = new Map()

export const apiUrl = (path) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return `${apiBaseUrl}${normalizedPath}`
}

export const readPageCache = (key) => {
  if (memoryCache.has(key)) {
    return memoryCache.get(key)
  }

  return null
}

export const writePageCache = (key, value) => {
  memoryCache.set(key, value)
  return value
}

export const clearPageCache = (key) => {
  memoryCache.delete(key)
}

export const clearPageCacheByPrefix = (prefix) => {
  Array.from(memoryCache.keys())
    .filter((key) => key.startsWith(prefix))
    .forEach((key) => memoryCache.delete(key))
}

export const cachedGetJson = async (key, path, options = {}) => {
  const { force = false, fetchOptions = {}, timeoutMs = 0 } = options
  const cached = force ? null : readPageCache(key)

  if (cached) {
    return cached
  }

  const controller = timeoutMs > 0 ? new AbortController() : null
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null

  let response
  try {
    response = await fetch(apiUrl(path), {
      ...fetchOptions,
      signal: controller?.signal || fetchOptions.signal,
    })
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
    }
  }

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  const data = await response.json()
  return writePageCache(key, data)
}
