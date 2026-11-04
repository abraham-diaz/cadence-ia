import { CalendarDays, House, Tag } from 'lucide-react'
import { Activity, useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import HomePage from '../features/home/HomePage.tsx'
import PlanPage from '../features/plans/PlanPage.tsx'
import WorkoutTypesPage from '../features/workout-types/WorkoutTypesPage.tsx'
import { useTabSwipe } from './tabNavigation.ts'
import './tab-bar.css'

// In order: swiping moves along this list.
const TABS = [
  { path: '/', label: 'Inicio', icon: House, Page: HomePage },
  { path: '/plan', label: 'Plan', icon: CalendarDays, Page: PlanPage },
  { path: '/tipos', label: 'Tipos', icon: Tag, Page: WorkoutTypesPage },
]
const TAB_PATHS = TABS.map((tab) => tab.path)

/** The main pages, with the tab bar at the bottom like an iPhone app. They stay mounted
    while hidden, so switching tabs or coming back from a detail page is instant. */
export function TabPages() {
  const { pathname } = useLocation()
  const onTab = TAB_PATHS.includes(pathname)
  const enter = useEnterDirection(pathname)
  useTabSwipe(TAB_PATHS)
  return (
    <div className="with-tabs">
      {TABS.map(({ path, Page }) => (
        <Activity key={path} mode={path === pathname ? 'visible' : 'hidden'}>
          {/* Shown again after display: none, the wrapper replays its slide-in. */}
          <div className="tab-page" data-enter={enter}>
            <Page />
          </div>
        </Activity>
      ))}
      {onTab && (
        <nav className="tab-bar" aria-label="Secciones">
          {TABS.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end className="tab" aria-label={label}>
              <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}

/** Which side the page coming in slides from: none when coming back from a detail page. */
function useEnterDirection(pathname: string) {
  const [shown, setShown] = useState<{ path: string; enter?: 'forward' | 'back' }>({ path: pathname })
  if (shown.path !== pathname) {
    const from = TAB_PATHS.indexOf(shown.path)
    const to = TAB_PATHS.indexOf(pathname)
    setShown({ path: pathname, enter: from === -1 || to === -1 ? undefined : to > from ? 'forward' : 'back' })
  }
  return shown.enter
}
