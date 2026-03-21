import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import {
  Upload, FileText, Brain, ChevronRight, X,
  CheckCircle, AlertCircle, Loader2, ArrowLeft
} from 'lucide-react'
import { runAnalysis } from '@/utils/api'
import { useStore } from '@/store/useStore'

const PIPELINE_STAGES = [
  { pct: 10, label: 'Parsing resume document...', engine: 'Parsing Engine' },
  { pct: 25, label: 'Extracting skills with Llama-3.3-70B...', engine: 'LLM Extraction' },
  { pct: 45, label: 'Analyzing job description...', engine: 'Parsing Engine' },
  { pct: 60, label: 'Computing skill gaps...', engine: 'Gap Engine' },
  { pct: 75, label: 'Traversing skill knowledge graph...', engine: 'Graph Engine' },
  { pct: 88, label: 'Generating adaptive learning path...', engine: 'Path Engine' },
  { pct: 95, label: 'Enriching with course recommendations...', engine: 'RAG Engine' },
  { pct: 100, label: 'Finalizing explainability traces...', engine: 'Explainability Engine' },
]

export default function AnalyzePage() {
  const navigate = useNavigate()
  const { setResult, setSessionId, setProgress } = useStore()

  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jdText, setJdText] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [maxModules, setMaxModules] = useState(20)
  const [timeWeeks, setTimeWeeks] = useState<number | ''>('')
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setLocalProgress] = useState(0)
  const [progressLabel, setProgressLabel] = useState('')
  const [currentEngine, setCurrentEngine] = useState('')

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setResumeFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    onDropRejected: (files) => {
      toast.error(files[0]?.errors[0]?.message || 'File rejected')
    },
  })

  const handleSubmit = async () => {
    if (!resumeFile) return toast.error('Please upload a resume')
    if (jdText.trim().length < 50) return toast.error('Job description is too short (min 50 characters)')

    setIsLoading(true)
    setLocalProgress(0)

    // Staged progress updates
    let stageIdx = 0
    const interval = setInterval(() => {
      if (stageIdx < PIPELINE_STAGES.length) {
        const s = PIPELINE_STAGES[stageIdx]
        setLocalProgress(s.pct)
        setProgressLabel(s.label)
        setCurrentEngine(s.engine)
        setProgress(s.pct, s.label)
        stageIdx++
      }
    }, 1600)

    try {
      const result = await runAnalysis(
        resumeFile,
        jdText,
        targetRole || undefined,
        maxModules,
        timeWeeks ? Number(timeWeeks) : undefined,
      )
      clearInterval(interval)
      setLocalProgress(100)
      setProgressLabel('Analysis complete!')
      setResult(result)
      setSessionId(result.session_id)
      toast.success('Analysis complete!')
      setTimeout(() => navigate('/dashboard'), 600)
    } catch (err: any) {
      clearInterval(interval)
      setIsLoading(false)
      setLocalProgress(0)
      toast.error(err.message || 'Analysis failed. Please try again.')
    }
  }

  const canSubmit = resumeFile && jdText.trim().length >= 50 && !isLoading

  return (
    <div className="min-h-screen bg-cream">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-cream/80 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-slate-400 hover:text-slate-700 transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            Back
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-slate-800 flex items-center justify-center">
              <Brain size={12} className="text-white" />
            </div>
            <span className="font-display text-lg text-slate-800">ASIOE</span>
          </div>
        </div>
      </nav>

      <div className="pt-24 pb-16 px-6 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-10"
        >
          <h1 className="font-display text-4xl text-slate-900 mb-2">
            New Analysis
          </h1>
          <p className="text-slate-400">
            Upload a resume and paste a job description to generate a personalized adaptive learning path.
          </p>
        </motion.div>

        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="card p-10 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-sage-50 flex items-center justify-center mx-auto mb-6">
                <Loader2 size={28} className="text-sage-600 animate-spin" />
              </div>
              <h2 className="font-display text-2xl text-slate-800 mb-2">
                Running Analysis Pipeline
              </h2>
              <p className="text-slate-400 text-sm mb-8 font-mono">{currentEngine}</p>

              {/* Progress bar */}
              <div className="max-w-md mx-auto mb-4">
                <div className="progress-bar mb-2">
                  <motion.div
                    className="progress-fill bg-sage-400"
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400 font-mono">
                  <span>{progressLabel}</span>
                  <span>{progress}%</span>
                </div>
              </div>

              {/* Stage list */}
              <div className="max-w-sm mx-auto mt-8 space-y-2 text-left">
                {PIPELINE_STAGES.map((stage, i) => {
                  const done = progress >= stage.pct
                  const active = progress < stage.pct &&
                    progress >= (PIPELINE_STAGES[i - 1]?.pct ?? 0)
                  return (
                    <div
                      key={stage.engine}
                      className={`flex items-center gap-3 text-xs transition-all duration-300 ${
                        done ? 'text-slate-600' : active ? 'text-sage-600 font-medium' : 'text-slate-300'
                      }`}
                    >
                      {done ? (
                        <CheckCircle size={13} className="text-sage-500 flex-shrink-0" />
                      ) : active ? (
                        <Loader2 size={13} className="animate-spin flex-shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-current flex-shrink-0" />
                      )}
                      {stage.engine}
                    </div>
                  )
                })}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="grid lg:grid-cols-2 gap-6"
            >
              {/* Left Column */}
              <div className="space-y-6">
                {/* Resume Upload */}
                <div className="card p-6">
                  <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
                    <FileText size={16} className="text-sky-500" />
                    Resume Upload
                    <span className="text-rose-500 text-sm">*</span>
                  </h2>
                  <p className="text-xs text-slate-400 mb-4">PDF, DOCX, or TXT · max 10MB</p>

                  <div
                    {...getRootProps()}
                    className={`
                      border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
                      transition-all duration-200
                      ${isDragActive
                        ? 'border-sage-400 bg-sage-50'
                        : resumeFile
                          ? 'border-sage-300 bg-sage-50'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }
                    `}
                  >
                    <input {...getInputProps()} />
                    {resumeFile ? (
                      <div className="flex items-center justify-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-sage-100 flex items-center justify-center">
                          <CheckCircle size={18} className="text-sage-600" />
                        </div>
                        <div className="text-left">
                          <p className="text-sm font-medium text-slate-700">{resumeFile.name}</p>
                          <p className="text-xs text-slate-400">
                            {(resumeFile.size / 1024).toFixed(0)} KB
                          </p>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); setResumeFile(null) }}
                          className="ml-auto p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                        >
                          <X size={14} className="text-slate-400" />
                        </button>
                      </div>
                    ) : (
                      <div>
                        <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
                          <Upload size={20} className="text-slate-400" />
                        </div>
                        <p className="text-sm text-slate-600 font-medium">
                          {isDragActive ? 'Drop to upload' : 'Drag & drop or click to browse'}
                        </p>
                        <p className="text-xs text-slate-400 mt-1">PDF, DOCX, TXT supported</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Options */}
                <div className="card p-6 space-y-4">
                  <h2 className="font-semibold text-slate-800 flex items-center gap-2">
                    Configuration
                  </h2>

                  <div>
                    <label className="text-xs font-medium text-slate-500 mb-1.5 block uppercase tracking-wide">
                      Target Role (optional)
                    </label>
                    <input
                      type="text"
                      value={targetRole}
                      onChange={e => setTargetRole(e.target.value)}
                      placeholder="e.g. Senior Data Scientist"
                      className="input-field"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1.5 block uppercase tracking-wide">
                        Max Modules
                      </label>
                      <select
                        value={maxModules}
                        onChange={e => setMaxModules(Number(e.target.value))}
                        className="input-field"
                      >
                        {[10, 15, 20, 25, 30].map(n => (
                          <option key={n} value={n}>{n} modules</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1.5 block uppercase tracking-wide">
                        Time Budget
                      </label>
                      <input
                        type="number"
                        value={timeWeeks}
                        onChange={e => setTimeWeeks(e.target.value ? Number(e.target.value) : '')}
                        placeholder="Weeks (opt.)"
                        min={1}
                        max={104}
                        className="input-field"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column — JD */}
              <div className="card p-6 flex flex-col">
                <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
                  <Brain size={16} className="text-sage-600" />
                  Job Description
                  <span className="text-rose-500 text-sm">*</span>
                </h2>
                <p className="text-xs text-slate-400 mb-4">Paste the full JD text (min 50 characters)</p>
                <textarea
                  value={jdText}
                  onChange={e => setJdText(e.target.value)}
                  placeholder="Paste the full job description here...

Example:
Senior Data Scientist — Financial Analytics
We are looking for an experienced Data Scientist to join our risk analytics team.

Required Skills:
- Python (Advanced) — 4+ years
- Machine Learning — 3+ years
- SQL (Advanced) — 3+ years
..."
                  className="input-field flex-1 resize-none min-h-[320px] font-mono text-xs leading-relaxed"
                />
                <div className="flex items-center justify-between mt-3">
                  <span className={`text-xs ${jdText.length < 50 ? 'text-rose-400' : 'text-sage-500'}`}>
                    {jdText.length} characters {jdText.length < 50 ? `(need ${50 - jdText.length} more)` : '✓'}
                  </span>
                  {jdText.length > 0 && (
                    <button
                      onClick={() => setJdText('')}
                      className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Submit — full width */}
              <div className="lg:col-span-2">
                <button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className={`
                    w-full py-4 rounded-xl font-semibold text-base flex items-center justify-center gap-3
                    transition-all duration-200
                    ${canSubmit
                      ? 'bg-slate-800 text-white hover:bg-slate-900 hover:shadow-lg active:scale-99'
                      : 'bg-slate-100 text-slate-300 cursor-not-allowed'
                    }
                  `}
                >
                  {!resumeFile && <AlertCircle size={18} />}
                  {canSubmit && <Brain size={18} />}
                  Run Adaptive Analysis
                  {canSubmit && <ChevronRight size={18} />}
                </button>
                {!canSubmit && (
                  <p className="text-center text-xs text-slate-400 mt-2">
                    {!resumeFile ? 'Upload a resume to continue' : 'Add more job description text'}
                  </p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
