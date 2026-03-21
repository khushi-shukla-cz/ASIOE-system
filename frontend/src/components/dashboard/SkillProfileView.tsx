import { motion } from 'framer-motion'
import { User, Briefcase, GraduationCap, Star, Shield } from 'lucide-react'
import type { SkillProfile, ExtractedSkill } from '@/types'
import { domainColors, difficultyColors, formatPercent } from '@/utils/helpers'

interface Props { profile: SkillProfile }

function SkillBadge({ skill }: { skill: ExtractedSkill }) {
  const dc = domainColors[skill.domain] ?? domainColors.technical
  const lvl = difficultyColors[skill.proficiency_level] ?? difficultyColors.intermediate
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white border border-slate-100 rounded-xl p-3 shadow-sm hover:shadow-card transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="font-medium text-sm text-slate-800 leading-tight">{skill.name}</p>
        <span className={`badge ${lvl.bg} ${lvl.text} flex-shrink-0 text-[10px]`}>
          {skill.proficiency_level}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`badge ${dc.bg} ${dc.text} text-[10px]`}>{skill.domain.replace('_', ' ')}</span>
        <div className="flex-1 progress-bar h-1.5">
          <div
            className="progress-fill bg-sage-400"
            style={{ width: `${skill.proficiency_score * 100}%` }}
          />
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          {formatPercent(skill.proficiency_score)}
        </span>
      </div>
    </motion.div>
  )
}

function StatCard({
  icon: Icon, label, value, color
}: {
  icon: any; label: string; value: string; color: string
}) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={16} className="text-current" />
      </div>
      <div>
        <p className="text-xs text-slate-400">{label}</p>
        <p className="font-semibold text-slate-800 text-sm">{value || '—'}</p>
      </div>
    </div>
  )
}

export default function SkillProfileView({ profile }: Props) {
  const grouped = profile.skills.reduce<Record<string, ExtractedSkill[]>>((acc, s) => {
    const d = s.domain
    if (!acc[d]) acc[d] = []
    acc[d].push(s)
    return acc
  }, {})

  const domainOrder = ['technical', 'analytical', 'leadership', 'communication', 'domain_specific', 'operational', 'soft_skills']

  return (
    <div className="space-y-6">
      {/* Candidate overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={User} label="Candidate"
          value={profile.candidate_name || 'Detected'}
          color="bg-sky-50 text-sky-500"
        />
        <StatCard
          icon={Briefcase} label="Current Role"
          value={profile.current_role || 'Not specified'}
          color="bg-sage-50 text-sage-600"
        />
        <StatCard
          icon={Star} label="Experience"
          value={profile.years_of_experience ? `${profile.years_of_experience} yrs` : 'Unknown'}
          color="bg-amber-50 text-amber-600"
        />
        <StatCard
          icon={GraduationCap} label="Education"
          value={profile.education_level?.replace('_', ' ') || 'Not specified'}
          color="bg-rose-50 text-rose-500"
        />
      </div>

      {/* Parse confidence */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-sage-500" />
            <span className="text-sm font-medium text-slate-700">Parsing Confidence</span>
          </div>
          <span className="font-mono text-sm font-semibold text-sage-600">
            {formatPercent(profile.parsing_confidence)}
          </span>
        </div>
        <div className="progress-bar">
          <motion.div
            className="progress-fill bg-sage-400"
            initial={{ width: 0 }}
            animate={{ width: `${profile.parsing_confidence * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        <p className="text-xs text-slate-400 mt-1">
          {profile.skills.length} skills extracted · {profile.certifications?.length || 0} certifications
        </p>
      </div>

      {/* Skills by domain */}
      <div>
        <h3 className="font-semibold text-slate-700 text-sm mb-4 uppercase tracking-wide">
          Extracted Skills by Domain
        </h3>
        <div className="space-y-6">
          {domainOrder.map(domain => {
            const skills = grouped[domain]
            if (!skills?.length) return null
            const dc = domainColors[domain as keyof typeof domainColors] ?? domainColors.technical
            return (
              <div key={domain}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`badge ${dc.bg} ${dc.text} text-xs`}>
                    {domain.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-slate-400">{skills.length} skills</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                  {skills.map(s => <SkillBadge key={s.name} skill={s} />)}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* JD Requirements */}
      {profile.jd_required_skills?.length > 0 && (
        <div>
          <h3 className="font-semibold text-slate-700 text-sm mb-4 uppercase tracking-wide">
            Role Requirements ({profile.target_role})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
            {profile.jd_required_skills.slice(0, 18).map(s => (
              <SkillBadge key={s.name} skill={{ ...s, source: 'jd_required' }} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
