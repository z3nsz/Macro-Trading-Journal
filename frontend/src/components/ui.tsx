// Small reusable UI pieces so every page looks and behaves the same.

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { ApiError } from '../api/client'
import type { TradeStatus } from '../api/types'
import { STATUS_LABELS } from '../lib/format'

type ButtonVariant = 'primary' | 'secondary' | 'danger'

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-400',
  secondary: 'border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 disabled:text-slate-400',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
}

export function Button({ variant = 'primary', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${BUTTON_STYLES[variant]} ${className}`}
      {...props}
    />
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-slate-200 bg-white p-4 sm:p-5 ${className}`}>{children}</div>
}

/** Label + input + hint + error message, stacked. */
export function Field({ label, error, hint, children, className = '' }: {
  label: string
  error?: string
  hint?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <label className={`block text-sm ${className}`}>
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs font-medium text-red-600">{error}</span>}
    </label>
  )
}

const INPUT_STYLE =
  'block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 disabled:bg-slate-100 disabled:text-slate-500'

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={INPUT_STYLE} {...props} />
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={INPUT_STYLE} {...props} />
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={INPUT_STYLE} rows={3} {...props} />
}

const STATUS_STYLES: Record<TradeStatus, string> = {
  planned: 'bg-slate-100 text-slate-700',
  open: 'bg-blue-100 text-blue-800',
  partially_closed: 'bg-amber-100 text-amber-800',
  closed: 'bg-emerald-100 text-emerald-800',
}

export function StatusBadge({ status }: { status: TradeStatus }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}>{STATUS_LABELS[status]}</span>
}

export function DirectionBadge({ direction }: { direction: 'long' | 'short' }) {
  const style = direction === 'long' ? 'text-emerald-700' : 'text-red-700'
  return <span className={`text-xs font-semibold uppercase ${style}`}>{direction}</span>
}

export function AccountTypeBadge({ type }: { type: 'simulated' | 'real' }) {
  const style = type === 'real' ? 'bg-violet-100 text-violet-800' : 'bg-slate-100 text-slate-600'
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${style}`}>{type === 'real' ? 'Real' : 'Simulated'}</span>
}

export function Loading({ what = 'Loading' }: { what?: string }) {
  return <p className="py-8 text-center text-sm text-slate-500">{what}…</p>
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  const fieldErrors = error instanceof ApiError ? error.fieldErrors : []
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert">
      <p className="font-semibold">{message}</p>
      {fieldErrors.length > 0 && (
        <ul className="mt-1 list-disc pl-5">
          {fieldErrors.map((e, i) => (
            <li key={i}>{e.field ? `${e.field}: ` : ''}{e.message}</li>
          ))}
        </ul>
      )}
      {onRetry && (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-10 text-center">
      <p className="font-medium text-slate-700">{title}</p>
      {children && <div className="mt-2 text-sm text-slate-500">{children}</div>}
    </div>
  )
}
