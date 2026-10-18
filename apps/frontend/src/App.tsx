import { BrowserRouter, Route, Routes } from 'react-router'
import SessionDetailPage from './pages/SessionDetailPage.tsx'
import SessionListPage from './pages/SessionListPage.tsx'
import WorkoutTypesPage from './pages/WorkoutTypesPage.tsx'

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
