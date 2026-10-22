import { BrowserRouter, Route, Routes } from 'react-router'
import PlanChatPage from '../features/plans/PlanChatPage.tsx'
import PlanPage from '../features/plans/PlanPage.tsx'
import PlanReviewPage from '../features/plans/PlanReviewPage.tsx'
import SessionDetailPage from '../features/sessions/SessionDetailPage.tsx'
import SessionListPage from '../features/sessions/SessionListPage.tsx'
import WorkoutTypesPage from '../features/workout-types/WorkoutTypesPage.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/sesion/:id" element={<SessionDetailPage />} />
        <Route path="/tipos" element={<WorkoutTypesPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/plan/nuevo" element={<PlanChatPage />} />
        <Route path="/plan/revisar" element={<PlanReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}
