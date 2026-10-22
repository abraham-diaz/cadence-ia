import { BrowserRouter, Route, Routes } from 'react-router'
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
      </Routes>
    </BrowserRouter>
  )
}
