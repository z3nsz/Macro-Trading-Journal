import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/health'

/** Small indicator in the header: is the backend up, and can it reach the database? */
export function BackendStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: false,
    refetchInterval: 15_000,
  })

  let dot = 'bg-slate-300'
  let label = 'Checking…'
  if (isError) {
    dot = 'bg-red-500'
    label = 'Backend offline'
  } else if (!isPending && data.database !== 'connected') {
    dot = 'bg-amber-500'
    label = 'Database unavailable'
  } else if (!isPending) {
    dot = 'bg-emerald-500'
    label = 'Connected'
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500" title={label}>
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      <span className="hidden sm:inline">{label}</span>
    </span>
  )
}
