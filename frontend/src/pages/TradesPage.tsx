import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { listPortfolios, listTrades } from '../api/journal'
import type { Direction, Trade, TradeFilters, TradeStatus } from '../api/types'
import { formatDateTime, formatPrice, trimDecimal } from '../lib/format'
import { firstEntry, firstExit, instrumentLabel, tradeDate } from '../lib/trade'
import { Button, Card, DirectionBadge, EmptyState, ErrorBox, Input, Loading, Select, StatusBadge } from '../components/ui'

export function TradesPage() {
  // Filters live in the URL (?status=open&q=cpi) so the back button and bookmarks keep them.
  const [params, setParams] = useSearchParams()
  const filters: TradeFilters = {
    portfolio_id: params.get('portfolio_id') ? Number(params.get('portfolio_id')) : undefined,
    status: (params.get('status') as TradeStatus) || undefined,
    direction: (params.get('direction') as Direction) || undefined,
    q: params.get('q') || undefined,
  }

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  // Search box: wait until typing pauses (300 ms) before asking the server.
  const [search, setSearch] = useState(filters.q ?? '')
  useEffect(() => {
    const timer = setTimeout(() => {
      const q = search.trim()
      if (q === (params.get('q') ?? '')) return
      const next = new URLSearchParams(params)
      if (q) next.set('q', q)
      else next.delete('q')
      setParams(next, { replace: true })
    }, 300)
    return () => clearTimeout(timer)
  }, [search, params, setParams])

  const portfolios = useQuery({ queryKey: ['portfolios'], queryFn: listPortfolios })
  const trades = useQuery({ queryKey: ['trades', filters], queryFn: () => listTrades(filters) })
  const hasFilters = Boolean(filters.portfolio_id || filters.status || filters.direction || filters.q)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Trade journal</h1>
        <Link to="/trades/new">
          <Button>+ New trade</Button>
        </Link>
      </div>

      <Card className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Input
          type="search"
          placeholder="Search symbol, thesis, notes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search trades"
        />
        <Select value={filters.portfolio_id ?? ''} onChange={(e) => setFilter('portfolio_id', e.target.value)} aria-label="Portfolio">
          <option value="">All portfolios</option>
          {portfolios.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
        <Select value={filters.status ?? ''} onChange={(e) => setFilter('status', e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          <option value="planned">Planned</option>
          <option value="open">Open</option>
          <option value="partially_closed">Partially closed</option>
          <option value="closed">Closed</option>
        </Select>
        <Select value={filters.direction ?? ''} onChange={(e) => setFilter('direction', e.target.value)} aria-label="Direction">
          <option value="">Long &amp; short</option>
          <option value="long">Long</option>
          <option value="short">Short</option>
        </Select>
      </Card>

      {trades.isPending && <Loading what="Loading trades" />}
      {trades.isError && <ErrorBox error={trades.error} onRetry={() => trades.refetch()} />}
      {trades.data?.length === 0 &&
        (hasFilters ? (
          <EmptyState title="No trades match these filters" />
        ) : portfolios.data?.length === 0 ? (
          <EmptyState title="Start by creating a portfolio">
            <Link to="/setup" className="font-medium text-slate-900 underline">Go to Portfolios &amp; strategies</Link>
          </EmptyState>
        ) : (
          <EmptyState title="No trades yet">
            <Link to="/trades/new" className="font-medium text-slate-900 underline">Record your first trade</Link>
          </EmptyState>
        ))}

      {trades.data && trades.data.length > 0 && (
        <>
          <TradeTable trades={trades.data} />
          <TradeCards trades={trades.data} />
          <p className="text-xs text-slate-500">{trades.data.length} trade(s). P&amp;L and R-multiples arrive in Milestone 5.</p>
        </>
      )}
    </div>
  )
}

/** Desktop: a table. Hidden below the "md" breakpoint. */
function TradeTable({ trades }: { trades: Trade[] }) {
  return (
    <div className="hidden overflow-x-auto rounded-lg border border-slate-200 bg-white md:block">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
          <tr>
            {['Date', 'Instrument', 'Side', 'Qty', 'Entry', 'Stop', 'Exit', 'Status', 'Portfolio', 'Strategy'].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {trades.map((t) => {
            const fmt = t.instrument.price_format
            const entry = firstEntry(t)
            const exit = firstExit(t)
            return (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2 text-slate-500">{formatDateTime(tradeDate(t))}</td>
                <td className="px-3 py-2 font-medium">
                  <Link to={`/trades/${t.id}`} className="hover:underline">{instrumentLabel(t)}</Link>
                </td>
                <td className="px-3 py-2"><DirectionBadge direction={t.direction} /></td>
                <td className="px-3 py-2">{trimDecimal(entry?.quantity ?? t.planned_quantity)}</td>
                <td className="px-3 py-2">{formatPrice(entry?.price ?? t.planned_entry_price, fmt)}{!entry && t.planned_entry_price && <span className="text-xs text-slate-400"> plan</span>}</td>
                <td className="px-3 py-2">{formatPrice(t.initial_stop_price, fmt)}</td>
                <td className="px-3 py-2">{formatPrice(exit?.price, fmt)}</td>
                <td className="px-3 py-2"><StatusBadge status={t.status} /></td>
                <td className="px-3 py-2 text-slate-600">{t.portfolio.name}</td>
                <td className="px-3 py-2 text-slate-600">{t.strategy?.name ?? '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** Phones: one card per trade. Hidden from the "md" breakpoint up. */
function TradeCards({ trades }: { trades: Trade[] }) {
  return (
    <ul className="space-y-2 md:hidden">
      {trades.map((t) => {
        const fmt = t.instrument.price_format
        const entry = firstEntry(t)
        const exit = firstExit(t)
        return (
          <li key={t.id}>
            <Link to={`/trades/${t.id}`}>
              <Card className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{instrumentLabel(t)} <DirectionBadge direction={t.direction} /></span>
                  <StatusBadge status={t.status} />
                </div>
                <p className="text-sm text-slate-600">
                  {trimDecimal(entry?.quantity ?? t.planned_quantity)} @ {formatPrice(entry?.price ?? t.planned_entry_price, fmt)}
                  {' · '}stop {formatPrice(t.initial_stop_price, fmt)}
                  {exit && <> · exit {formatPrice(exit.price, fmt)}</>}
                </p>
                <p className="text-xs text-slate-500">{formatDateTime(tradeDate(t))} · {t.portfolio.name}</p>
              </Card>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
