import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from '@/pages/HomePage'
import AnalyzePage from '@/pages/AnalyzePage'
import DashboardPage from '@/pages/DashboardPage'
import { useStore } from '@/store/useStore'
import { getSessionToken } from '@/utils/api'

function DashboardGate() {
  const hasResult = useStore(state => Boolean(state.result && state.sessionId))
  const hasSessionToken = Boolean(getSessionToken())

  if (!hasResult || !hasSessionToken) {
    return <Navigate to="/analyze" replace />
  }

  return <DashboardPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/analyze" element={<AnalyzePage />} />
      <Route path="/dashboard" element={<DashboardGate />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
