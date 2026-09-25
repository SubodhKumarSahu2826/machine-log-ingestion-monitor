import React, { useState, useEffect, useCallback } from 'react';
import type { Incident, RecoveryAttempt, RecoveryAction, DiagnosticResult } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { DiagnosticChecks } from '../components/DiagnosticChecks';
import { RecoveryAttempts } from '../components/RecoveryAttempts';
import { RecoveryActionDialog } from '../components/RecoveryActionDialog';
import { Timeline } from '../components/Timeline';
import { formatDateTime } from '../utils/formatters';
import { api } from '../api/client';

interface IncidentDetailPageProps {
  incidentId: number;
  onBack: () => void;
  onSelectIntegration: (id: number) => void;
}

export const IncidentDetailPage: React.FC<IncidentDetailPageProps> = ({
  incidentId,
  onBack,
  onSelectIntegration,
}) => {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [attempts, setAttempts] = useState<RecoveryAttempt[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'danger' | 'info' } | null>(null);

  // Action states
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [isRecovering, setIsRecovering] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isRecoveryModalOpen, setIsRecoveryModalOpen] = useState(false);

  const fetchIncidentData = useCallback(async () => {
    try {
      setError(null);
      const [incData, attData] = await Promise.all([
        api.getIncident(incidentId),
        api.getRecoveryAttempts(incidentId),
      ]);
      setIncident(incData);
      setAttempts(attData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    fetchIncidentData();
    const interval = setInterval(fetchIncidentData, 3000);
    return () => clearInterval(interval);
  }, [fetchIncidentData]);

  const handleRunDiagnostics = async () => {
    setIsDiagnosing(true);
    setActionMessage(null);
    try {
      const diag = await api.diagnoseIncident(incidentId);
      setActionMessage({
        text: `Diagnostics completed: Probable Cause is ${diag.probable_cause}`,
        type: 'info',
      });
      await fetchIncidentData();
    } catch (err: unknown) {
      setActionMessage({
        text: `Diagnostic execution failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'danger',
      });
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleInitiateRecovery = async (action: RecoveryAction) => {
    setIsRecovering(true);
    setActionMessage(null);
    try {
      const res = await api.recoverIncident(incidentId, action);
      setActionMessage({
        text: res.message,
        type: 'info',
      });
      setIsRecoveryModalOpen(false);
      await fetchIncidentData();
    } catch (err: unknown) {
      setActionMessage({
        text: `Recovery initiation failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'danger',
      });
    } finally {
      setIsRecovering(false);
    }
  };

  const handleVerifyRecovery = async () => {
    setIsVerifying(true);
    setActionMessage(null);
    try {
      const res = await api.verifyRecovery(incidentId);
      setActionMessage({
        text: res.message,
        type: res.verified ? 'success' : 'danger',
      });
      await fetchIncidentData();
    } catch (err: unknown) {
      setActionMessage({
        text: `Verification request failed: ${err instanceof Error ? err.message : String(err)}`,
        type: 'danger',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  if (isLoading && !incident) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
        <span className="spinner" style={{ display: 'inline-block', marginBottom: '0.75rem' }} />
        <div>Loading Incident #{incidentId}...</div>
      </div>
    );
  }

  if (error && !incident) {
    return (
      <div style={{ padding: '2rem' }}>
        <div className="alert-banner alert-danger">
          Error loading incident: {error}
        </div>
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  if (!incident) return null;

  const isResolved = incident.state === 'RESOLVED';
  const isEscalated = incident.state === 'ESCALATED';
  const isRecoveringState = incident.state === 'RECOVERING';
  const canRecover = !isResolved && !isEscalated && !isRecoveringState;
  const canVerify = isRecoveringState;

  return (
    <div>
      {/* Top Breadcrumb & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button className="btn btn-secondary" onClick={onBack}>
            ← Back
          </button>
          <span style={{ color: 'var(--text-dim)' }}>/</span>
          <span
            onClick={() => onSelectIntegration(incident.integration_id)}
            style={{ color: '#38bdf8', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
          >
            Integration #{incident.integration_id}
          </span>
          <span style={{ color: 'var(--text-dim)' }}>/</span>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            Incident #{incident.id}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="btn btn-secondary"
            onClick={handleRunDiagnostics}
            disabled={isDiagnosing || isResolved}
          >
            {isDiagnosing ? <span className="spinner" /> : 'Run Diagnostics'}
          </button>

          <button
            className="btn btn-primary"
            onClick={() => setIsRecoveryModalOpen(true)}
            disabled={!canRecover || isRecovering}
          >
            Initiate Recovery
          </button>

          <button
            className="btn btn-success"
            onClick={handleVerifyRecovery}
            disabled={!canVerify || isVerifying}
          >
            {isVerifying ? (
              <>
                <span className="spinner" /> Verifying...
              </>
            ) : (
              'Verify Telemetry'
            )}
          </button>

          <button className="btn btn-secondary" onClick={fetchIncidentData}>
            ↻
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className={`alert-banner alert-${actionMessage.type}`}>
          {actionMessage.text}
        </div>
      )}

      {/* Incident Header Panel */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Incident #{incident.id} Workspace</span>
          </div>
          <div>
            <StatusBadge type="incident" status={incident.state} />
          </div>
        </div>

        <div className="panel-body">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1.25rem',
            }}
          >
            <div>
              <div className="form-label">Incident Lifecycle</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Created: <strong>{formatDateTime(incident.created_at)}</strong>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                Resolved: <strong>{formatDateTime(incident.resolved_at)}</strong>
              </div>
            </div>

            <div>
              <div className="form-label">Associated Integration</div>
              <div
                onClick={() => onSelectIntegration(incident.integration_id)}
                style={{
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  color: '#38bdf8',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                Integration #{incident.integration_id}
              </div>
            </div>

            <div>
              <div className="form-label">Probable Cause</div>
              <div
                style={{
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  color: incident.probable_cause?.includes('OFFLINE') ? '#f43f5e' : '#f59e0b',
                }}
              >
                {incident.probable_cause || 'Awaiting Diagnostic Evaluation'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recovery Timeline Flow */}
      <Timeline
        currentState={incident.state}
        createdAt={incident.created_at}
        resolvedAt={incident.resolved_at}
        attempts={attempts}
      />

      {/* Diagnostic Engine Panel */}
      <DiagnosticChecks
        diagnostic={incident.diagnostic_details as DiagnosticResult | null}
        onRunDiagnostics={!isResolved ? handleRunDiagnostics : undefined}
        isRunning={isDiagnosing}
      />

      {/* Recovery Attempts Table */}
      <RecoveryAttempts attempts={attempts} />

      {/* Modal Dialog for Recovery Action */}
      <RecoveryActionDialog
        isOpen={isRecoveryModalOpen}
        onClose={() => setIsRecoveryModalOpen(false)}
        onConfirm={handleInitiateRecovery}
        isSubmitting={isRecovering}
        incidentId={incident.id}
      />
    </div>
  );
};
