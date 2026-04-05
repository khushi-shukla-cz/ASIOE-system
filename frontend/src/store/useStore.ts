import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { AnalysisResult, SimulationRequest } from '@/types'

interface AppState {
  // Session
  sessionId: string | null
  isAnalyzing: boolean
  analysisProgress: number
  progressLabel: string

  // Results
  result: AnalysisResult | null
  activeTab: 'profile' | 'gaps' | 'path' | 'graph' | 'explain' | 'metrics'

  // Simulation
  simulationResult: AnalysisResult['learning_path'] | null
  isSimulating: boolean

  // UI
  selectedModuleId: string | null
  sidebarOpen: boolean

  // Actions
  setSessionId: (id: string) => void
  setAnalyzing: (v: boolean) => void
  setProgress: (pct: number, label?: string) => void
  setResult: (result: AnalysisResult) => void
  setActiveTab: (tab: AppState['activeTab']) => void
  setSimulationResult: (r: AnalysisResult['learning_path']) => void
  setSimulating: (v: boolean) => void
  setSelectedModule: (id: string | null) => void
  reset: () => void
}

const initialState = {
  sessionId: null,
  isAnalyzing: false,
  analysisProgress: 0,
  progressLabel: '',
  result: null,
  activeTab: 'profile' as const,
  simulationResult: null,
  isSimulating: false,
  selectedModuleId: null,
  sidebarOpen: true,
}

export const useStore = create<AppState>()(
  devtools(
    (set) => ({
      ...initialState,

      setSessionId: (id) => set({ sessionId: id }),
      setAnalyzing: (v) => set({ isAnalyzing: v }),
      setProgress: (pct, label) => set({ analysisProgress: pct, progressLabel: label || '' }),
      setResult: (result) => set({ result, isAnalyzing: false, analysisProgress: 100 }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setSimulationResult: (r) => set({ simulationResult: r, isSimulating: false }),
      setSimulating: (v) => set({ isSimulating: v }),
      setSelectedModule: (id) => set({ selectedModuleId: id }),
      reset: () => set(initialState),
    }),
    { name: 'asioe-store' }
  )
)
