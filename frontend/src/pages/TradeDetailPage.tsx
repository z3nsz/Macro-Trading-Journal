import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { deleteTrade, getTrade } from '../api/journal'
import { formatDateTime, formatMoney, formatPrice, formatR, pnlColor, trimDecimal } from '../lib/format'
import { instrumentLabel } from '../lib/trade'
import { AccountTypeBadge, Button, Card, DirectionBadge, EmptyState, ErrorBox, Loading, StatusBadge } from '../components/ui'

export function TradeDetailPage() {
  const id = Number(useParams().tradeId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const trade = useQuery({ queryKey: ['trade', id], queryFn: () => getTrade(id) })

  const remove = useMutation({
    mutationFn: () => deleteTrade(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['trade', id] })
      queryClient.invalidateQueries({ queryKey: ['trades'] })
      navigate('/trades')
    },
  })

  if (trade.isPending) return <Loading what="Loading trade" />
  if (trade.isError) {
    if (trade.error instanceof ApiError && trade.error.status === 404) {
      return (
        <EmptyState title="Trade not found">
          <Link to="/trades" className="underline">Back to journal</Link>
        </EmptyState>
      )
    }
    return <ErrorBox error={trade.error} onRetry={() => trade.refetch()} />
  }

  const t = trade.data
  const m = t.metrics
  const fmt = t.instrument.price_format
  const price = (v: string | null | undefined) => formatPrice(v, fmt)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/trades" className="text-sm text-slate-500 hover:underline">← Journal</Link>
          <h1 className="mt-1 flex flex-wrap items-center gap-2 text-xl font-semibold">
            {instrumentLabel(t)} <DirectionBadge direction={t.direction} /> <StatusBadge status={t.status} />
          </h1>
          <p className="text-sm text-slate-500">
            {t.instrument.name} · {t.portfolio.name} <AccountTypeBadge type={t.portfolio.account_type} />
            {t.strategy && <> · {t.strategy.name}</>}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/trades/${t.id}/edit`}><Button variant="secondary">Edit</Button></Link>
          <Button
            variant="danger"
            disabled={remove.isPending}
            onClick={() => { if (confirm('Delete this trade permanently?')) remove.mutate() }}
          >
            Delete
          </Button>
        </div>
      </div>
      {remove.isError && <ErrorBox error={remove.error} />}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Plan</h2>
          <dl className="grid grid-cols-2 gap-y-1 text-sm">
            <Row label="Quantity">{trimDecimal(t.planned_quantity)}</Row>
            <Row label="Planned entry">{price(t.planned_entry_price)}</Row>
            <Row label="Initial stop">{price(t.initial_stop_price)}</Row>
            {t.current_stop_price && <Row label="Current stop">{price(t.current_stop_price)}</Row>}
            {m.targets.map((x) => (
              <Row key={x.sequence} label={`TP${x.sequence}`}>
                {price(x.price)}{' '}
                <span className="text-xs text-slate-500">
                  ({x.reward_to_risk ? `${x.reward_to_risk} R:R` : 'R:R unavailable'})
                </span>
              </Row>
            ))}
            <Row label="Planned risk">
              <Metric value={m.planned_risk_amount && formatMoney(m.planned_risk_amount)} reason={m.unavailable.planned_risk} />
            </Row>
          </dl>
          <p className="mt-3 text-xs text-slate-400">
            Reward-to-risk = distance to target ÷ distance to initial stop, from the planned entry.
          </p>
        </Card>

        <Card>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Executions</h2>
          {t.executions.length === 0 ? (
            <p className="text-sm text-slate-500">Not entered yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr><th className="py-1">Fill</th><th>Qty</th><th>Price</th><th>Fees</th><th>Time</th></tr>
              </thead>
              <tbody>
                {t.executions.map((e) => (
                  <tr key={e.id} className="border-t border-slate-100">
                    <td className="py-1 capitalize">{e.kind}</td>
                    <td>{trimDecimal(e.quantity)}</td>
                    <td>{price(e.price)}</td>
                    <td>{formatMoney(e.fees)}</td>
                    <td className="text-slate-500">{formatDateTime(e.executed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Risk &amp; results</h2>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
          <Row label="Initial risk">
            <Metric value={m.initial_risk_amount && formatMoney(m.initial_risk_amount)} reason={m.unavailable.initial_risk} />
          </Row>
          <Row label="Avg entry">{price(m.average_entry_price)}</Row>
          <Row label="Avg exit">{price(m.average_exit_price)}</Row>
          <Row label="Open qty">{trimDecimal(m.open_quantity)}</Row>
          <Row label="Gross realized">
            <Metric value={m.gross_realized_pnl && formatMoney(m.gross_realized_pnl)} reason={m.unavailable.realized_pnl} className={pnlColor(m.gross_realized_pnl)} />
          </Row>
          <Row label="Fees counted">
            <Metric value={m.fees_counted && formatMoney(m.fees_counted)} reason={m.unavailable.realized_pnl} />
          </Row>
          <Row label="Net realized">
            <Metric value={m.net_realized_pnl && formatMoney(m.net_realized_pnl)} reason={m.unavailable.realized_pnl} className={`font-semibold ${pnlColor(m.net_realized_pnl)}`} />
          </Row>
          <Row label="Realized R">
            <Metric value={m.realized_r && formatR(m.realized_r)} reason={m.unavailable.realized_r} className={`font-semibold ${pnlColor(m.realized_r)}`} />
          </Row>
          <Row label="Unrealized">
            <Metric
              value={m.unrealized_pnl && `${formatMoney(m.unrealized_pnl)} (${m.unrealized_price?.source}, ${formatDateTime(m.unrealized_price?.as_of)})`}
              reason={m.unavailable.unrealized_pnl}
              className={pnlColor(m.unrealized_pnl)}
            />
          </Row>
          <Row label="All fees paid">{formatMoney(m.total_fees)}</Row>
        </dl>
        <p className="mt-3 text-xs text-slate-400">
          Net = gross − exit fees − the closed share of entry fees. Realized R = net realized P&amp;L ÷ initial risk
          (|avg entry − initial stop| × quantity × {Number(t.instrument.point_value).toLocaleString()} $/point).
          {t.status === 'partially_closed' && ' Partially closed: results so far, for the closed portion.'}
        </p>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <TextCard title="Thesis" text={t.thesis} />
        <TextCard title="Catalyst / economic event" text={t.catalyst} />
        <TextCard title="Notes" text={t.notes} />
        <TextCard title="Post-trade reflection" text={t.reflection} />
      </div>
      <p className="text-xs text-slate-400">Created {formatDateTime(t.created_at)} · last updated {formatDateTime(t.updated_at)}</p>
    </div>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd>{children}</dd>
    </>
  )
}

/** A calculated value, or "Unavailable" with the reason — never an invented number. */
function Metric({ value, reason, className = '' }: { value: string | null; reason?: string; className?: string }) {
  if (value) return <span className={className}>{value}</span>
  return (
    <span className="text-slate-400" title={reason}>
      Unavailable{reason && <span className="block text-xs">{reason}</span>}
    </span>
  )
}

function TextCard({ title, text }: { title: string; text: string | null }) {
  return (
    <Card>
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {text ? <p className="whitespace-pre-wrap text-sm">{text}</p> : <p className="text-sm text-slate-400">—</p>}
    </Card>
  )
}
