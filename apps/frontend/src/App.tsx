import { BrowserRouter, Route, Routes } from 'react-router'
import SessionDetailPage from './pages/SessionDetailPage.tsx'
import SessionListPage from './pages/SessionListPage.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/sesion/:id" element={<SessionDetailPage />} />
      </Routes>
    </BrowserRouter>
  )
}
