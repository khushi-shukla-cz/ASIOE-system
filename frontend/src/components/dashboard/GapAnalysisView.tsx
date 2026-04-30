import { motion } from 'framer-motion'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, Legend
} from 'recharts'
import { AlertTriangle, TrendingUp, Minus, CheckCircle2, Quote } from 'lucide-react'
import type { GapAnalysisResult, SkillGap } from '@/types'
import { severityColors, readinessColor, formatPercent } from '@/utils/helpers'
import LoadingSkeleton from '@/components/common/LoadingSkeleton'
import ErrorState from '@/components/common/ErrorState'

interface Props { gap?: GapAnalysisResult }

function ReadinessMeter({ score, label }: { score: number; label: string }) {
  const color = readinessColor(score)
  const pct = Math.round(score * 100)
  const circumference = 2 * Math.PI * 54
  const dash = (pct / 100) * circumference

  return (
    <div className="card p-8 flex flex-col items-center text-center">
      <p className="text-xs text-slate-400 uppercase tracking-widest mb-4 font-mono">
        Overall Readiness
      </p>
      <div className="relative w-36 h-36">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r="54" fill="none" stroke="#EFF1F5" strokeWidth="10" />
          <motion.circle
            cx="60" cy="60" r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - dash }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-3xl font-display"
            style={{ color }}
          >
            {pct}%
          </motion.span>
        </div>
      </div>
      <p className="font-semibold text-slate-700 mt-3">{label}</p>
    </div>
  )
}

function GapCard({ gap, index }: { gap: SkillGap; index: number }) {
  const sc = severityColors[gap.severity as keyof typeof severityColors]
  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
      className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="font-semibold text-slate-800 text-sm">{gap.skill_name}</p>
          <p className="text-xs text-slate-400 capitalize">{gap.domain.replace('_', ' ')}</p>
        </div>
        <span className={`badge ${sc.bg} ${sc.text} flex-shrink-0 capitalize`}>
          <span className={`w-1.5 h-1.5 rounded-full ${sc.dot} mr-1`} />
          {gap.severity}
        </span>
      </div>

      {/* Score bars */}
      <div className="space-y-1.5 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 w-16 flex-shrink-0">Current</span>
          <div className="flex-1 progress-bar">
            <motion.div
              className="progress-fill bg-slate-300"
              initial={{ width: 0 }}
              animate={{ width: `${gap.current_score * 100}%` }}
              transition={{ duration: 0.7, delay: index * 0.05 }}
            />
          </div>
          <span className="text-xs font-mono text-slate-500 w-10 text-right">
            {formatPercent(gap.current_score)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 w-16 flex-shrink-0">Required</span>
          <div className="flex-1 progress-bar">
            <motion.div
              className="progress-fill bg-rose-300"
              initial={{ width: 0 }}
              animate={{ width: `${gap.required_score * 100}%` }}
              transition={{ duration: 0.7, delay: index * 0.05 + 0.1 }}
            />
          </div>
          <span className="text-xs font-mono text-slate-500 w-10 text-right">
            {formatPercent(gap.required_score)}
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-400 leading-relaxed italic">{gap.reasoning}</p>
    </motion.div>
  )
}

export default function GapAnalysisView({ gap }: Props) {
  if (!gap) return <LoadingSkeleton />
  if (!Array.isArray(gap.domain_coverage)) {
    return (
      <ErrorState
        type="error"
        title="Gap analysis unavailable"
        message="The gap analysis response is incomplete. Please rerun analysis."
      />
    )
  }

  const radarData = gap.domain_coverage.map(d => ({
    domain: d.domain.replace('_', ' '),
    Candidate: Math.round(d.radar_value * 100),
    Required: 100,
  }))

  const totalGaps = gap.critical_gaps.length + gap.major_gaps.length + gap.minor_gaps.length

  return (
    <div className="space-y-6">
      {/* Top metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ReadinessMeter score={gap.overall_readiness_score} label={gap.readiness_label} />

        <div className="card p-5 col-span-1">
          <div className="space-y-3">
            {[
              { label: 'Critical Gaps', count: gap.critical_gaps.length, color: 'text-rose-500', bg: 'bg-rose-50', icon: AlertTriangle },
              { label: 'Major Gaps', count: gap.major_gaps.length, color: 'text-amber-600', bg: 'bg-amber-50', icon: TrendingUp },
              { label: 'Minor Gaps', count: gap.minor_gaps.length, color: 'text-sky-600', bg: 'bg-sky-50', icon: Minus },
              { label: 'Strengths', count: gap.strength_areas.length, color: 'text-sage-600', bg: 'bg-sage-50', icon: CheckCircle2 },
            ].map(({ label, count, color, bg, icon: Icon }) => (
              <div key={label} className={`flex items-center gap-3 p-2.5 rounded-lg ${bg}`}>
                <Icon size={14} className={color} />
                <span className="text-xs text-slate-600 flex-1">{label}</span>
                <span className={`text-sm font-bold ${color}`}>{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Radar chart */}
        <div className="card p-4 col-span-2">
          <p className="text-xs text-slate-400 uppercase tracking-wide mb-2 font-mono">
            Domain Coverage Radar
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#EFF1F5" />
              <PolarAngleAxis
                dataKey="domain"
                tick={{ fontSize: 10, fontFamily: 'DM Sans', fill: '#8892A8' }}
              />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Required"
                dataKey="Required"
                stroke="#D8DCE8"
                fill="#D8DCE8"
                fillOpacity={0.2}
                strokeDasharray="4 2"
              />
              <Radar
                name="Candidate"
                dataKey="Candidate"
                stroke="#4A8A4A"
                fill="#4A8A4A"
                fillOpacity={0.3}
              />
              <Tooltip
                contentStyle={{
                  fontFamily: 'DM Sans',
                  fontSize: 11,
                  borderRadius: 8,
                  border: '1px solid #E8ECF0',
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Reasoning trace */}
      <div className="card p-5 border-l-4 border-l-sage-300">
        <div className="flex items-start gap-3">
          <Quote size={16} className="text-sage-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wide">
              AI Reasoning Trace
            </p>
            <p className="text-sm text-slate-600 leading-relaxed">{gap.reasoning_trace}</p>
          </div>
        </div>
      </div>

      {/* Gaps by severity */}
      {gap.critical_gaps.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={15} className="text-rose-500" />
            <h3 className="font-semibold text-slate-700 text-sm">
              Critical Gaps <span className="text-rose-500">({gap.critical_gaps.length})</span>
            </h3>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {gap.critical_gaps.map((g, i) => <GapCard key={g.skill_id} gap={g} index={i} />)}
          </div>
        </section>
      )}

      {gap.major_gaps.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} className="text-amber-600" />
            <h3 className="font-semibold text-slate-700 text-sm">
              Major Gaps <span className="text-amber-600">({gap.major_gaps.length})</span>
            </h3>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {gap.major_gaps.map((g, i) => <GapCard key={g.skill_id} gap={g} index={i} />)}
          </div>
        </section>
      )}

      {gap.strength_areas.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 size={15} className="text-sage-600" />
            <h3 className="font-semibold text-slate-700 text-sm">
              Strength Areas <span className="text-sage-600">({gap.strength_areas.length})</span>
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {gap.strength_areas.map(s => (
              <span key={s.name} className="badge badge-success">
                <CheckCircle2 size={11} />
                {s.name}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
