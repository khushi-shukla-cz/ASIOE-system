import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Clock, BookOpen, ChevronDown, ChevronRight,
  ExternalLink, Layers, Zap, Target, Award
} from 'lucide-react'
import type { LearningPathResult, LearningModule, PathPhase } from '@/types'
import { domainColors, difficultyColors, formatHours } from '@/utils/helpers'
import { useStore } from '@/store/useStore'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorState from '@/components/common/ErrorState'

interface Props { path?: LearningPathResult }

function ModuleCard({ module, index }: { module: LearningModule; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const { setSelectedModule } = useStore()
  const dc = domainColors[module.domain as keyof typeof domainColors] ?? domainColors.technical
  const lc = difficultyColors[module.difficulty_level as keyof typeof difficultyColors] ?? difficultyColors.intermediate

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.04 }}
      className="bg-white border border-slate-100 rounded-xl overflow-hidden shadow-sm hover:shadow-card transition-shadow"
    >
      {/* Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={() => { setExpanded(!expanded); setSelectedModule(module.module_id) }}
      >
        <div className="flex items-start gap-3">
          {/* Sequence number */}
          <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-xs font-bold text-slate-500">{module.sequence_order}</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold text-slate-800 text-sm leading-tight">{module.skill_name}</p>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <span className={`badge ${lc.bg} ${lc.text} text-[10px]`}>
                  {module.difficulty_level}
                </span>
                {expanded
                  ? <ChevronDown size={14} className="text-slate-400" />
                  : <ChevronRight size={14} className="text-slate-400" />
                }
              </div>
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className={`badge ${dc.bg} ${dc.text} text-[10px]`}>
                {module.domain.replace('_', ' ')}
              </span>
              <span className="flex items-center gap-1 text-[11px] text-slate-400">
                <Clock size={10} />
                {formatHours(module.estimated_hours)}
              </span>
              <span className="text-[11px] text-slate-300">·</span>
              <span className="text-[11px] text-slate-400 font-mono">
                conf {Math.round(module.confidence_score * 100)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-0 border-t border-slate-50 space-y-3">
              {/* Why selected */}
              <div className="bg-sage-50 rounded-lg p-3">
                <p className="text-[10px] font-mono text-sage-500 uppercase tracking-wide mb-1">
                  Why Selected
                </p>
                <p className="text-xs text-slate-600 leading-relaxed">{module.why_selected}</p>
              </div>

              {/* Dependency chain */}
              {module.dependency_chain.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wide mb-1.5">
                    Dependency Chain
                  </p>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {module.dependency_chain.map((dep, i) => (
                      <span key={i} className="flex items-center gap-1">
                        <span className="text-xs bg-slate-100 px-2 py-0.5 rounded-md text-slate-600">
                          {dep}
                        </span>
                        {i < module.dependency_chain.length - 1 && (
                          <ChevronRight size={11} className="text-slate-300" />
                        )}
                      </span>
                    ))}
                    <ChevronRight size={11} className="text-slate-300" />
                    <span className="text-xs bg-slate-800 text-white px-2 py-0.5 rounded-md">
                      {module.skill_name}
                    </span>
                  </div>
                </div>
              )}

              {/* Scores */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                  <p className="text-[10px] text-slate-400 mb-0.5">Importance</p>
                  <p className="text-sm font-bold text-slate-700">
                    {Math.round(module.importance_score * 100)}%
                  </p>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                  <p className="text-[10px] text-slate-400 mb-0.5">Confidence</p>
                  <p className="text-sm font-bold text-slate-700">
                    {Math.round(module.confidence_score * 100)}%
                  </p>
                </div>
              </div>

              {/* Course link */}
              {module.course_title && (
                <a
                  href={module.course_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 p-3 bg-sky-50 rounded-lg hover:bg-sky-100 transition-colors group"
                >
                  <BookOpen size={14} className="text-sky-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">
                      {module.course_title}
                    </p>
                    <p className="text-[10px] text-slate-400">{module.course_provider}</p>
                  </div>
                  <ExternalLink
                    size={12}
                    className="text-sky-400 flex-shrink-0 group-hover:text-sky-600 transition-colors"
                  />
                </a>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function PhaseBlock({ phase, globalIndex }: { phase: PathPhase; globalIndex: number }) {
  const [collapsed, setCollapsed] = useState(false)
  const phaseColors = [
    { bg: 'bg-sky-50', border: 'border-sky-200', badge: 'bg-sky-100 text-sky-700', num: 'bg-sky-500' },
    { bg: 'bg-sage-50', border: 'border-sage-200', badge: 'bg-sage-100 text-sage-700', num: 'bg-sage-500' },
    { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-100 text-amber-700', num: 'bg-amber-500' },
  ]
  const pc = phaseColors[(phase.phase_number - 1) % phaseColors.length]

  return (
    <div className={`border ${pc.border} rounded-2xl overflow-hidden`}>
      {/* Phase header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={`w-full ${pc.bg} px-6 py-4 flex items-center gap-4 text-left`}
      >
        <div className={`w-8 h-8 rounded-xl ${pc.num} flex items-center justify-center flex-shrink-0`}>
          <span className="text-white text-sm font-bold">{phase.phase_number}</span>
        </div>
        <div className="flex-1">
          <p className="font-semibold text-slate-800">{phase.phase_name}</p>
          <p className="text-xs text-slate-500 mt-0.5">{phase.description}</p>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-500 flex-shrink-0">
          <span className="flex items-center gap-1.5">
            <Layers size={13} />
            {phase.modules.length} modules
          </span>
          <span className="flex items-center gap-1.5">
            <Clock size={13} />
            {phase.estimated_hours.toFixed(0)}h
          </span>
          <span className="flex items-center gap-1.5">
            <Target size={13} />
            {phase.estimated_weeks.toFixed(1)}w
          </span>
          {collapsed
            ? <ChevronRight size={16} className="text-slate-400" />
            : <ChevronDown size={16} className="text-slate-400" />
          }
        </div>
      </button>

      {/* Modules */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-2 bg-white">
              {phase.modules.map((mod, i) => (
                <ModuleCard key={mod.module_id} module={mod} index={globalIndex + i} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function LearningPathView({ path }: Props) {
  if (!path) return <LoadingSkeleton />

  let globalIndex = 0

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: Layers, label: 'Total Modules', value: `${path.total_modules}`, color: 'bg-sky-50 text-sky-500' },
          { icon: Clock, label: 'Total Hours', value: `${path.total_hours.toFixed(0)}h`, color: 'bg-sage-50 text-sage-600' },
          { icon: Target, label: 'Estimated Weeks', value: `${path.total_weeks.toFixed(1)}w`, color: 'bg-amber-50 text-amber-600' },
          { icon: Zap, label: 'Efficiency', value: `${Math.round(path.efficiency_score * 100)}%`, color: 'bg-rose-50 text-rose-500' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="card p-4 flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
              <Icon size={16} className="text-current" />
            </div>
            <div>
              <p className="text-xs text-slate-400">{label}</p>
              <p className="font-bold text-slate-800">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Redundancy callout */}
      {path.redundancy_eliminated > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 bg-sage-50 border border-sage-200 rounded-xl"
        >
          <Award size={16} className="text-sage-600 flex-shrink-0" />
          <p className="text-sm text-slate-700">
            <span className="font-semibold text-sage-700">
              {path.redundancy_eliminated} modules eliminated
            </span>
            {' '}based on your existing competencies — saving you time on content you already know.
          </p>
        </motion.div>
      )}

      {/* Path reasoning */}
      <div className="card p-4 border-l-4 border-l-sky-300">
        <p className="text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-1">
          Path Algorithm · {path.path_algorithm}
        </p>
        <p className="text-sm text-slate-600 leading-relaxed">{path.reasoning_trace}</p>
      </div>

      {/* Phases */}
      <div className="space-y-4">
        {path.phases.map(phase => {
          const block = (
            <PhaseBlock key={phase.phase_number} phase={phase} globalIndex={globalIndex} />
          )
          globalIndex += phase.modules.length
          return block
        })}
      </div>
    </div>
  )
}
