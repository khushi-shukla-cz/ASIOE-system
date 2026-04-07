// ── Core Types ─────────────────────────────────────────────────────────────────

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type SkillDomain = 'technical' | 'analytical' | 'leadership' | 'communication' | 'domain_specific' | 'operational' | 'soft_skills'
export type GapSeverity = 'critical' | 'major' | 'minor' | 'none'
export type SessionStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ExtractedSkill {
  skill_id: string
  name: string
  canonical_name?: string
  domain: SkillDomain
  proficiency_level: DifficultyLevel
  proficiency_score: number
  years_used?: number
  confidence: number
  source: string
  context_snippet?: string
}

export interface SkillGap {
  skill_id: string
  skill_name: string
  domain: SkillDomain
  severity: GapSeverity
  current_score: number
  required_score: number
  gap_delta: number
  reasoning: string
}

export interface DomainCoverage {
  domain: SkillDomain
  coverage_percentage: number
  matched_skills: number
  total_required: number
  radar_value: number
}

export interface GapAnalysisResult {
  session_id: string
  overall_readiness_score: number
  readiness_label: string
  critical_gaps: SkillGap[]
  major_gaps: SkillGap[]
  minor_gaps: SkillGap[]
  strength_areas: ExtractedSkill[]
  domain_coverage: DomainCoverage[]
  reasoning_trace: string
  analysis_timestamp: string
}

export interface LearningModule {
  module_id: string
  skill_id: string
  skill_name: string
  title: string
  description: string
  domain: SkillDomain
  difficulty_level: DifficultyLevel
  estimated_hours: number
  sequence_order: number
  phase_number: number
  course_id?: string
  course_title?: string
  course_url?: string
  course_provider?: string
  prerequisite_module_ids: string[]
  unlocks_module_ids: string[]
  why_selected: string
  dependency_chain: string[]
  importance_score: number
  confidence_score: number
}

export interface PathPhase {
  phase_number: number
  phase_name: string
  description: string
  modules: LearningModule[]
  estimated_hours: number
  estimated_weeks: number
  focus_domains: string[]
}

export interface PathGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphNode {
  id: string
  skill_id: string
  label: string
  domain: SkillDomain
  difficulty: DifficultyLevel
  hours: number
  phase: number
  importance: number
  confidence: number
  gap_severity?: GapSeverity
}

export interface GraphEdge {
  source: string
  target: string
  type: string
}

export interface LearningPathResult {
  session_id: string
  path_id: string
  target_role: string
  phases: PathPhase[]
  total_modules: number
  total_hours: number
  total_weeks: number
  path_graph: PathGraph
  efficiency_score: number
  redundancy_eliminated: number
  path_algorithm: string
  path_version: number
  reasoning_trace: string
  generated_at: string
}

export interface SystemReasoningTrace {
  session_id: string
  parsing_trace: string
  normalization_trace: string
  gap_trace: string
  path_trace: string
  total_tokens_used: number
  model_used: string
  generated_at: string
}

export interface SkillProfile {
  candidate_name?: string
  current_role?: string
  years_of_experience?: number
  education_level?: string
  skills: ExtractedSkill[]
  certifications?: string[]
  parsing_confidence: number
  target_role?: string
  jd_required_skills: ExtractedSkill[]
}

export interface AnalysisResult {
  session_id: string
  status: SessionStatus
  skill_profile?: SkillProfile
  gap_analysis?: GapAnalysisResult
  learning_path?: LearningPathResult
  reasoning_trace?: SystemReasoningTrace
  processing_time_ms: number
}

export interface SimulationRequest {
  session_id: string
  time_constraint_weeks: number
  max_modules?: number
  priority_domains: string[]
  exclude_module_ids: string[]
}

export interface SimulationDelta {
  original_modules: number
  simulated_modules: number
  module_delta: number
  original_hours: number
  simulated_hours: number
  hour_delta: number
}

export interface SimulationResponse {
  session_id: string
  simulation_key: string
  simulation_applied: boolean
  time_constraint_weeks: number
  max_modules: number
  priority_domains: string[]
  learning_path: LearningPathResult
  delta: SimulationDelta
}
