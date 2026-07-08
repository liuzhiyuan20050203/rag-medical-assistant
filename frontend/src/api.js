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
  const { force = false, fetchOptions = {} } = options
  const cached = force ? null : readPageCache(key)

  if (cached) {
    return cached
  }

  const response = await fetch(apiUrl(path), fetchOptions)
  const data = await response.json()
  return writePageCache(key, data)
}
