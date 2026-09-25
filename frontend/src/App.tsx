import React, { useState, useEffect, useCallback } from 'react';
import type { Integration, Incident } from './types';
import { api } from './api/client';
import { DashboardPage } from './pages/DashboardPage';
import { IntegrationDetailPage } from './pages/IntegrationDetailPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { SimulatorJudgePage } from './pages/SimulatorJudgePage';

type ViewMode = 'dashboard' | 'integration' | 'incident' | 'simulator';

export const App: React.FC = () => {
  const [view, setView] = useState<ViewMode>('dashboard');
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<number | null>(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [backendHealthy, setBackendHealthy] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [pollingEnabled, setPollingEnabled] = useState<boolean>(true);
  const [lastSync, setLastSync] = useState<Date>(new Date());

  const fetchGlobalData = useCallback(async () => {
    try {
      const [health, intgList, incList] = await Promise.all([
        api.checkHealth().catch(() => ({ status: 'down' })),
        api.getIntegrations().catch(() => []),
        api.getIncidents().catch(() => []),
      ]);

      setBackendHealthy(health.status === 'healthy');
      setIntegrations(intgList);
      setIncidents(incList);
      setLastSync(new Date());
    } catch {
      setBackendHealthy(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Polling every 3 seconds
  useEffect(() => {
    fetchGlobalData();
    if (!pollingEnabled) return;

    const interval = setInterval(fetchGlobalData, 3000);
    return () => clearInterval(interval);
  }, [fetchGlobalData, pollingEnabled]);

  const handleSelectIntegration = (id: number) => {
    setSelectedIntegrationId(id);
    setView('integration');
  };

  const handleSelectIncident = (id: number) => {
    setSelectedIncidentId(id);
    setView('incident');
  };

  const activeIntegration = integrations.find((i) => i.id === selectedIntegrationId);
  const activeIncidentForIntegration = incidents.find(
    (inc) => inc.integration_id === selectedIntegrationId && inc.state !== 'RESOLVED'
  ) || null;

  return (
    <div className="app-container">
      {/* Top Industrial Navigation Header */}
      <header className="top-nav">
        <div className="brand-section">
          <div className="brand-logo">⚡</div>
          <div>
            <div className="brand-title">Factory Data Reliability Monitor</div>
            <div className="brand-subtitle">Field Support & Autonomous Auto-Recovery Console</div>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${view === 'dashboard' ? 'active' : ''}`}
            onClick={() => setView('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`nav-btn ${view === 'simulator' ? 'active' : ''}`}
            onClick={() => setView('simulator')}
          >
            Simulator / Judge Mode
          </button>
        </nav>

        <div className="system-status">
          <div className="pulse-indicator">
            <span className={`pulse-dot ${backendHealthy ? 'pulse' : 'error'}`} />
            <span>{backendHealthy ? 'API Connected' : 'API Offline'}</span>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPollingEnabled(!pollingEnabled)}
            title="Toggle background auto-refresh"
          >
            {pollingEnabled ? 'Auto-Sync: ON (3s)' : 'Auto-Sync: PAUSED'}
          </button>

          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
            Synced: {lastSync.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {!backendHealthy && (
          <div className="alert-banner alert-danger">
            <strong>Backend API is unreachable.</strong> Ensure the FastAPI server is running on{' '}
            <code>http://localhost:8000</code>.
          </div>
        )}

        {view === 'dashboard' && (
          <DashboardPage
            integrations={integrations}
            incidents={incidents}
            onSelectIntegration={handleSelectIntegration}
            onSelectIncident={handleSelectIncident}
            onRefresh={fetchGlobalData}
            isLoading={isLoading}
          />
        )}

        {view === 'integration' && activeIntegration && (
          <IntegrationDetailPage
            integration={activeIntegration}
            activeIncident={activeIncidentForIntegration}
            onBack={() => setView('dashboard')}
            onSelectIncident={handleSelectIncident}
            onRefresh={fetchGlobalData}
          />
        )}

        {view === 'incident' && selectedIncidentId && (
          <IncidentDetailPage
            incidentId={selectedIncidentId}
            onBack={() => setView('dashboard')}
            onSelectIntegration={handleSelectIntegration}
          />
        )}

        {view === 'simulator' && (
          <SimulatorJudgePage
            integrations={integrations}
            onSelectIntegration={handleSelectIntegration}
          />
        )}
      </main>
    </div>
  );
};

export default App;
