import { BackendStatus } from './components/BackendStatus'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <h1 className="text-xl font-bold">Macro Trading Journal</h1>
          <p className="text-sm text-slate-500">Milestone 3 — frontend ↔ backend ↔ database</p>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-6">
        <BackendStatus />
      </main>
    </div>
  )
}
