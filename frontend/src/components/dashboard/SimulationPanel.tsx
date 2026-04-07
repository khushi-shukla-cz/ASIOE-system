import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Play, Sliders, Clock, Layers, Zap, Target, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import type { LearningPathResult } from '@/types'
import { runSimulation } from '@/utils/api'
import { useStore } from '@/store/useStore'
import LearningPathView from '@/components/dashboard/LearningPathView'

const DOMAINS = [
  'technical', 'analytical', 'leadership',
  'communication', 'domain_specific', 'operational',
]

interface Props {
  sessionId: string
  originalPath: LearningPathResult
}

export default function SimulationPanel({ sessionId, originalPath }: Props) {
  const {
    simulationResult,
    setSimulationResult,
    clearSimulationResult,
    setSimulating,
    isSimulating,
  } = useStore()
  const [weeks, setWeeks] = useState(originalPath.total_weeks)
  const [maxModules, setMaxModules] = useState(originalPath.total_modules)
  const [priorityDomains, setPriorityDomains] = useState<string[]>([])

  const displayPath = simulationResult || originalPath

  const toggleDomain = (domain: string) => {
    setPriorityDomains(prev =>
      prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]
    )
  }

  const handleSimulate = async () => {
    setSimulating(true)
    try {
      const result = await runSimulation({
        sessionId,
        timeConstraintWeeks: Math.round(weeks),
        maxModules: Math.max(5, Math.round(maxModules)),
        priorityDomains,
      })
      setSimulationResult(result.learning_path)
      toast.success(`Recomputed: ${result.learning_path?.total_modules} modules in ${result.learning_path?.total_weeks?.toFixed(1)}w`)
    } catch (err: any) {
      toast.error(err.message || 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  const handleReset = () => {
    clearSimulationResult()
    setWeeks(originalPath.total_weeks)
    setMaxModules(originalPath.total_modules)
    setPriorityDomains([])
    toast.success('Reverted to original learning path')
  }

  const delta = simulationResult
    ? {
        modules: simulationResult.total_modules - originalPath.total_modules,
        hours: simulationResult.total_hours - originalPath.total_hours,
      }
    : null

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-5">
          <Sliders size={16} className="text-amber-600" />
          <h3 className="font-semibold text-slate-800">Simulation Controls</h3>
          <span className="badge badge-minor ml-1">Live Recompute</span>
        </div>

        {/* Time slider */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">
              Time Budget
            </label>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
              <Clock size={14} className="text-amber-500" />
              {Math.round(weeks)} weeks · {(Math.round(weeks) * 10).toFixed(0)}h
            </div>
          </div>
          <input
            type="range"
            min={4}
            max={52}
            step={1}
            value={weeks}
            onChange={e => setWeeks(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none bg-slate-200 accent-amber-500 cursor-pointer"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>4 weeks</span>
            <span>26 weeks</span>
            <span>52 weeks</span>
          </div>
        </div>

        {/* Priority domains */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-slate-600 uppercase tracking-wide block">
              Max Modules
            </label>
            <span className="text-sm font-semibold text-slate-800">
              {Math.round(maxModules)}
            </span>
          </div>
          <input
            type="range"
            min={5}
            max={50}
            step={1}
            value={maxModules}
            onChange={e => setMaxModules(Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none bg-slate-200 accent-slate-700 cursor-pointer"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1 mb-5">
            <span>5 modules</span>
            <span>25 modules</span>
            <span>50 modules</span>
          </div>

          <label className="text-xs font-medium text-slate-600 uppercase tracking-wide mb-2 block">
            Priority Domains (optional)
          </label>
          <div className="flex flex-wrap gap-2">
            {DOMAINS.map(domain => (
              <button
                key={domain}
                onClick={() => toggleDomain(domain)}
                className={`
                  px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150
                  ${priorityDomains.includes(domain)
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                  }
                `}
              >
                {domain.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Run */}
        <button
          onClick={handleSimulate}
          disabled={isSimulating}
          className="btn-accent w-full justify-center py-3"
        >
          {isSimulating ? (
            <><Loader2 size={16} className="animate-spin" /> Recomputing path...</>
          ) : (
            <><Play size={16} /> Run Simulation</>
          )}
        </button>

        {simulationResult && (
          <button
            onClick={handleReset}
            className="btn-ghost w-full justify-center py-3 mt-2"
          >
            <RotateCcw size={16} /> Reset To Original
          </button>
        )}
      </div>

      {/* Delta comparison */}
      <AnimatePresence>
        {delta && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-4 gap-3"
          >
            {[
              {
                icon: Layers, label: 'Modules',
                orig: originalPath.total_modules,
                sim: simulationResult!.total_modules,
                delta: delta.modules,
                unit: '',
              },
              {
                icon: Clock, label: 'Hours',
                orig: originalPath.total_hours.toFixed(0),
                sim: simulationResult!.total_hours.toFixed(0),
                delta: delta.hours.toFixed(0),
                unit: 'h',
              },
              {
                icon: Target, label: 'Weeks',
                orig: originalPath.total_weeks.toFixed(1),
                sim: simulationResult!.total_weeks.toFixed(1),
                delta: (simulationResult!.total_weeks - originalPath.total_weeks).toFixed(1),
                unit: 'w',
              },
              {
                icon: Zap, label: 'Efficiency',
                orig: `${Math.round(originalPath.efficiency_score * 100)}%`,
                sim: `${Math.round(simulationResult!.efficiency_score * 100)}%`,
                delta: Math.round((simulationResult!.efficiency_score - originalPath.efficiency_score) * 100),
                unit: '%',
              },
            ].map(({ icon: Icon, label, orig, sim, delta: d, unit }) => {
              const negative = Number(d) < 0
              return (
                <div key={label} className="card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon size={13} className="text-slate-400" />
                    <span className="text-xs text-slate-400">{label}</span>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-[10px] text-slate-400">Was: {orig}{unit}</p>
                      <p className="font-bold text-slate-800 text-lg">{sim}{unit}</p>
                    </div>
                    <span className={`text-xs font-semibold ${negative ? 'text-sage-600' : 'text-rose-500'}`}>
                      {Number(d) > 0 ? '+' : ''}{d}{unit}
                    </span>
                  </div>
                </div>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Path preview */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <h3 className="font-semibold text-slate-700 text-sm">
            {simulationResult ? 'Simulated Path' : 'Original Path'}
          </h3>
          {simulationResult && (
            <span className="badge badge-minor">Recomputed</span>
          )}
        </div>
        <LearningPathView path={displayPath} />
      </div>
    </div>
  )
}
