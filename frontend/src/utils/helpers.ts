import type { DifficultyLevel, GapSeverity, SkillDomain } from '@/types'

export const domainColors: Record<SkillDomain, { bg: string; text: string; border: string }> = {
  technical:      { bg: 'bg-sky-100',    text: 'text-sky-700',   border: 'border-sky-200' },
  analytical:     { bg: 'bg-sage-100',   text: 'text-sage-700',  border: 'border-sage-200' },
  leadership:     { bg: 'bg-amber-100',  text: 'text-amber-700', border: 'border-amber-200' },
  communication:  { bg: 'bg-rose-100',   text: 'text-rose-600',  border: 'border-rose-200' },
  domain_specific:{ bg: 'bg-slate-100',  text: 'text-slate-700', border: 'border-slate-200' },
  operational:    { bg: 'bg-slate-100',  text: 'text-slate-600', border: 'border-slate-200' },
  soft_skills:    { bg: 'bg-sage-50',    text: 'text-sage-600',  border: 'border-sage-100' },
}

export const difficultyColors: Record<DifficultyLevel, { bg: string; text: string }> = {
  beginner:     { bg: 'bg-sage-100',  text: 'text-sage-700' },
  intermediate: { bg: 'bg-sky-100',   text: 'text-sky-700' },
  advanced:     { bg: 'bg-amber-100', text: 'text-amber-700' },
  expert:       { bg: 'bg-rose-100',  text: 'text-rose-600' },
}

export const severityColors: Record<GapSeverity, { bg: string; text: string; dot: string }> = {
  critical: { bg: 'bg-rose-100',  text: 'text-rose-600',  dot: 'bg-rose-500' },
  major:    { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500' },
  minor:    { bg: 'bg-sky-100',   text: 'text-sky-700',   dot: 'bg-sky-500' },
  none:     { bg: 'bg-sage-100',  text: 'text-sage-700',  dot: 'bg-sage-500' },
}

export const domainGraphColors: Record<SkillDomain, string> = {
  technical:       '#38A0F5',
  analytical:      '#4A8A4A',
  leadership:      '#F5A623',
  communication:   '#F87171',
  domain_specific: '#8892A8',
  operational:     '#7AAD7A',
  soft_skills:     '#C8DCC8',
}

export function readinessColor(score: number): string {
  if (score >= 0.85) return '#4A8A4A'
  if (score >= 0.70) return '#7AAD7A'
  if (score >= 0.50) return '#F5A623'
  if (score >= 0.30) return '#F87171'
  return '#DC2626'
}

export function formatHours(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`
  return `${hours.toFixed(0)}h`
}

export function formatPercent(score: number): string {
  return `${Math.round(score * 100)}%`
}

export function clsx(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
