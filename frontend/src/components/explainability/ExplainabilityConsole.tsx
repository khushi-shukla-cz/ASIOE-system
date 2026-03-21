import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronRight, Search, Code2, Database,
  GitBranch, Cpu, Layers, Zap, BarChart3
} from 'lucide-react'
import type { SystemReasoningTrace, LearningPathResult } from '@/types'
import { domainColors, difficultyColors } from '@/utils/helpers'

interface Props {
  trace: SystemReasoningTrace
  path: LearningPathResult
}

const ENGINE_ICONS: Record<string, any> = {
  parsing_trace:       { icon: Database, label: 'Parsing Engine', color: 'text-sky-500', bg: 'bg-sky-50' },
  normalization_trace: { icon: Code2,    label: 'Normalization Engine', color: 'text-sage-600', bg: 'bg-sage-50' },
  gap_trace:           { icon: BarChart3, label: 'Gap Analysis Engine', color: 'text-rose-500', bg: 'bg-rose-50' },
  path_trace:          { icon: GitBranch, label: 'Path Engine', color: 'text-amber-600', bg: 'bg-amber-50' },
}

function TraceBlock({ traceKey, text }: { traceKey: string; text: string }) {
  const [open, setOpen] = useState(false)
  const meta = ENGINE_ICONS[traceKey]
  if (!meta) return null
  const { icon: Icon, label, color, bg } = meta

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-slate-100 rounded-xl overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 bg-white hover:bg-slate-50 transition-colors text-left"
      >
        <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center flex-shrink-0`}>
          <Icon size={15} className={color} />
        </div>
        <span className="font-medium text-sm text-slate-700 flex-1">{label}</span>
        <ChevronRight
          size={15}
          className={`text-slate-400 transition-transform ${open ? 'rotate-90' : ''}`}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 bg-white border-t border-slate-50">
              <pre className="text-xs text-slate-600 leading-relaxed font-mono whitespace-pre-wrap mt-3 bg-slate-50 rounded-lg p-3">
                {text}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ExplainabilityConsole({ trace, path }: Props) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedModuleIdx, setSelectedModuleIdx] = useState<number | null>(null)

  const allModules = path.phases.flatMap(p => p.modules)
  const filtered = allModules.filter(m =>
    !searchTerm ||
    m.skill_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.domain.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const selectedModule = selectedModuleIdx !== null ? allModules[selectedModuleIdx] : null

  return (
    <div className="space-y-6">
      {/* Token & model metadata */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Cpu, label: 'Model Used', value: trace.model_used.replace('llama-', 'Llama '), color: 'bg-sky-50 text-sky-500' },
          { icon: Zap, label: 'Total Tokens', value: trace.total_tokens_used.toLocaleString(), color: 'bg-amber-50 text-amber-600' },
          { icon: Layers, label: 'Total Modules', value: String(path.total_modules), color: 'bg-sage-50 text-sage-600' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="card p-4 flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
              <Icon size={16} className="text-current" />
            </div>
            <div>
              <p className="text-xs text-slate-400">{label}</p>
              <p className="font-semibold text-slate-800 text-sm">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* System-level engine traces */}
      <div>
        <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide mb-3">
          Engine Reasoning Traces
        </h3>
        <div className="space-y-2">
          {Object.entries(ENGINE_ICONS).map(([key]) => (
            <TraceBlock
              key={key}
              traceKey={key}
              text={(trace as any)[key] || 'No trace available'}
            />
          ))}
        </div>
      </div>

      {/* Per-module explainability */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <h3 className="font-semibold text-slate-700 text-sm uppercase tracking-wide">
            Module-Level Explanations
          </h3>
          <div className="relative flex-1 max-w-xs">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search skills..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="input-field pl-8 py-2 text-xs"
            />
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-4">
          {/* Module list */}
          <div className="space-y-1.5 max-h-[480px] overflow-y-auto pr-1">
            {filtered.map((mod, i) => {
              const dc = domainColors[mod.domain] ?? domainColors.technical
              const isSelected = selectedModuleIdx === allModules.indexOf(mod)
              return (
                <button
                  key={mod.module_id}
                  onClick={() => setSelectedModuleIdx(allModules.indexOf(mod))}
                  className={`
                    w-full text-left p-3 rounded-xl border transition-all duration-150
                    ${isSelected
                      ? 'bg-slate-800 border-slate-800 text-white'
                      : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-mono ${isSelected ? 'text-slate-300' : 'text-slate-400'}`}>
                      {String(mod.sequence_order).padStart(2, '0')}
                    </span>
                    <span className={`font-medium text-sm flex-1 ${isSelected ? 'text-white' : 'text-slate-800'}`}>
                      {mod.skill_name}
                    </span>
                    <span className={`badge ${dc.bg} ${dc.text} text-[10px] ${isSelected ? 'opacity-80' : ''}`}>
                      {mod.domain.replace('_', ' ')}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Detail pane */}
          <AnimatePresence mode="wait">
            {selectedModule ? (
              <motion.div
                key={selectedModule.module_id}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="card p-5 space-y-4 sticky top-0"
              >
                <div>
                  <p className="text-xs font-mono text-slate-400 uppercase tracking-wide">Module</p>
                  <h3 className="font-display text-xl text-slate-800 mt-0.5">
                    {selectedModule.skill_name}
                  </h3>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className={`badge ${difficultyColors[selectedModule.difficulty_level].bg} ${difficultyColors[selectedModule.difficulty_level].text} text-xs`}>
                      {selectedModule.difficulty_level}
                    </span>
                    <span className="text-xs text-slate-400">{selectedModule.estimated_hours}h</span>
                  </div>
                </div>

                <div className="bg-sage-50 rounded-lg p-3">
                  <p className="text-[10px] font-mono text-sage-500 uppercase mb-1">Why Selected</p>
                  <p className="text-xs text-slate-700 leading-relaxed">{selectedModule.why_selected}</p>
                </div>

                {selectedModule.dependency_chain.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wide mb-2">
                      Dependency Chain
                    </p>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {selectedModule.dependency_chain.map((dep, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <code className="text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                            {dep}
                          </code>
                          <ChevronRight size={10} className="text-slate-300" />
                        </span>
                      ))}
                      <code className="text-[10px] bg-slate-800 text-white px-2 py-0.5 rounded">
                        {selectedModule.skill_name}
                      </code>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-50 rounded-lg p-3 text-center">
                    <p className="text-[10px] text-slate-400">Importance</p>
                    <p className="text-base font-bold text-slate-700">
                      {Math.round(selectedModule.importance_score * 100)}%
                    </p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3 text-center">
                    <p className="text-[10px] text-slate-400">Confidence</p>
                    <p className="text-base font-bold text-slate-700">
                      {Math.round(selectedModule.confidence_score * 100)}%
                    </p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center h-48 border-2 border-dashed border-slate-200 rounded-xl"
              >
                <p className="text-sm text-slate-400">Select a module to inspect its reasoning</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
