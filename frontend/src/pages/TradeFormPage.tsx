import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import {
  createContract,
  createStock,
  createTrade,
  getTrade,
  listContracts,
  listInstruments,
  listPortfolios,
  listStrategies,
  replaceTrade,
} from '../api/journal'
import type { AssetClass, Direction, FillInput, Instrument, Trade, TradeInput } from '../api/types'
import { isoToLocalInput, localInputToIso, toThirtySeconds, trimDecimal } from '../lib/format'
import { firstEntry, firstExit } from '../lib/trade'
import { fieldErrorMap } from '../lib/errors'
import { Button, Card, ErrorBox, Field, Input, Loading, Select, TextArea } from '../components/ui'

// Everything in the form is kept as strings, exactly as typed; we convert only when submitting.
interface FormState {
  portfolio_id: string
  asset_class: AssetClass
  instrument_id: string
  futures_contract_id: string
  strategy_id: string
  direction: Direction
  planned_quantity: string
  planned_entry_price: string
  initial_stop_price: string
  current_stop_price: string
  targets: string[]
  thesis: string
  catalyst: string
  notes: string
  reflection: string
  has_entry: boolean
  entry_price: string
  entry_time: string
  entry_fees: string
  has_exit: boolean
  exit_price: string
  exit_time: string
  exit_quantity: string
  exit_fees: string
}

const EMPTY: FormState = {
  portfolio_id: '', asset_class: 'future', instrument_id: '', futures_contract_id: '', strategy_id: '',
  direction: 'long', planned_quantity: '1', planned_entry_price: '', initial_stop_price: '', current_stop_price: '',
  targets: [''], thesis: '', catalyst: '', notes: '', reflection: '',
  has_entry: false, entry_price: '', entry_time: '', entry_fees: '',
  has_exit: false, exit_price: '', exit_time: '', exit_quantity: '', exit_fees: '',
}

function fromTrade(t: Trade): FormState {
  const entry = firstEntry(t)
  const exit = firstExit(t)
  const s = (v: string | null | undefined) => (v ? trimDecimal(v) : '')
  return {
    portfolio_id: String(t.portfolio.id),
    asset_class: t.instrument.asset_class,
    instrument_id: String(t.instrument.id),
    futures_contract_id: t.futures_contract ? String(t.futures_contract.id) : '',
    strategy_id: t.strategy ? String(t.strategy.id) : '',
    direction: t.direction,
    planned_quantity: s(t.planned_quantity),
    planned_entry_price: s(t.planned_entry_price),
    initial_stop_price: s(t.initial_stop_price),
    current_stop_price: s(t.current_stop_price),
    targets: t.targets.length ? t.targets.map((x) => s(x.price)) : [''],
    thesis: t.thesis ?? '', catalyst: t.catalyst ?? '', notes: t.notes ?? '', reflection: t.reflection ?? '',
    has_entry: Boolean(entry),
    entry_price: s(entry?.price), entry_time: entry ? isoToLocalInput(entry.executed_at) : '', entry_fees: s(entry?.fees),
    has_exit: Boolean(exit),
    exit_price: s(exit?.price), exit_time: exit ? isoToLocalInput(exit.executed_at) : '',
    exit_quantity: exit && entry && exit.quantity !== entry.quantity ? s(exit.quantity) : '',
    exit_fees: s(exit?.fees),
  }
}

function toInput(f: FormState): TradeInput {
  const orNull = (v: string) => (v.trim() === '' ? null : v.trim())
  const fill = (price: string, time: string, fees: string, quantity?: string): FillInput => ({
    price: price.trim(),
    executed_at: time ? localInputToIso(time) : '',
    fees: fees.trim() || '0',
    ...(quantity?.trim() ? { quantity: quantity.trim() } : {}),
  })
  return {
    portfolio_id: Number(f.portfolio_id),
    instrument_id: Number(f.instrument_id),
    futures_contract_id: f.asset_class === 'future' && f.futures_contract_id ? Number(f.futures_contract_id) : null,
    strategy_id: f.strategy_id ? Number(f.strategy_id) : null,
    direction: f.direction,
    planned_quantity: f.planned_quantity.trim(),
    planned_entry_price: orNull(f.planned_entry_price),
    initial_stop_price: orNull(f.initial_stop_price),
    current_stop_price: orNull(f.current_stop_price),
    targets: f.targets.filter((t) => t.trim() !== '').map((price) => ({ price: price.trim() })),
    thesis: orNull(f.thesis), catalyst: orNull(f.catalyst), notes: orNull(f.notes), reflection: orNull(f.reflection),
    entry: f.has_entry ? fill(f.entry_price, f.entry_time, f.entry_fees) : null,
    exit: f.has_entry && f.has_exit ? fill(f.exit_price, f.exit_time, f.exit_fees, f.exit_quantity) : null,
  }
}

export function TradeFormPage() {
  const { tradeId } = useParams()
  const editing = tradeId !== undefined
  const existing = useQuery({ queryKey: ['trade', Number(tradeId)], queryFn: () => getTrade(Number(tradeId)), enabled: editing })

  if (editing && existing.isPending) return <Loading what="Loading trade" />
  if (editing && existing.isError) return <ErrorBox error={existing.error} onRetry={() => existing.refetch()} />
  // `key` makes React start a fresh form when switching between trades.
  return <TradeForm key={tradeId ?? 'new'} existing={existing.data} />
}

function TradeForm({ existing }: { existing?: Trade }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<FormState>(existing ? fromTrade(existing) : EMPTY)
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }))

  const portfolios = useQuery({ queryKey: ['portfolios'], queryFn: listPortfolios })
  const strategies = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })
  const instruments = useQuery({ queryKey: ['instruments', form.asset_class], queryFn: () => listInstruments(form.asset_class) })
  const instrument = instruments.data?.find((i) => String(i.id) === form.instrument_id)

  // New trades default to the first portfolio until the user picks one.
  const portfolioId = form.portfolio_id || (portfolios.data?.[0] ? String(portfolios.data[0].id) : '')

  const save = useMutation({
    mutationFn: (input: TradeInput) => (existing ? replaceTrade(existing.id, input) : createTrade(input)),
    onSuccess: (trade) => {
      queryClient.invalidateQueries({ queryKey: ['trades'] })
      queryClient.setQueryData(['trade', trade.id], trade)
      navigate(`/trades/${trade.id}`)
    },
  })
  const errors = fieldErrorMap(save.error)
  const unplacedErrors = save.error ? Object.keys(errors).filter((k) => !SHOWN_FIELDS.has(k) && !k.startsWith('targets.')) : []

  // Planned risk is fixed once the trade has been entered (enforced by the server too).
  const initialStopLocked = Boolean(existing && firstEntry(existing))

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    save.mutate(toInput({ ...form, portfolio_id: portfolioId }))
  }

  if (portfolios.data?.length === 0) {
    return (
      <Card>
        <p>You need a portfolio before recording trades.</p>
        <Link to="/setup" className="mt-2 inline-block font-medium underline">Create a portfolio</Link>
      </Card>
    )
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">{existing ? `Edit trade #${existing.id}` : 'New trade'}</h1>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" onClick={() => navigate(-1)}>Cancel</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save trade'}</Button>
        </div>
      </div>

      {save.isError && (Object.keys(errors).length === 0 || unplacedErrors.length > 0) && <ErrorBox error={save.error} />}
      {Object.keys(errors).length > 0 && unplacedErrors.length === 0 && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Please fix the highlighted fields.</p>
      )}

      {/* ---------------- instrument ---------------- */}
      <Section title="Instrument">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Portfolio" error={errors.portfolio_id}>
            <Select value={portfolioId} onChange={(e) => set('portfolio_id', e.target.value)} required>
              {portfolios.data?.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.account_type})</option>
              ))}
            </Select>
          </Field>
          <Field label="Asset type">
            <Select
              value={form.asset_class}
              onChange={(e) => setForm((f) => ({ ...f, asset_class: e.target.value as AssetClass, instrument_id: '', futures_contract_id: '' }))}
              disabled={Boolean(existing)}
            >
              <option value="future">Futures</option>
              <option value="stock">Stock</option>
            </Select>
          </Field>
          <Field label={form.asset_class === 'future' ? 'Product' : 'Stock'} error={errors.instrument_id}>
            <Select
              value={form.instrument_id}
              onChange={(e) => setForm((f) => ({ ...f, instrument_id: e.target.value, futures_contract_id: '' }))}
              required
            >
              <option value="">{instruments.isPending ? 'Loading…' : 'Choose…'}</option>
              {instruments.data?.map((i) => (
                <option key={i.id} value={i.id}>{i.symbol} — {i.name}</option>
              ))}
            </Select>
          </Field>
          {form.asset_class === 'future' ? (
            <ContractPicker
              instrument={instrument}
              value={form.futures_contract_id}
              onChange={(v) => set('futures_contract_id', v)}
              error={errors.futures_contract_id}
            />
          ) : (
            <AddStock onAdded={(stock) => set('instrument_id', String(stock.id))} />
          )}
        </div>
        {instrument && <InstrumentSpec instrument={instrument} />}
      </Section>

      {/* ---------------- plan ---------------- */}
      <Section title="Plan">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Direction" error={errors.direction}>
            <Select value={form.direction} onChange={(e) => set('direction', e.target.value as Direction)}>
              <option value="long">Long</option>
              <option value="short">Short</option>
            </Select>
          </Field>
          <Field label={form.asset_class === 'future' ? 'Contracts' : 'Shares'} error={errors.planned_quantity}>
            <Input inputMode="decimal" value={form.planned_quantity} onChange={(e) => set('planned_quantity', e.target.value)} required />
          </Field>
          <PriceField label="Planned entry" field="planned_entry_price" form={form} set={set} errors={errors} instrument={instrument} />
          <PriceField
            label="Initial stop loss"
            field="initial_stop_price"
            form={form}
            set={set}
            errors={errors}
            instrument={instrument}
            disabled={initialStopLocked}
            hint={initialStopLocked ? 'Locked after entry to preserve planned risk. Use “current stop” for later moves.' : undefined}
          />
          {existing && form.has_entry && (
            <PriceField label="Current stop (if moved)" field="current_stop_price" form={form} set={set} errors={errors} instrument={instrument} />
          )}
          <Field label="Strategy" error={errors.strategy_id}>
            <Select value={form.strategy_id} onChange={(e) => set('strategy_id', e.target.value)}>
              <option value="">None</option>
              {strategies.data?.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="mt-4">
          <p className="mb-1 text-sm font-medium text-slate-700">Take-profit targets</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {form.targets.map((target, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="flex-1">
                  <Field label={`TP${i + 1}`} error={errors[`targets.${i}.price`]} hint={thirtySecondsHint(target, instrument)}>
                    <Input
                      inputMode="decimal"
                      value={target}
                      onChange={(e) => set('targets', form.targets.map((t, j) => (j === i ? e.target.value : t)))}
                    />
                  </Field>
                </div>
                {form.targets.length > 1 && (
                  <button
                    type="button"
                    className="mt-7 text-sm text-slate-400 hover:text-red-600"
                    aria-label={`Remove TP${i + 1}`}
                    onClick={() => set('targets', form.targets.filter((_, j) => j !== i))}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
          {form.targets.length < 5 && (
            <button type="button" className="mt-2 text-sm font-medium text-slate-600 hover:underline" onClick={() => set('targets', [...form.targets, ''])}>
              + Add target
            </button>
          )}
        </div>
      </Section>

      {/* ---------------- reasoning ---------------- */}
      <Section title="Reasoning">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Thesis — why this trade?" error={errors.thesis}>
            <TextArea value={form.thesis} onChange={(e) => set('thesis', e.target.value)} />
          </Field>
          <Field label="Catalyst / economic event" error={errors.catalyst}>
            <TextArea value={form.catalyst} onChange={(e) => set('catalyst', e.target.value)} placeholder="e.g. September CPI release" />
          </Field>
        </div>
      </Section>

      {/* ---------------- executions ---------------- */}
      <Section title="Execution">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.has_entry} onChange={(e) => set('has_entry', e.target.checked)} disabled={Boolean(existing && firstEntry(existing))} />
          I have entered this trade
        </label>
        {errors.exit && <p className="mt-1 text-xs font-medium text-red-600">{errors.exit}</p>}

        {form.has_entry && (
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <PriceField label="Entry fill price" field="entry_price" errorKey="entry.price" form={form} set={set} errors={errors} instrument={instrument} required />
            <Field label="Entry time (your local time)" error={errors['entry.executed_at']}>
              <Input type="datetime-local" value={form.entry_time} onChange={(e) => set('entry_time', e.target.value)} required />
            </Field>
            <Field label="Entry fees & commissions ($)" error={errors['entry.fees']}>
              <Input inputMode="decimal" value={form.entry_fees} onChange={(e) => set('entry_fees', e.target.value)} placeholder="0.00" />
            </Field>
          </div>
        )}

        {form.has_entry && (
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.has_exit} onChange={(e) => set('has_exit', e.target.checked)} />
            I have exited (fully or partly)
          </label>
        )}

        {form.has_entry && form.has_exit && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <PriceField label="Exit fill price" field="exit_price" errorKey="exit.price" form={form} set={set} errors={errors} instrument={instrument} required />
            <Field label="Exit time (your local time)" error={errors['exit.executed_at']}>
              <Input type="datetime-local" value={form.exit_time} onChange={(e) => set('exit_time', e.target.value)} required />
            </Field>
            <Field label="Exit quantity" error={errors['exit.quantity']} hint="Blank = whole position">
              <Input inputMode="decimal" value={form.exit_quantity} onChange={(e) => set('exit_quantity', e.target.value)} />
            </Field>
            <Field label="Exit fees & commissions ($)" error={errors['exit.fees']}>
              <Input inputMode="decimal" value={form.exit_fees} onChange={(e) => set('exit_fees', e.target.value)} placeholder="0.00" />
            </Field>
          </div>
        )}
      </Section>

      {/* ---------------- review ---------------- */}
      <Section title="Notes & review">
        <div className="grid gap-3 md:grid-cols-2">
          <Field label="Notes" error={errors.notes}>
            <TextArea value={form.notes} onChange={(e) => set('notes', e.target.value)} />
          </Field>
          <Field label="Post-trade reflection" error={errors.reflection}>
            <TextArea value={form.reflection} onChange={(e) => set('reflection', e.target.value)} placeholder="What went well? What would you change?" />
          </Field>
        </div>
      </Section>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={() => navigate(-1)}>Cancel</Button>
        <Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save trade'}</Button>
      </div>
    </form>
  )
}

// Fields that already display their own error next to the input.
const SHOWN_FIELDS = new Set([
  'portfolio_id', 'instrument_id', 'futures_contract_id', 'strategy_id', 'direction', 'planned_quantity',
  'planned_entry_price', 'initial_stop_price', 'current_stop_price', 'thesis', 'catalyst', 'notes', 'reflection',
  'exit', 'entry.price', 'entry.executed_at', 'entry.fees', 'exit.price', 'exit.executed_at', 'exit.quantity', 'exit.fees',
])

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </Card>
  )
}

function thirtySecondsHint(value: string, instrument?: Instrument): string | undefined {
  if (!instrument || instrument.price_format === 'decimal' || !value.trim()) return undefined
  const quoted = toThirtySeconds(value.trim(), instrument.price_format)
  return quoted ? `= ${quoted}` : 'Not on the 32nds grid'
}

type PriceKey = 'planned_entry_price' | 'initial_stop_price' | 'current_stop_price' | 'entry_price' | 'exit_price'

function PriceField(props: {
  label: string
  field: PriceKey
  errorKey?: string
  form: FormState
  set: <K extends keyof FormState>(key: K, value: FormState[K]) => void
  errors: Record<string, string>
  instrument?: Instrument
  disabled?: boolean
  required?: boolean
  hint?: string
}) {
  const value = props.form[props.field]
  return (
    <Field label={props.label} error={props.errors[props.errorKey ?? props.field]} hint={props.hint ?? thirtySecondsHint(value, props.instrument)}>
      <Input
        inputMode="decimal"
        value={value}
        onChange={(e) => props.set(props.field, e.target.value)}
        disabled={props.disabled}
        required={props.required}
      />
    </Field>
  )
}

function InstrumentSpec({ instrument: i }: { instrument: Instrument }) {
  if (i.asset_class === 'stock') {
    return <p className="mt-3 text-xs text-slate-500">Quoted in USD per share · P&amp;L = price change × shares.</p>
  }
  return (
    <p className="mt-3 text-xs text-slate-500">
      Quoted in {i.price_unit} · tick {trimDecimal(i.tick_size)} = ${trimDecimal(i.tick_value)} · ${Number(i.point_value).toLocaleString()} per 1.0 move
      {i.spec_verified_on && (
        <>
          {' · '}spec verified {i.spec_verified_on}
          {i.spec_source_url && (
            <> (<a href={i.spec_source_url} target="_blank" rel="noreferrer" className="underline">CME</a>)</>
          )}
        </>
      )}
    </p>
  )
}

function ContractPicker({ instrument, value, onChange, error }: {
  instrument?: Instrument
  value: string
  onChange: (id: string) => void
  error?: string
}) {
  const queryClient = useQueryClient()
  const contracts = useQuery({
    queryKey: ['contracts', instrument?.id],
    queryFn: () => listContracts(instrument!.id),
    enabled: Boolean(instrument),
  })
  const [adding, setAdding] = useState(false)
  const [month, setMonth] = useState('')
  const [expiration, setExpiration] = useState('')
  const add = useMutation({
    mutationFn: () => createContract(instrument!.id, { contract_month: month, expiration_date: expiration }),
    onSuccess: (contract) => {
      queryClient.invalidateQueries({ queryKey: ['contracts', instrument?.id] })
      onChange(String(contract.id))
      setAdding(false)
    },
  })
  const addErrors = fieldErrorMap(add.error)

  return (
    <div className="space-y-2">
      <Field label="Contract" error={error}>
        <Select value={value} onChange={(e) => onChange(e.target.value)} disabled={!instrument} required>
          <option value="">{!instrument ? 'Pick a product first' : contracts.data?.length === 0 ? 'None yet — add one' : 'Choose…'}</option>
          {contracts.data?.map((c) => (
            <option key={c.id} value={c.id}>{c.code} (exp. {c.expiration_date})</option>
          ))}
        </Select>
      </Field>
      {instrument && !adding && (
        <button type="button" className="text-xs font-medium text-slate-600 hover:underline" onClick={() => setAdding(true)}>
          + Add contract month
        </button>
      )}
      {instrument && adding && (
        <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-2">
          <Field label="Contract month" error={addErrors.contract_month}>
            <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
          </Field>
          <Field label="Last trading day" error={addErrors.expiration_date} hint="From the exchange's expiration calendar">
            <Input type="date" value={expiration} onChange={(e) => setExpiration(e.target.value)} />
          </Field>
          {add.isError && Object.keys(addErrors).length === 0 && <p className="text-xs text-red-600">{add.error.message}</p>}
          <div className="flex gap-2">
            <Button type="button" onClick={() => add.mutate()} disabled={!month || !expiration || add.isPending}>Add</Button>
            <Button type="button" variant="secondary" onClick={() => setAdding(false)}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  )
}

function AddStock({ onAdded }: { onAdded: (stock: Instrument) => void }) {
  const queryClient = useQueryClient()
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [open, setOpen] = useState(false)
  const add = useMutation({
    mutationFn: () => createStock({ symbol, name }),
    onSuccess: (stock) => {
      queryClient.invalidateQueries({ queryKey: ['instruments', 'stock'] })
      onAdded(stock)
      setOpen(false)
      setSymbol('')
      setName('')
    },
  })
  const errors = fieldErrorMap(add.error)

  if (!open) {
    return (
      <div className="flex items-end">
        <button type="button" className="pb-2 text-sm font-medium text-slate-600 hover:underline" onClick={() => setOpen(true)}>
          + Add a stock symbol
        </button>
      </div>
    )
  }
  return (
    <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-2">
      <Field label="Symbol" error={errors.symbol}>
        <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="AAPL" />
      </Field>
      <Field label="Company name" error={errors.name}>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Apple Inc." />
      </Field>
      {add.isError && Object.keys(errors).length === 0 && <p className="text-xs text-red-600">{add.error.message}</p>}
      <div className="flex gap-2">
        <Button type="button" onClick={() => add.mutate()} disabled={!symbol || !name || add.isPending}>Add</Button>
        <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </div>
  )
}
