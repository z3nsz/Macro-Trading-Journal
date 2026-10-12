import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/health'

export function BackendStatus() {
  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: false,
    refetchInterval: 10_000, // re-check every 10 s so the card reacts if the backend stops
  })

  if (isPending) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-slate-500">
        Checking backend connection…
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-5">
        <p className="font-semibold text-red-700">Backend not reachable</p>
        <p className="mt-1 text-sm text-red-600">{error.message}</p>
        <p className="mt-1 text-sm text-red-600">
          Is the FastAPI server running on port 8000?
        </p>
        <button
          onClick={() => refetch()}
          className="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        >
          {isFetching ? 'Retrying…' : 'Retry'}
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5">
      <p className="font-semibold text-emerald-700">Backend connected</p>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm text-emerald-900">
        <dt className="text-emerald-700">App</dt>
        <dd>{data.app}</dd>
        <dt className="text-emerald-700">Environment</dt>
        <dd>{data.environment}</dd>
        <dt className="text-emerald-700">Server time</dt>
        <dd>{new Date(data.server_time).toLocaleString()}</dd>
      </dl>
    </div>
  )
}
