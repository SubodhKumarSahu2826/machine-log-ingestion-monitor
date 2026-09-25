import React, { useState } from 'react';
import type { Integration } from '../types';
import { api } from '../api/client';
import { StatusIndicator } from '../components/StatusIndicator';

interface DemoPageProps {
  integrations: Integration[];
  onSelectIntegration?: (id: number) => void;
  onNavigateToIncidents?: () => void;
}

type ScenarioType = 'NORMAL' | 'SILENT' | 'RECOVER_AFTER_RETRY' | 'PERMANENT_FAILURE';

interface ScenarioDef {
  type: ScenarioType;
  name: string;
  description: string;
  expectedOutcome: string;
}

const SCENARIOS: ScenarioDef[] = [
  {
    type: 'NORMAL',
    name: 'Normal Continuous Telemetry',
    description: 'Simulates normal steady telemetry arrival. Generates valid cycle events at expected intervals.',
    expectedOutcome: 'Integration stays HEALTHY. last_seen_at advances steadily. Zero incidents created.',
  },
  {
    type: 'SILENT',
    name: 'Silent Sensor Interruption',
    description: 'Emits initial cycle telemetry then abruptly stops all data transmission.',
    expectedOutcome: 'Data freshness breaches stale threshold. Status transitions to STALE. A single active Incident is opened.',
  },
  {
    type: 'RECOVER_AFTER_RETRY',
    name: 'Controlled Auto-Recovery (Scenario A)',
    description: 'Stops sending events until incident enters RECOVERING, then automatically resumes valid telemetry upon recovery action.',
    expectedOutcome: 'Incident detected → Recovery action executed → New event received → Verification succeeds → Incident RESOLVED.',
  },
  {
    type: 'PERMANENT_FAILURE',
    name: 'Permanent Hardware Failure (Scenario B)',
    description: 'Hardware communication is permanently lost; zero events arrive despite automated recovery retries.',
    expectedOutcome: '3 bounded recovery attempts fail verification → Retries exhausted → Incident ESCALATED → Integration marked FAILED.',
  },
];

export const DemoPage: React.FC<DemoPageProps> = ({
  integrations,
  onNavigateToIncidents,
}) => {
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<number>(
    integrations[0]?.id || 1
  );
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>('RECOVER_AFTER_RETRY');
  const [isSending, setIsSending] = useState(false);
  const [eventLogs, setEventLogs] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  const selectedIntegration = integrations.find((i) => i.id === selectedIntegrationId) || integrations[0];
  const machineId = selectedIntegration?.machine_id || 1;

  const cliCommand = `python -m simulator.machine_simulator --scenario ${selectedScenario} --integration-id ${selectedIntegrationId} --machine-id ${machineId}`;

  const handleCopyCommand = async () => {
    try {
      await navigator.clipboard.writeText(cliCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSendTelemetry = async (count: number = 1) => {
    setIsSending(true);
    const newLogs: string[] = [];

    for (let i = 0; i < count; i++) {
      const eventId = `sim-${Date.now()}-${i + 1}`;
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
            cycle_time_ms: 1840,
          },
        });
        newLogs.push(`[${new Date().toLocaleTimeString()}] Event ${res.event_id} -> HTTP 201 Created (persisted)`);
      } catch (err: unknown) {
        newLogs.push(
          `[${new Date().toLocaleTimeString()}] Event ${eventId} ERROR: ${
            err instanceof Error ? err.message : String(err)
          }`
        );
      }
    }

    setEventLogs((prev) => [...newLogs, ...prev].slice(0, 25));
    setIsSending(false);
  };

  const activeScenario = SCENARIOS.find((s) => s.type === selectedScenario) || SCENARIOS[0];

  return (
    <div className="demo-page">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Simulator & Demo Console</h2>
            <p className="card-subtitle">
              External machine simulation and closed-loop verification workbench.
            </p>
          </div>
          {selectedIntegration && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className="text-muted" style={{ fontSize: '0.8rem' }}>Target Status:</span>
              <StatusIndicator status={selectedIntegration.health_state} />
            </div>
          )}
        </div>

        {/* Transparency note mandated by requirement 17 */}
        <div className="transparency-banner">
          <span className="info-icon">ℹ</span>
          <span>
            <strong>Transparency Notice:</strong> The simulator behaves as an external machine integration
            and sends events through the same HTTP ingestion API used by the application (<code>POST /api/v1/events</code>).
          </span>
        </div>

        <div className="demo-controls-grid">
          <div className="control-group">
            <label htmlFor="integration-select" className="control-label">Target Integration</label>
            <select
              id="integration-select"
              className="form-select"
              value={selectedIntegrationId}
              onChange={(e) => setSelectedIntegrationId(Number(e.target.value))}
            >
              {integrations.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} (ID: {i.id} | Machine #{i.machine_id} | {i.health_state})
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="scenario-select" className="control-label">Simulation Scenario</label>
            <select
              id="scenario-select"
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

        {/* Scenario description & expected outcome */}
        <div className="scenario-spec-box">
          <div className="scenario-spec-header">
            <span className="scenario-tag">{activeScenario.type}</span>
            <span className="scenario-name">{activeScenario.name}</span>
          </div>
          <p className="scenario-desc">{activeScenario.description}</p>
          <div className="scenario-outcome">
            <span className="outcome-label">Expected Behavior:</span>
            <span>{activeScenario.expectedOutcome}</span>
          </div>
        </div>

        {/* CLI Execution Command */}
        <div className="terminal-box">
          <div className="terminal-header">
            <span className="terminal-title">TERMINAL SIMULATOR EXECUTION</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleCopyCommand}
              id="copy-cli-command-btn"
            >
              {copied ? '✓ COPIED' : 'COPY COMMAND'}
            </button>
          </div>
          <pre className="terminal-content"><code>{cliCommand}</code></pre>
        </div>

        {/* In-Browser Telemetry Injection */}
        <div className="emitter-section">
          <div className="emitter-header">
            <div>
              <h3 className="emitter-title">In-Browser Telemetry Emitter</h3>
              <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0 }}>
                Dispatches real telemetry events directly to <code>POST /api/v1/events</code> to test ingestion and verify recovery.
              </p>
            </div>
            <div className="emitter-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleSendTelemetry(1)}
                disabled={isSending}
                id="emit-single-event-btn"
              >
                {isSending ? 'Transmitting...' : 'Emit Single Event'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleSendTelemetry(3)}
                disabled={isSending}
                id="emit-burst-events-btn"
              >
                Emit 3-Event Burst
              </button>
              {onNavigateToIncidents && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={onNavigateToIncidents}
                >
                  View Incidents →
                </button>
              )}
            </div>
          </div>

          {eventLogs.length > 0 && (
            <div className="console-stream" aria-label="Event Transmission Log">
              {eventLogs.map((log, index) => (
                <div key={index} className="stream-line">{log}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
