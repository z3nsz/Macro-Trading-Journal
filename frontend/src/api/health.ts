import { apiGet } from './client'

// Mirrors HealthResponse in backend/app/api/health.py.
export interface HealthResponse {
  status: string
  app: string
  environment: string
  server_time: string // ISO-8601 timestamp in UTC
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>('/health')
}
