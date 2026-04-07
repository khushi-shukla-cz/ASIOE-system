import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain, User, BarChart3, GitBranch, Network,
  Terminal, Sliders, ArrowLeft,
  CheckCircle, Clock, Zap, Layers
} from 'lucide-react'
import { useStore } from '@/store/useStore'
import SkillProfileView from '@/components/dashboard/SkillProfileView'
import GapAnalysisView from '@/components/dashboard/GapAnalysisView'
import LearningPathView from '@/components/dashboard/LearningPathView'
import SkillGraphD3 from '@/components/graph/SkillGraphD3'
import ExplainabilityConsole from '@/components/explainability/ExplainabilityConsole'
import SimulationPanel from '@/components/dashboard/SimulationPanel'
import { formatPercent } from '@/utils/helpers'
import { readinessColor } from '@/utils/helpers'

type Tab = 'profile' | 'gaps' | 'path' | 'graph' | 'explain' | 'simulate'

const TABS: { id: Tab; label: string; icon: any; description: string }[] = [
  { id: 'profile', label: 'Skill Profile', icon: User, description: 'Extracted skills from resume and JD' },
  { id: 'gaps', label: 'Gap Analysis', icon: BarChart3, description: 'Competency gap breakdown' },
  { id: 'path', label: 'Learning Path', icon: GitBranch, description: 'Adaptive personalized curriculum' },
  { id: 'graph', label: 'Skill Graph', icon: Network, description: 'Knowledge DAG visualization' },
  { id: 'explain', label: 'Explainability', icon: Terminal, description: 'Full reasoning traces' },
  { id: 'simulate', label: 'Simulate', icon: Sliders, description: 'Dynamic path recomputation' },
]

function EmptyState() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-cream flex items-center justify-center p-6">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
          <Brain size={28} className="text-slate-400" />
        </div>
        <h2 className="font-display text-2xl text-slate-800 mb-2">No Analysis Yet</h2>
        <p className="text-slate-400 text-sm mb-6">
          Run an analysis first to see your adaptive learning path.
        </p>
        <button onClick={() => navigate('/analyze')} className="btn-primary">
          Start Analysis
        </button>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { result, sessionId, simulationResult, clearSimulationResult } = useStore()
  const [activeTab, setActiveTab] = useState<Tab>('profile')

  if (!result || !result.gap_analysis || !result.learning_path) {
    return <EmptyState />
  }

  const { skill_profile, gap_analysis, learning_path, reasoning_trace } = result
  const readiness = gap_analysis.overall_readiness_score
  const rColor = readinessColor(readiness)

  return (
    <div className="min-h-screen bg-cream">
      {/* Top Nav */}
      <nav className="fixed top-0 w-full z-50 bg-white border-b border-slate-100 shadow-sm">
        <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/analyze')}
              className="flex items-center gap-2 text-slate-400 hover:text-slate-700 transition-colors text-sm"
            >
              <ArrowLeft size={15} />
              New Analysis
            </button>
            <div className="w-px h-4 bg-slate-200" />
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-slate-800 flex items-center justify-center">
                <Brain size={12} className="text-white" />
              </div>
              <span className="font-display text-base text-slate-800">ASIOE</span>
              <span className="text-xs font-mono text-slate-400 ml-1">
                {sessionId?.slice(0, 8)}...
              </span>
            </div>
          </div>

          {/* Quick stats */}
          <div className="hidden md:flex items-center gap-4">
            <div className="text-xs">
              {simulationResult ? (
                <button
                  onClick={clearSimulationResult}
                  className="px-2 py-1 rounded-md bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors"
                >
                  Simulated Path Active · View Original
                </button>
              ) : (
                <span className="px-2 py-1 rounded-md bg-slate-50 text-slate-500 border border-slate-200">
                  Baseline Path
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <CheckCircle size={13} className="text-sage-500" />
              <span>{skill_profile?.skills.length || 0} skills extracted</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Layers size={13} className="text-sky-500" />
              <span>{learning_path.total_modules} modules</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Clock size={13} className="text-amber-500" />
              <span>{learning_path.total_hours.toFixed(0)}h total</span>
            </div>
            <div
              className="flex items-center gap-1.5 text-xs font-semibold"
              style={{ color: rColor }}
            >
              <Zap size={13} />
              <span>{formatPercent(readiness)} ready</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="pt-14 flex">
        {/* Sidebar tabs */}
        <aside className="fixed left-0 top-14 h-[calc(100vh-3.5rem)] w-52 bg-white border-r border-slate-100 flex flex-col py-4 px-3 z-40 overflow-y-auto">
          {/* Role header */}
          <div className="px-2 mb-4">
            <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-0.5">
              Target Role
            </p>
            <p className="text-sm font-semibold text-slate-800 leading-tight">
              {learning_path.target_role || 'Analyzed Role'}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 progress-bar h-1.5">
                <motion.div
                  className="progress-fill"
                  style={{ width: `${readiness * 100}%`, backgroundColor: rColor }}
                  initial={{ width: 0 }}
                  animate={{ width: `${readiness * 100}%` }}
                  transition={{ duration: 1, delay: 0.5 }}
                />
              </div>
              <span className="text-[10px] font-mono font-semibold" style={{ color: rColor }}>
                {formatPercent(readiness)}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">{gap_analysis.readiness_label}</p>
          </div>

          <div className="w-full h-px bg-slate-100 mb-3" />

          {/* Tab buttons */}
          <nav className="space-y-1 flex-1">
            {TABS.map(tab => {
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left
                    transition-all duration-150 text-sm
                    ${isActive
                      ? 'bg-slate-800 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
                    }
                  `}
                >
                  <tab.icon size={15} className={isActive ? 'text-white' : 'text-slate-400'} />
                  <span className="font-medium">{tab.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Gap severity mini summary */}
          <div className="mt-4 border-t border-slate-100 pt-4 space-y-1.5 px-1">
            <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wide mb-2">
              Gap Summary
            </p>
            {[
              { label: 'Critical', count: gap_analysis.critical_gaps.length, color: 'bg-rose-400' },
              { label: 'Major', count: gap_analysis.major_gaps.length, color: 'bg-amber-400' },
              { label: 'Minor', count: gap_analysis.minor_gaps.length, color: 'bg-sky-400' },
            ].map(({ label, count, color }) => (
              <div key={label} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${color}`} />
                <span className="text-xs text-slate-500 flex-1">{label}</span>
                <span className="text-xs font-bold text-slate-700">{count}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main className="ml-52 flex-1 p-6 min-h-[calc(100vh-3.5rem)]">
          {/* Tab header */}
          <div className="mb-6">
            {TABS.filter(t => t.id === activeTab).map(tab => (
              <div key={tab.id}>
                <h1 className="font-display text-2xl text-slate-900">{tab.label}</h1>
                <p className="text-slate-400 text-sm mt-0.5">{tab.description}</p>
              </div>
            ))}
          </div>

          {/* Tab content */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25 }}
            >
              {activeTab === 'profile' && skill_profile && (
                <SkillProfileView profile={skill_profile as any} />
              )}

              {activeTab === 'gaps' && (
                <GapAnalysisView gap={gap_analysis} />
              )}

              {activeTab === 'path' && (
                <LearningPathView path={learning_path} />
              )}

              {activeTab === 'graph' && (
                <div className="card overflow-hidden">
                  <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-800 text-sm">Skill Knowledge Graph</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {learning_path.path_graph.nodes.length} nodes · {learning_path.path_graph.edges.length} edges
                        · Drag to rearrange · Scroll to zoom
                      </p>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span>Phase ① → ② → ③</span>
                    </div>
                  </div>
                  <SkillGraphD3
                    graph={learning_path.path_graph}
                    onNodeClick={(node) => {
                      setActiveTab('explain' as Tab)
                    }}
                  />
                </div>
              )}

              {activeTab === 'explain' && reasoning_trace && (
                <ExplainabilityConsole
                  trace={reasoning_trace}
                  path={learning_path}
                />
              )}

              {activeTab === 'simulate' && sessionId && (
                <SimulationPanel
                  sessionId={sessionId}
                  originalPath={learning_path}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
