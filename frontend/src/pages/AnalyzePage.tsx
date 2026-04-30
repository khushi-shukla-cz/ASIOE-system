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
import { ErrorState } from '@/components/common/ErrorState'
import { FormField, Input, TextArea, Select } from '@/components/common/FormField'

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
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setResumeFile(accepted[0])
      setError(null)
    }
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
      const err = files[0]?.errors[0]?.message || 'File rejected'
      setError(err)
      toast.error(err)
    },
  })

  const handleSubmit = async () => {
    if (!resumeFile) {
      setError('Please upload a resume')
      return toast.error('Please upload a resume')
    }
    if (jdText.trim().length < 50) {
      setError('Job description is too short (minimum 50 characters)')
      return toast.error('Job description is too short (min 50 characters)')
    }

    setIsLoading(true)
    setError(null)
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
      const errorMessage = err.message || 'Analysis failed. Please try again.'
      setError(errorMessage)
      toast.error(errorMessage)
    }
  }

  const canSubmit = resumeFile && jdText.trim().length >= 50 && !isLoading

  return (
    <div className="min-h-screen bg-cream">
      {/* Skip link */}
      <a href="#main-form" className="skip-link">
        Skip to analysis form
      </a>

      {/* Nav */}
      <nav
        className="fixed top-0 w-full z-50 bg-cream/80 backdrop-blur-md border-b border-slate-100"
        aria-label="Navigation"
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-slate-400 hover:text-slate-700 transition-colors text-sm"
            aria-label="Back to home"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            <span className="hidden sm:inline">Back</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-slate-800 flex items-center justify-center" aria-hidden="true">
              <Brain size={12} className="text-white" />
            </div>
            <span className="font-display text-lg text-slate-800">ASIOE</span>
          </div>
        </div>
      </nav>

      <div className="pt-20 sm:pt-24 pb-12 sm:pb-16 px-4 sm:px-6 max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8 sm:mb-10"
        >
          <h1 className="font-display text-3xl sm:text-4xl text-slate-900 mb-2">New Analysis</h1>
          <p className="text-slate-400 text-sm sm:text-base">
            Upload a resume and paste a job description to generate a personalized adaptive learning path.
          </p>
        </motion.div>

        {/* Global error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6"
            >
              <ErrorState
                type="error"
                title="Error"
                message={error}
                onDismiss={() => setError(null)}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="card p-8 sm:p-10 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-sage-50 flex items-center justify-center mx-auto mb-6" aria-hidden="true">
                <Loader2 size={28} className="text-sage-600 animate-spin" />
              </div>
              <h2 className="font-display text-2xl text-slate-800 mb-2">Running Analysis Pipeline</h2>
              <p className="text-slate-400 text-sm mb-8 font-mono" role="status" aria-live="polite">
                {currentEngine}
              </p>

              {/* Progress bar */}
              <div className="max-w-md mx-auto mb-4">
                <div className="progress-bar mb-2">
                  <motion.div
                    className="progress-fill bg-sage-400"
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    role="progressbar"
                    aria-valuenow={progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400 font-mono">
                  <span>{progressLabel}</span>
                  <span aria-label={`Progress: ${progress} percent`}>{progress}%</span>
                </div>
              </div>

              {/* Stage list */}
              <div className="max-w-sm mx-auto mt-8 space-y-2 text-left">
                {PIPELINE_STAGES.map((stage, i) => {
                  const done = progress >= stage.pct
                  const active = progress < stage.pct && progress >= (PIPELINE_STAGES[i - 1]?.pct ?? 0)
                  return (
                    <div
                      key={`${stage.engine}-${stage.pct}`}
                      className={`flex items-center gap-3 text-xs transition-all duration-300 ${
                        done ? 'text-slate-600' : active ? 'text-sage-600 font-medium' : 'text-slate-300'
                      }`}
                      aria-current={active ? 'step' : undefined}
                    >
                      {done ? (
                        <CheckCircle size={13} className="text-sage-500 flex-shrink-0" aria-hidden="true" />
                      ) : active ? (
                        <Loader2 size={13} className="animate-spin flex-shrink-0" aria-hidden="true" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-current flex-shrink-0" aria-hidden="true" />
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
              id="main-form"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6"
            >
              {/* Left Column */}
              <div className="space-y-6">
                {/* Resume Upload */}
                <div className="card p-4 sm:p-6">
                  <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
                    <FileText size={16} className="text-sky-500" aria-hidden="true" />
                    Resume Upload
                    <span className="text-rose-500 text-sm" aria-label="Required">*</span>
                  </h2>
                  <p className="text-xs text-slate-400 mb-4">PDF, DOCX, or TXT · max 10MB</p>

                  <div
                    {...getRootProps()}
                    className={`
                      border-2 border-dashed rounded-xl p-6 sm:p-8 text-center cursor-pointer
                      transition-all duration-200 focus-within:ring-2 focus-within:ring-sage-200
                      ${
                        isDragActive
                          ? 'border-sage-400 bg-sage-50'
                          : resumeFile
                            ? 'border-sage-300 bg-sage-50'
                            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }
                    `}
                    role="button"
                    tabIndex={0}
                    aria-label="Upload resume, drag and drop or click to browse"
                  >
                    <input {...getInputProps()} />
                    {resumeFile ? (
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 flex-1 text-left">
                          <div className="w-10 h-10 rounded-xl bg-sage-100 flex items-center justify-center flex-shrink-0">
                            <CheckCircle size={18} className="text-sage-600" aria-hidden="true" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-slate-700">{resumeFile.name}</p>
                            <p className="text-xs text-slate-400">
                              {(resumeFile.size / 1024).toFixed(0)} KB
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setResumeFile(null)
                          }}
                          className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                          aria-label="Remove uploaded file"
                        >
                          <X size={14} className="text-slate-400" aria-hidden="true" />
                        </button>
                      </div>
                    ) : (
                      <div>
                        <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3" aria-hidden="true">
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
                <div className="card p-4 sm:p-6 space-y-4">
                  <h2 className="font-semibold text-slate-800 flex items-center gap-2">Configuration</h2>

                  <FormField label="Target Role (optional)" hint="e.g., Senior Data Scientist">
                    <Input
                      type="text"
                      value={targetRole}
                      onChange={e => setTargetRole(e.target.value)}
                      placeholder="e.g. Senior Data Scientist"
                    />
                  </FormField>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <FormField label="Max Modules">
                      <Select
                        value={maxModules}
                        onChange={e => setMaxModules(Number(e.target.value))}
                        options={[10, 15, 20, 25, 30].map(n => ({ value: n, label: `${n} modules` }))}
                      />
                    </FormField>
                    <FormField label="Time Budget (weeks)">
                      <Input
                        type="number"
                        value={timeWeeks}
                        onChange={e => setTimeWeeks(e.target.value ? Number(e.target.value) : '')}
                        placeholder="Optional"
                        min={1}
                        max={104}
                      />
                    </FormField>
                  </div>
                </div>
              </div>

              {/* Right Column — JD */}
              <div className="card p-4 sm:p-6 flex flex-col">
                <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
                  <Brain size={16} className="text-sage-600" aria-hidden="true" />
                  Job Description
                  <span className="text-rose-500 text-sm" aria-label="Required">*</span>
                </h2>
                <p className="text-xs text-slate-400 mb-4">Paste the full JD text (min 50 characters)</p>
                <TextArea
                  value={jdText}
                  onChange={e => setJdText(e.target.value)}
                  placeholder="Paste the full job description here..."
                  className="flex-1 min-h-80"
                  aria-invalid={jdText.length > 0 && jdText.length < 50}
                />
                <div className="flex items-center justify-between mt-3">
                  <span
                    className={`text-xs ${jdText.length < 50 ? 'text-rose-400' : 'text-sage-500'}`}
                    aria-live="polite"
                  >
                    {jdText.length} characters{' '}
                    {jdText.length < 50 ? `(need ${50 - jdText.length} more)` : '✓'}
                  </span>
                  {jdText.length > 0 && (
                    <button
                      onClick={() => setJdText('')}
                      className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
                      aria-label="Clear job description"
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
                    w-full py-3 sm:py-4 rounded-xl font-semibold text-base flex items-center justify-center gap-3
                    transition-all duration-200
                    ${
                      canSubmit
                        ? 'btn-primary'
                        : 'bg-slate-100 text-slate-300 cursor-not-allowed'
                    }
                  `}
                  aria-disabled={!canSubmit}
                >
                  {!resumeFile && <AlertCircle size={18} aria-hidden="true" />}
                  {canSubmit && <Brain size={18} aria-hidden="true" />}
                  Run Adaptive Analysis
                  {canSubmit && <ChevronRight size={18} aria-hidden="true" />}
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
