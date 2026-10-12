import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { createPortfolio, createStrategy, deletePortfolio, listPortfolios, listStrategies } from '../api/journal'
import type { AccountType } from '../api/types'
import { fieldErrorMap } from '../lib/errors'
import { formatMoney } from '../lib/format'
import { AccountTypeBadge, Button, Card, EmptyState, ErrorBox, Field, Input, Loading, Select } from '../components/ui'

export function SetupPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <PortfoliosSection />
      <StrategiesSection />
    </div>
  )
}

function PortfoliosSection() {
  const queryClient = useQueryClient()
  const portfolios = useQuery({ queryKey: ['portfolios'], queryFn: listPortfolios })

  const [name, setName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('simulated')
  const [capital, setCapital] = useState('')

  const create = useMutation({
    mutationFn: createPortfolio,
    onSuccess: () => {
      setName('')
      setCapital('')
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })

  const remove = useMutation({
    mutationFn: deletePortfolio,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['trades'] })
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser's default full-page form submission
    create.mutate({ name, account_type: accountType, starting_capital: capital || '0' })
  }

  const errors = fieldErrorMap(create.error)

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Portfolios</h2>

      {portfolios.isPending && <Loading what="Loading portfolios" />}
      {portfolios.isError && <ErrorBox error={portfolios.error} onRetry={() => portfolios.refetch()} />}
      {portfolios.data?.length === 0 && (
        <EmptyState title="No portfolios yet">Create one below, e.g. “CME Competition”.</EmptyState>
      )}

      {portfolios.data && portfolios.data.length > 0 && (
        <ul className="space-y-2">
          {portfolios.data.map((p) => (
            <li key={p.id}>
              <Card className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {p.name} <AccountTypeBadge type={p.account_type} />
                  </p>
                  <p className="text-sm text-slate-500">
                    Starting capital: {formatMoney(p.starting_capital)} {p.currency}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (confirm(`Delete “${p.name}” and ALL of its trades? This cannot be undone.`)) remove.mutate(p.id)
                  }}
                >
                  Delete
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}
      {remove.isError && <ErrorBox error={remove.error} />}

      <Card>
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-3">
          <Field label="Name" error={errors.name} className="sm:col-span-3">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CME Competition" required />
          </Field>
          <Field label="Type" error={errors.account_type}>
            <Select value={accountType} onChange={(e) => setAccountType(e.target.value as AccountType)}>
              <option value="simulated">Simulated</option>
              <option value="real">Real money</option>
            </Select>
          </Field>
          <Field label="Starting capital (USD)" error={errors.starting_capital} className="sm:col-span-2">
            <Input inputMode="decimal" value={capital} onChange={(e) => setCapital(e.target.value)} placeholder="100000" />
          </Field>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Creating…' : 'Create portfolio'}
            </Button>
          </div>
          {create.isError && Object.keys(errors).length === 0 && (
            <div className="sm:col-span-3">
              <ErrorBox error={create.error} />
            </div>
          )}
        </form>
      </Card>
      <p className="text-xs text-slate-500">Deposits and withdrawals will be recorded separately from trading P&amp;L in a later milestone.</p>
    </section>
  )
}

function StrategiesSection() {
  const queryClient = useQueryClient()
  const strategies = useQuery({ queryKey: ['strategies'], queryFn: listStrategies })
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const create = useMutation({
    mutationFn: createStrategy,
    onSuccess: () => {
      setName('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
  const errors = fieldErrorMap(create.error)

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">Strategies</h2>
      {strategies.isPending && <Loading what="Loading strategies" />}
      {strategies.isError && <ErrorBox error={strategies.error} onRetry={() => strategies.refetch()} />}
      {strategies.data?.length === 0 && (
        <EmptyState title="No strategies yet">Examples: “Opening range breakout”, “CPI fade”.</EmptyState>
      )}
      {strategies.data && strategies.data.length > 0 && (
        <ul className="space-y-2">
          {strategies.data.map((s) => (
            <li key={s.id}>
              <Card>
                <p className="font-medium">{s.name}</p>
                {s.description && <p className="text-sm text-slate-500">{s.description}</p>}
              </Card>
            </li>
          ))}
        </ul>
      )}
      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate({ name, description: description || null })
          }}
          className="space-y-3"
        >
          <Field label="Strategy name" error={errors.name}>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Opening range breakout" required />
          </Field>
          <Field label="Description (optional)" error={errors.description}>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? 'Adding…' : 'Add strategy'}
          </Button>
          {create.isError && Object.keys(errors).length === 0 && <ErrorBox error={create.error} />}
        </form>
      </Card>
      <p className="text-xs text-slate-500">Editing strategies and per-strategy statistics come in Phase 7.</p>
    </section>
  )
}
