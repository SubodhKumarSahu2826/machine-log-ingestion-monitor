export type HealthState = 'HEALTHY' | 'WARNING' | 'STALE' | 'RECOVERING' | 'FAILED';

export type IncidentState =
  | 'DETECTED'
  | 'OPEN'
  | 'INVESTIGATING'
  | 'RECOVERING'
  | 'VERIFIED'
  | 'RESOLVED'
  | 'FAILED'
  | 'ESCALATED';

export type RecoveryAction = 'RETRY_CONNECTION' | 'RECONNECT_CONNECTOR' | 'REPLAY_EVENTS';

export type CheckStatus = 'PASS' | 'FAIL' | 'UNKNOWN';

export interface Integration {
  id: number;
  machine_id: number;
  name: string;
  type: string;
  health_state: HealthState;
  last_seen_at: string | null;
  expected_interval_seconds: number | null;
  warning_threshold_seconds: number | null;
  stale_threshold_seconds: number | null;
}

export interface DiagnosticCheckItem {
  status: CheckStatus;
  details: string;
}

export interface DiagnosticChecks {
  machine_heartbeat: DiagnosticCheckItem;
  network: DiagnosticCheckItem;
  connector: DiagnosticCheckItem;
  authentication: DiagnosticCheckItem;
  parser: DiagnosticCheckItem;
  ingestion: DiagnosticCheckItem;
}

export interface DiagnosticResult {
  incident_id: number;
  integration_id: number;
  evaluated_at: string;
  checks: DiagnosticChecks;
  probable_cause: string;
  explanation: string;
}

export interface Incident {
  id: number;
  integration_id: number;
  state: IncidentState;
  probable_cause: string | null;
  diagnostic_details: DiagnosticResult | null;
  created_at: string;
  resolved_at: string | null;
}

export interface RecoveryAttempt {
  id: number;
  incident_id: number;
  action: string;
  status: 'STARTED' | 'SUCCESS' | 'FAILURE';
  attempted_at: string;
  completed_at: string | null;
  result_message: string | null;
}

export interface RecoveryResponse {
  incident_id: number;
  integration_id: number;
  incident_state: IncidentState;
  attempt: RecoveryAttempt;
  message: string;
}

export interface VerificationResponse {
  incident_id: number;
  integration_id: number;
  incident_state: IncidentState;
  verified: boolean;
  message: string;
  attempt: RecoveryAttempt | null;
}

export interface MachineEventPayload {
  event_id: string;
  machine_id: number;
  integration_id: number;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}
