export interface ApiResponse<T> {
  data: T
  requestId: string
}

export interface ApiErrorDetail {
  row?: number | null
  field?: string | null
  code: string
  message: string
}

export interface ApiErrorBody {
  status: number
  code: string
  message: string
  field?: string | null
  details: ApiErrorDetail[]
}

export interface ApiErrorResponse {
  error: ApiErrorBody
  requestId: string
}

export interface ApiClientErrorOptions {
  status?: number
  code: string
  field?: string | null
  details?: ApiErrorDetail[]
  requestId?: string
  cause?: unknown
}

export class ApiClientError extends Error {
  readonly status?: number
  readonly code: string
  readonly field?: string | null
  readonly details: ApiErrorDetail[]
  readonly requestId?: string
  readonly cause?: unknown

  constructor(message: string, options: ApiClientErrorOptions) {
    super(message)
    this.name = 'ApiClientError'
    this.status = options.status
    this.code = options.code
    this.field = options.field
    this.details = options.details ?? []
    this.requestId = options.requestId
    this.cause = options.cause
    Object.setPrototypeOf(this, ApiClientError.prototype)
  }
}
