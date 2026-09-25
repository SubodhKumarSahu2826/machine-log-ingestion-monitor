import React, { useState, useEffect, useCallback } from 'react';
import type { Incident, RecoveryAttempt, RecoveryAction, DiagnosticResult, Integration } from '../types';
import { StatusIndicator } from '../components/StatusIndicator';
import { DiagnosisPanel } from '../components/DiagnosisPanel';
import { RecoveryPanel } from '../components/RecoveryPanel';
import { RecoveryProof } from '../components/RecoveryProof';
import { formatDateTime } from '../utils/formatters';
import { api } from '../api/client';

interface IncidentPageProps {
  incidentId: number | null;
  incidents: Incident[];
  integrations: Integration[];
  onBack: () => void;
  onSelectIncident: (id: number) => void;
  onSelectIntegration: (id: number) => void;
}

export const IncidentPage: React.FC<IncidentPageProps> = ({
  incidentId,
  incidents,
  integrations,
  onBack,
  onSelectIncident,
  onSelectIntegration,
}) => {
  // Determine effective incident ID
  const effectiveIncidentId = incidentId ?? (incidents.length > 0 ? incidents[0].id : null);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [attempts, setAttempts] = useState<RecoveryAttempt[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ msg: string; type: 'success' | 'alert' | 'info' } | null>(null);

  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const fetchIncidentDetails = useCallback(async () => {
    if (!effectiveIncidentId) {
      setIsLoading(false);
      return;
    }
    try {
      const [inc, atts] = await Promise.all([
        api.getIncident(effectiveIncidentId),
        api.getRecoveryAttempts(effectiveIncidentId),
      ]);
      setIncident(inc);
      setAttempts(atts);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [effectiveIncidentId]);

  useEffect(() => {
    setIsLoading(true);
    fetchIncidentDetails();
    const interval = setInterval(fetchIncidentDetails, 3000);
    return () => clearInterval(interval);
  }, [fetchIncidentDetails]);

  const handleRunDiagnostics = async () => {
    if (!effectiveIncidentId) return;
    setIsDiagnosing(true);
    setNotification(null);
    try {
      const diag = await api.diagnoseIncident(effectiveIncidentId);
      setNotification({
        msg: `Diagnostic checks completed. Probable Cause: ${diag.probable_cause}`,
        type: 'info',
      });
      await fetchIncidentDetails();
    } catch (err: unknown) {
      setNotification({
        msg: `Diagnostic execution failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'alert',
      });
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleInitiateRecovery = async (action: RecoveryAction) => {
    if (!effectiveIncidentId) return;
    setIsRecovering(true);
    setNotification(null);
    try {
      await api.recoverIncident(effectiveIncidentId, action);
      setNotification({
        msg: `Recovery action ${action} dispatched. Incident moved to RECOVERING state.`,
        type: 'info',
      });
      await fetchIncidentDetails();
    } catch (err: unknown) {
      setNotification({
        msg: `Recovery dispatch failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'alert',
      });
    } finally {
      setIsRecovering(false);
    }
  };

  const handleVerifyRecovery = async () => {
    if (!effectiveIncidentId) return;
    setIsVerifying(true);
    setNotification(null);
    try {
      const res = await api.verifyRecovery(effectiveIncidentId);
      setNotification({
        msg: res.message,
        type: res.verified ? 'success' : 'alert',
      });
      await fetchIncidentDetails();
    } catch (err: unknown) {
      setNotification({
        msg: `Verification request failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'alert',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  if (!effectiveIncidentId || incidents.length === 0) {
    return (
      <div className="incident-page">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Incident Triage & Auto-Recovery Console</h2>
          </div>
          <div className="calm-status-banner" style={{ margin: '1rem 0' }}>
            <div className="calm-indicator-icon">✓</div>
            <div>
              <div className="calm-title">NO ACTIVE INCIDENTS</div>
              <div className="calm-subtitle">
                All machine streams are operating within healthy telemetry bounds. No triage required.
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading && !incident) {
    return <div className="page-loader">Loading incident workspace #{effectiveIncidentId}...</div>;
  }

  if (error && !incident) {
    return (
      <div className="error-panel">
        <div className="error-title">Failed to load incident #{effectiveIncidentId}</div>
        <div className="error-body">{error}</div>
        <button className="btn btn-secondary mt-2" onClick={onBack}>
          ← Back to Operations
        </button>
      </div>
    );
  }

  if (!incident) return null;

  const currentIntegration = integrations.find((i) => i.id === incident.integration_id);
  const isResolved = incident.state === 'RESOLVED';
  const successfulAttempt = attempts.find((a) => a.status === 'SUCCESS');

  return (
    <div className="incident-page">
      {/* Top Header / Breadcrumb & Incident Switcher */}
      <div className="incident-top-bar">
        <div className="breadcrumb-nav">
          <button className="btn btn-secondary btn-sm" onClick={onBack}>
            ← Operations
          </button>
          <span className="crumb-sep">/</span>
          <span
            className="crumb-link font-mono"
            onClick={() => onSelectIntegration(incident.integration_id)}
          >
            Stream #{incident.integration_id}
          </span>
          <span className="crumb-sep">/</span>
          <span className="crumb-current font-mono">Incident #{incident.id}</span>
        </div>

        {/* Quick Incident Switcher Dropdown */}
        {incidents.length > 1 && (
          <div className="incident-switcher">
            <label htmlFor="incident-select" className="control-label" style={{ margin: 0, whiteSpace: 'nowrap' }}>
              Switch Incident:
            </label>
            <select
              id="incident-select"
              className="form-select form-select-sm"
              value={incident.id}
              onChange={(e) => onSelectIncident(Number(e.target.value))}
            >
              {incidents.map((inc) => (
                <option key={inc.id} value={inc.id}>
                  #{inc.id} — Stream #{inc.integration_id} ({inc.state})
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="header-status-box">
          <span className="header-label">CURRENT STATE:</span>
          <StatusIndicator type="incident" status={incident.state} />
        </div>
      </div>

      {notification && (
        <div className={`notification-banner banner-${notification.type}`}>
          {notification.msg}
        </div>
      )}

      {/* Incident Specifications Overview */}
      <div className="incident-meta-grid">
        <div className="meta-card">
          <span className="meta-card-label">INCIDENT ID</span>
          <span className="meta-card-value font-mono">#{incident.id}</span>
          <span className="meta-card-sub font-mono">
            Created: {formatDateTime(incident.created_at)}
          </span>
        </div>

        <div className="meta-card">
          <span className="meta-card-label">STREAM & MACHINE</span>
          <span
            className="meta-card-value font-mono link-title"
            onClick={() => onSelectIntegration(incident.integration_id)}
          >
            {currentIntegration?.name || `Integration #${incident.integration_id}`}
          </span>
          <span className="meta-card-sub font-mono">
            Machine #{currentIntegration?.machine_id || '—'} ({currentIntegration?.type || 'API'})
          </span>
        </div>

        <div className="meta-card">
          <span className="meta-card-label">EXPECTED INTERVAL</span>
          <span className="meta-card-value font-mono">
            {currentIntegration?.expected_interval_seconds || 30}s
          </span>
          <span className="meta-card-sub font-mono">
            Stale threshold: {currentIntegration?.stale_threshold_seconds || 120}s
          </span>
        </div>

        <div className="meta-card">
          <span className="meta-card-label">LATEST TELEMETRY</span>
          <span className="meta-card-value font-mono">
            {formatDateTime(currentIntegration?.last_seen_at)}
          </span>
          <span className="meta-card-sub font-mono">
            {isResolved ? `Resolved: ${formatDateTime(incident.resolved_at)}` : 'Stream interrupted'}
          </span>
        </div>
      </div>

      {/* 1. Diagnostics Panel */}
      <DiagnosisPanel
        diagnostic={incident.diagnostic_details as DiagnosticResult | null}
        onRunDiagnostics={handleRunDiagnostics}
        isRunning={isDiagnosing}
        isResolved={isResolved}
      />

      {/* 2. Recovery Panel */}
      <RecoveryPanel
        incident={incident}
        attempts={attempts}
        onInitiateRecovery={handleInitiateRecovery}
        onVerifyRecovery={handleVerifyRecovery}
        isRecovering={isRecovering}
        isVerifying={isVerifying}
      />

      {/* 3. Verification Proof (Displayed upon confirmed resolution) */}
      <RecoveryProof
        incident={incident}
        successfulAttempt={successfulAttempt}
        integration={currentIntegration}
      />
    </div>
  );
};
