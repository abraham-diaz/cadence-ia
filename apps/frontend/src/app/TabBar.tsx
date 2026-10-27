import { CalendarDays, House, Tag, type LucideIcon } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { setTabDirection, useTabSwipe } from './tabNavigation.ts'
import './tab-bar.css'

/** The main pages, with the tab bar at the bottom like an iPhone app. */
export function TabLayout() {
  useTabSwipe()
  return (
    <div className="with-tabs">
      <Outlet />
      <TabBar />
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
  const { pathname } = useLocation()
  return (
    <NavLink
      to={to}
      end={end}
      className="tab"
      aria-label={label}
      onClick={() => setTabDirection(pathname, to)}
      viewTransition
    >
      <Icon size={22} strokeWidth={1.75} aria-hidden="true" />
    </NavLink>
  )
}
