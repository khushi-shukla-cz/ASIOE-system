import axios, { AxiosHeaders } from 'axios'
import type { AnalysisResult, SimulationResponse } from '@/types'

const SESSION_TOKEN_STORAGE_KEY = 'asioe_session_token'

export function getSessionToken() {
  return localStorage.getItem(SESSION_TOKEN_STORAGE_KEY)
}

export function setSessionToken(token: string) {
  localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token)
}

export function clearSessionToken() {
  localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY)
}

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000, // 2 min — LLM inference takes time
})

api.interceptors.request.use((config) => {
  const token = getSessionToken()
  if (token) {
    const headers = AxiosHeaders.from(config.headers)
    headers.set('X-Session-Token', token)
    config.headers = headers
  }
  return config
})

// ── Interceptors ──────────────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(msg))
  }
)

// ── Analysis ──────────────────────────────────────────────────────────────────
export async function runAnalysis(
  resumeFile: File,
  jdText: string,
  targetRole?: string,
  maxModules = 20,
  timeConstraintWeeks?: number,
  onProgress?: (pct: number, label: string) => void
): Promise<AnalysisResult> {
  const formData = new FormData()
  formData.append('resume', resumeFile)
  formData.append('jd_text', jdText)
  if (targetRole) formData.append('target_role', targetRole)
  formData.append('max_modules', String(maxModules))
  if (timeConstraintWeeks) formData.append('time_constraint_weeks', String(timeConstraintWeeks))

  // Simulate progress stages
  const progressStages = [
    { pct: 10, label: 'Parsing resume...' },
    { pct: 25, label: 'Extracting skills with AI...' },
    { pct: 45, label: 'Analyzing job description...' },
    { pct: 60, label: 'Computing skill gaps...' },
    { pct: 75, label: 'Building learning graph...' },
    { pct: 88, label: 'Generating adaptive path...' },
    { pct: 95, label: 'Enriching with courses...' },
  ]

  let stageIdx = 0
  const progressInterval = setInterval(() => {
    if (stageIdx < progressStages.length) {
      const s = progressStages[stageIdx]
      onProgress?.(s.pct, s.label)
      stageIdx++
    }
  }, 1800)

  try {
    const res = await api.post<AnalysisResult>('/v1/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const sessionToken = res.headers['x-session-token']
    if (typeof sessionToken === 'string' && sessionToken) {
      setSessionToken(sessionToken)
    }
    clearInterval(progressInterval)
    onProgress?.(100, 'Analysis complete!')
    return res.data
  } catch (err) {
    clearInterval(progressInterval)
    throw err
  }
}

export async function getExplanations(sessionId: string) {
  const res = await api.get(`/v1/explain/${sessionId}`)
  return res.data
}

export async function getGraph(sessionId: string) {
  const res = await api.get(`/v1/graph/${sessionId}`)
  return res.data
}

export async function getMetrics(sessionId: string) {
  const res = await api.get(`/v1/metrics/${sessionId}`)
  return res.data
}

export async function runSimulation(params: {
  sessionId: string
  timeConstraintWeeks: number
  maxModules?: number
  priorityDomains: string[]
}): Promise<SimulationResponse> {
  const res = await api.post<SimulationResponse>('/v1/simulate', {
    session_id: params.sessionId,
    time_constraint_weeks: params.timeConstraintWeeks,
    max_modules: params.maxModules,
    priority_domains: params.priorityDomains,
    exclude_module_ids: [],
  })
  return res.data
}

export async function healthCheck() {
  const res = await api.get('/health')
  return res.data
}

export default api
