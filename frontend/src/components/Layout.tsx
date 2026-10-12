import { NavLink, Outlet } from 'react-router'
import { BackendStatus } from './BackendStatus'

const NAV = [
  { to: '/trades', label: 'Journal' },
  { to: '/setup', label: 'Portfolios & strategies' },
]

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <span className="font-bold">Macro Trading Journal</span>
          <nav className="flex gap-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md px-2.5 py-1.5 ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <span className="ml-auto">
            <BackendStatus />
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {/* The current page renders here. */}
        <Outlet />
      </main>
    </div>
  )
}
