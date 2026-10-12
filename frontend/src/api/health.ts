import { apiGet } from './client'

// Mirrors HealthResponse in backend/app/api/health.py.
export interface HealthResponse {
  status: 'ok' | 'degraded'
  app: string
  environment: string
  database: 'connected' | 'unavailable'
  server_time: string // ISO-8601 timestamp in UTC
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>('/health')
}
