import { createBrowserRouter, Outlet, ScrollRestoration } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import PlanChatPage from '../features/plans/PlanChatPage.tsx'
import PlanReviewPage from '../features/plans/PlanReviewPage.tsx'
import ExerciseDetailPage from '../features/exercises/ExerciseDetailPage.tsx'
import SessionDetailPage from '../features/sessions/SessionDetailPage.tsx'
import { TabPages } from './TabBar.tsx'

// A data router: it's what enables view transitions and scroll restoration.
const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      // Drawn by TabPages, which keeps them alive between visits.
      { path: '/' },
      { path: '/plan' },
      { path: '/tipos' },
      { path: '/sesion/:id', element: <SessionDetailPage /> },
      { path: '/ejercicio/:id', element: <ExerciseDetailPage /> },
      { path: '/plan/nuevo', element: <PlanChatPage /> },
      { path: '/plan/revisar', element: <PlanReviewPage /> },
    ],
  },
])

function Root() {
  return (
    <>
      <TabPages />
      <Outlet />
      {/* By path, so each tab comes back where it was left. */}
      <ScrollRestoration getKey={(location) => location.pathname} />
    </>
  )
}

export default function App() {
  return <RouterProvider router={router} />
}
