import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { EmptyState } from './components/ui'
import { SetupPage } from './pages/SetupPage'
import { TradeDetailPage } from './pages/TradeDetailPage'
import { TradeFormPage } from './pages/TradeFormPage'
import { TradesPage } from './pages/TradesPage'

// URL → page. Every page renders inside <Layout> (header + navigation).
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/trades" replace />} />
        <Route path="trades" element={<TradesPage />} />
        <Route path="trades/new" element={<TradeFormPage />} />
        <Route path="trades/:tradeId" element={<TradeDetailPage />} />
        <Route path="trades/:tradeId/edit" element={<TradeFormPage />} />
        <Route path="setup" element={<SetupPage />} />
        <Route path="*" element={<EmptyState title="Page not found" />} />
      </Route>
    </Routes>
  )
}
