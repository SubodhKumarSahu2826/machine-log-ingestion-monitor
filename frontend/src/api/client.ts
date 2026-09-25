import type {
  Incident,
  Integration,
  DiagnosticResult,
  RecoveryResponse,
  VerificationResponse,
  RecoveryAttempt,
  RecoveryAction,
  MachineEventPayload,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMessage = `Request failed with status ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson && errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to text status
      }
      throw new ApiError(errorMessage, res.status);
    }
    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error or backend unavailable',
      0
    );
  }
}

export const api = {
  checkHealth: () => request<{ status: string }>('/health'),

  getIntegrations: () => request<Integration[]>('/api/v1/integrations'),

  getIntegration: (id: number) => request<Integration>(`/api/v1/integrations/${id}`),

  getIncidents: (params?: { integration_id?: number; state?: string }) => {
    const query = new URLSearchParams();
    if (params?.integration_id !== undefined) {
      query.set('integration_id', String(params.integration_id));
    }
    if (params?.state) {
      query.set('state', params.state);
    }
    const qStr = query.toString();
    return request<Incident[]>(`/api/v1/incidents${qStr ? `?${qStr}` : ''}`);
  },

  getIncident: (id: number) => request<Incident>(`/api/v1/incidents/${id}`),

  diagnoseIncident: (incidentId: number) =>
    request<DiagnosticResult>(`/api/v1/incidents/${incidentId}/diagnose`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  recoverIncident: (incidentId: number, action: RecoveryAction, timeoutSeconds?: number) =>
    request<RecoveryResponse>(`/api/v1/incidents/${incidentId}/recover`, {
      method: 'POST',
      body: JSON.stringify({
        action,
        timeout_seconds: timeoutSeconds,
      }),
    }),

  verifyRecovery: (incidentId: number) =>
    request<VerificationResponse>(`/api/v1/incidents/${incidentId}/verify`, {
      method: 'POST',
    }),

  getRecoveryAttempts: (incidentId: number) =>
    request<RecoveryAttempt[]>(`/api/v1/incidents/${incidentId}/recovery-attempts`),

  sendEvent: (payload: MachineEventPayload) =>
    request<{ status: string; event_id: string; received_at: string; message: string }>(
      '/api/v1/events',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
};
