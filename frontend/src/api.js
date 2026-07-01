const DEFAULT_API_BASE_URL = 'http://47.113.197.215:8000'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

export const apiUrl = (path) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`

  return `${apiBaseUrl}${normalizedPath}`
}
