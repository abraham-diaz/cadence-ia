import { createBrowserRouter, Outlet, ScrollRestoration } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import HomePage from '../features/home/HomePage.tsx'
import PlanChatPage from '../features/plans/PlanChatPage.tsx'
import PlanPage from '../features/plans/PlanPage.tsx'
import PlanReviewPage from '../features/plans/PlanReviewPage.tsx'
import ExerciseDetailPage from '../features/exercises/ExerciseDetailPage.tsx'
import SessionDetailPage from '../features/sessions/SessionDetailPage.tsx'
import WorkoutTypesPage from '../features/workout-types/WorkoutTypesPage.tsx'
import { TabLayout } from './TabBar.tsx'

// A data router: it's what enables view transitions and scroll restoration.
const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      {
        element: <TabLayout />,
        children: [
          { path: '/', element: <HomePage /> },
          { path: '/plan', element: <PlanPage /> },
          { path: '/tipos', element: <WorkoutTypesPage /> },
        ],
      },
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
      <Outlet />
      <ScrollRestoration />
    </>
  )
}

export default function App() {
  return <RouterProvider router={router} />
}
