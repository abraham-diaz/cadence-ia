import { CalendarDays, House, Tag, type LucideIcon } from 'lucide-react'
import { Activity, useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import HomePage from '../features/home/HomePage.tsx'
import PlanPage from '../features/plans/PlanPage.tsx'
import WorkoutTypesPage from '../features/workout-types/WorkoutTypesPage.tsx'
import { TAB_PATHS, useTabSwipe } from './tabNavigation.ts'
import './tab-bar.css'

// Same order as TAB_PATHS.
const PAGES = [HomePage, PlanPage, WorkoutTypesPage]

/** The main pages, with the tab bar at the bottom like an iPhone app. They stay mounted
    while hidden, so switching tabs or coming back from a detail page is instant. */
export function TabPages() {
  const { pathname } = useLocation()
  const onTab = TAB_PATHS.includes(pathname)
  const enter = useEnterDirection(pathname)
  useTabSwipe()
  return (
    <div className="with-tabs">
      {TAB_PATHS.map((path, i) => {
        const Page = PAGES[i]
        return (
          <Activity key={path} mode={path === pathname ? 'visible' : 'hidden'}>
            {/* Shown again after display: none, the wrapper replays its slide-in. */}
            <div className="tab-page" data-enter={enter}>
              <Page />
            </div>
          </Activity>
        )
      })}
      {onTab && <TabBar />}
    </div>
  )
}

// Same order as TAB_PATHS, which the swipe follows.
function TabBar() {
  return (
    <nav className="tab-bar" aria-label="Secciones">
      <Tab to="/" label="Inicio" icon={House} end />
      <Tab to="/plan" label="Plan" icon={CalendarDays} />
      <Tab to="/tipos" label="Tipos" icon={Tag} />
    </nav>
  )
}

function Tab({ to, label, icon: Icon, end }: { to: string; label: string; icon: LucideIcon; end?: boolean }) {
  return (
    <NavLink to={to} end={end} className="tab" aria-label={label}>
      <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
    </NavLink>
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
