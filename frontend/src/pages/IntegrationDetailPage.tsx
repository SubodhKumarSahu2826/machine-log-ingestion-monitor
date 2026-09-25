import React, { useState } from 'react';
import type { Integration, Incident } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { formatDateTime, formatFreshness } from '../utils/formatters';
import { api } from '../api/client';

interface IntegrationDetailPageProps {
  integration: Integration;
  activeIncident: Incident | null;
  onBack: () => void;
  onSelectIncident: (id: number) => void;
  onRefresh: () => void;
}

export const IntegrationDetailPage: React.FC<IntegrationDetailPageProps> = ({
  integration,
  activeIncident,
  onBack,
  onSelectIncident,
  onRefresh,
}) => {
  const [isSendingEvent, setIsSendingEvent] = useState(false);
  const [eventMessage, setEventMessage] = useState<string | null>(null);

  const freshness = formatFreshness(integration.last_seen_at);

  const handleSendTestEvent = async () => {
    setIsSendingEvent(true);
    setEventMessage(null);
    try {
      const resp = await api.sendEvent({
        event_id: `manual-${Date.now()}`,
        machine_id: integration.machine_id,
        integration_id: integration.id,
        event_type: 'cycle_completed',
        occurred_at: new Date().toISOString(),
        payload: {
          result: 'PASS',
          manual_trigger: true,
          cycle_time_ms: 1850,
        },
      });
      setEventMessage(`Event ${resp.event_id} accepted: ${resp.message}`);
      onRefresh();
    } catch (err: unknown) {
      setEventMessage(
        `Failed to send event: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      setIsSendingEvent(false);
    }
  };

  return (
    <div>
      {/* Top action bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back to Dashboard
        </button>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" onClick={onRefresh}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {eventMessage && (
        <div
          className={`alert-banner ${eventMessage.includes('Failed') ? 'alert-danger' : 'alert-success'}`}
        >
          {eventMessage}
        </div>
      )}

      {/* Header Panel */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>{integration.name}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 400 }}>
              (Integration #{integration.id})
            </span>
          </div>
          <div>
            <StatusBadge type="health" status={integration.health_state} />
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
              <div className="form-label">Stream Configuration</div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                Protocol / Adapter: {integration.type}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                Machine Association: Machine #{integration.machine_id}
              </div>
            </div>

            <div>
              <div className="form-label">Telemetry Freshness</div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8' }}>
                {freshness.text}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                Last seen: {formatDateTime(integration.last_seen_at)}
              </div>
            </div>

            <div>
              <div className="form-label">Monitoring Thresholds</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                • Expected Interval: <strong>{integration.expected_interval_seconds || 30}s</strong>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                • Warning Threshold: <strong>{integration.warning_threshold_seconds || 60}s</strong>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                • Stale Threshold: <strong>{integration.stale_threshold_seconds || 120}s</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Incident Alert */}
      {activeIncident ? (
        <div className="panel" style={{ borderColor: 'rgba(245, 158, 11, 0.4)' }}>
          <div className="panel-header" style={{ background: 'rgba(245, 158, 11, 0.1)' }}>
            <div className="panel-title" style={{ color: '#fbbf24' }}>
              <span>Active Incident Detected</span>
              <StatusBadge type="incident" status={activeIncident.state} />
            </div>
            <button
              className="btn btn-warning btn-sm"
              onClick={() => onSelectIncident(activeIncident.id)}
            >
              Open Incident Workspace #{activeIncident.id} →
            </button>
          </div>
          <div className="panel-body">
            <div style={{ fontSize: '0.85rem', color: '#f8fafc', marginBottom: '0.5rem' }}>
              <strong>Probable Cause:</strong> {activeIncident.probable_cause || 'Investigating...'}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Created: {formatDateTime(activeIncident.created_at)}
            </div>
          </div>
        </div>
      ) : (
        <div className="panel" style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}>
          <div className="panel-body" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ color: '#34d399', fontSize: '1.25rem' }}>✓</span>
            <div>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.9rem' }}>
                No active incidents
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Telemetry data is flowing within acceptable threshold bounds.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Telemetry Test Actions */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Direct Telemetry Control</span>
          </div>
        </div>
        <div className="panel-body">
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Trigger an instantaneous machine event directly to <code>POST /api/v1/events</code> to
            verify ingestion pipeline responsiveness and advance <code>last_seen_at</code>.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleSendTestEvent}
            disabled={isSendingEvent}
          >
            {isSendingEvent ? (
              <>
                <span className="spinner" /> Emitting Telemetry Event...
              </>
            ) : (
              'Emit Valid Cycle Event'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
