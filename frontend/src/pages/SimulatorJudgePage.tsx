import React, { useState } from 'react';
import type { Integration } from '../types';
import { api } from '../api/client';

interface SimulatorJudgePageProps {
  integrations: Integration[];
  onSelectIntegration: (id: number) => void;
}

type ScenarioType = 'NORMAL' | 'SILENT' | 'RECOVER_AFTER_RETRY' | 'PERMANENT_FAILURE';

const SCENARIOS: { type: ScenarioType; name: string; desc: string; expectedOutcome: string }[] = [
  {
    type: 'NORMAL',
    name: 'Normal Continuous Telemetry',
    desc: 'Continuously generates valid cycle events every second, maintaining HEALTHY state.',
    expectedOutcome: 'Integration stays HEALTHY, last_seen_at advances steadily, no incidents created.',
  },
  {
    type: 'SILENT',
    name: 'Silent Sensor Interruption',
    desc: 'Emits 3 initial events then abruptly halts all transmission.',
    expectedOutcome: 'Freshness exceeds threshold → Integration becomes STALE → Single active Incident is opened.',
  },
  {
    type: 'RECOVER_AFTER_RETRY',
    name: 'Controlled Auto-Recovery (Scenario A)',
    desc: 'Goes silent until an incident enters RECOVERING, then automatically resumes emitting events.',
    expectedOutcome: 'Incident detected → Recovery action executed → New event received → Verification succeeds → Incident RESOLVED.',
  },
  {
    type: 'PERMANENT_FAILURE',
    name: 'Permanent Hardware Failure (Scenario B)',
    desc: 'Hardware is dead; no events arrive despite repeated recovery attempts.',
    expectedOutcome: '3 recovery attempts fail verification → Incident ESCALATED → Integration marked FAILED.',
  },
];

export const SimulatorJudgePage: React.FC<SimulatorJudgePageProps> = ({
  integrations,
  onSelectIntegration,
}) => {
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<number>(
    integrations[0]?.id || 1
  );
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('RECOVER_AFTER_RETRY');

  const [isSending, setIsSending] = useState(false);
  const [eventLogs, setEventLogs] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  const selectedIntegration = integrations.find((i) => i.id === selectedIntegrationId);
  const machineId = selectedIntegration?.machine_id || 1;

  const cliCommand = `python -m simulator.machine_simulator --scenario ${selectedScenario} --integration-id ${selectedIntegrationId} --machine-id ${machineId}`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(cliCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSendManualEvent = async (count: number = 1) => {
    setIsSending(true);
    const newLogs: string[] = [];

    for (let i = 0; i < count; i++) {
      const eventId = `manual-sim-${Date.now()}-${i + 1}`;
      try {
        const res = await api.sendEvent({
          event_id: eventId,
          machine_id: machineId,
          integration_id: selectedIntegrationId,
          event_type: 'cycle_completed',
          occurred_at: new Date().toISOString(),
          payload: {
            result: 'PASS',
            cycle_count: i + 1,
            cycle_time_ms: 1800,
          },
        });
        newLogs.push(`[${new Date().toLocaleTimeString()}] Event ${res.event_id} -> HTTP 201 (persisted)`);
      } catch (err: unknown) {
        newLogs.push(
          `[${new Date().toLocaleTimeString()}] Event ${eventId} ERROR: ${
            err instanceof Error ? err.message : String(err)
          }`
        );
      }
    }

    setEventLogs((prev) => [...newLogs, ...prev].slice(0, 20));
    setIsSending(false);
  };

  return (
    <div>
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Simulator & Demonstration Console (Judge Mode)</span>
          </div>
        </div>

        <div className="panel-body">
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            Demonstrate and validate the closed-loop recovery workflow (DETECT → DIAGNOSE → RECOVER → VERIFY → RESOLVE/ESCALATE).
            The simulator operates strictly as an external client communicating via HTTP (<code>POST /api/v1/events</code>).
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1.25rem',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <label className="form-label">Target Integration</label>
              <select
                className="form-select"
                value={selectedIntegrationId}
                onChange={(e) => setSelectedIntegrationId(Number(e.target.value))}
              >
                {integrations.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} (ID: {i.id}, Machine #{i.machine_id}, State: {i.health_state})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="form-label">Simulation Scenario</label>
              <select
                className="form-select"
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value as ScenarioType)}
              >
                {SCENARIOS.map((s) => (
                  <option key={s.type} value={s.type}>
                    {s.type} — {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Scenario Details */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '1rem',
              marginBottom: '1.5rem',
            }}
          >
            {SCENARIOS.filter((s) => s.type === selectedScenario).map((s) => (
              <div key={s.type}>
                <div style={{ fontWeight: 600, color: '#38bdf8', marginBottom: '0.3rem' }}>
                  {s.name}
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                  <strong>Description:</strong> {s.desc}
                </div>
                <div style={{ fontSize: '0.82rem', color: '#34d399' }}>
                  <strong>Expected Outcome:</strong> {s.expectedOutcome}
                </div>
              </div>
            ))}
          </div>

          {/* Terminal Command Box */}
          <div className="form-group">
            <label className="form-label">Run Simulator From Terminal</label>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                background: '#040711',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '0.5rem 0.75rem',
                gap: '0.5rem',
              }}
            >
              <code style={{ flex: 1, color: '#38bdf8', fontSize: '0.82rem' }}>{cliCommand}</code>
              <button className="btn btn-secondary btn-sm" onClick={copyToClipboard}>
                {copied ? '✓ Copied' : 'Copy Command'}
              </button>
            </div>
          </div>

          {/* Direct Telemetry Injection for Fast In-Browser Evaluation */}
          <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              Interactive Browser Telemetry Emitter (POST /api/v1/events)
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.85rem' }}>
              Trigger actual HTTP telemetry events directly from the dashboard to evaluate ingestion and verify recovery without opening a terminal window.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
              <button
                className="btn btn-primary"
                onClick={() => handleSendManualEvent(1)}
                disabled={isSending}
              >
                Send Single Cycle Event
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => handleSendManualEvent(3)}
                disabled={isSending}
              >
                Send 3-Event Burst
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => onSelectIntegration(selectedIntegrationId)}
              >
                Inspect Integration #{selectedIntegrationId} →
              </button>
            </div>

            {eventLogs.length > 0 && (
              <div
                style={{
                  background: '#040711',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  maxHeight: '150px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                }}
              >
                {eventLogs.map((log, i) => (
                  <div key={i}>{log}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
