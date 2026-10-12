import { ApiError } from '../api/client'

/** Turns an API error into {field: message} so forms can show errors next to inputs. */
export function fieldErrorMap(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {}
  const map: Record<string, string> = {}
  for (const e of error.fieldErrors) map[e.field] ??= e.message
  return map
}
