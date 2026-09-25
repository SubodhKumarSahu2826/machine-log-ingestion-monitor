import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Integration, Incident } from './types';
import { api } from './api/client';
import { OperationsPage } from './pages/OperationsPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { IncidentPage } from './pages/IncidentPage';
import { DemoPage } from './pages/DemoPage';

type NavView = 'operations' | 'integrations' | 'incident' | 'demo';

export const App: React.FC = () => {
  const [view, setView] = useState<NavView>('operations');
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<number | null>(null);
  const [selectedIncidentId, setSelectedIncidentId] = useState<number | null>(null);

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [backendHealthy, setBackendHealthy] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [pollingEnabled, setPollingEnabled] = useState<boolean>(true);
  const [lastSync, setLastSync] = useState<Date>(new Date());

  // Prevent overlapping background requests
  const isFetchingRef = useRef<boolean>(false);

  const fetchGlobalData = useCallback(async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

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
      isFetchingRef.current = false;
      setIsLoading(false);
    }
  }, []);

  // Polling loop with clean interval teardown
  useEffect(() => {
    fetchGlobalData();
    if (!pollingEnabled) return;

    const interval = setInterval(fetchGlobalData, 3500);
    return () => clearInterval(interval);
  }, [fetchGlobalData, pollingEnabled]);

  const handleSelectIntegration = (id: number) => {
    setSelectedIntegrationId(id);
    setView('integrations');
  };

  const handleSelectIncident = (id: number) => {
    setSelectedIncidentId(id);
    setView('incident');
  };

  // Count open/unresolved incidents for badge
  const openIncidentsCount = incidents.filter((i) => i.state !== 'RESOLVED').length;

  return (
    <div className="app-layout">
      {/* Top Industrial Navigation Header */}
      <header className="app-header">
        <div className="brand-block">
          <span className="brand-symbol">⚙</span>
          <div>
            <h1 className="brand-title">FACTORY DATA RELIABILITY MONITOR</h1>
            <p className="brand-subtitle">Autonomous Log Ingestion & Closed-Loop Recovery</p>
          </div>
        </div>

        <nav className="nav-tabs" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab ${view === 'operations' ? 'active' : ''}`}
            onClick={() => setView('operations')}
            id="nav-operations-btn"
          >
            Operations Flow
          </button>
          <button
            type="button"
            className={`nav-tab ${view === 'integrations' ? 'active' : ''}`}
            onClick={() => setView('integrations')}
            id="nav-integrations-btn"
          >
            Integrations Registry
          </button>
          <button
            type="button"
            className={`nav-tab ${view === 'incident' ? 'active' : ''}`}
            onClick={() => setView('incident')}
            id="nav-incident-btn"
          >
            Incident Workspace
            {openIncidentsCount > 0 && (
              <span className="tab-badge" aria-label={`${openIncidentsCount} active incidents`}>
                {openIncidentsCount}
              </span>
            )}
          </button>
          <button
            type="button"
            className={`nav-tab ${view === 'demo' ? 'active' : ''}`}
            onClick={() => setView('demo')}
            id="nav-demo-btn"
          >
            Simulator Demo
          </button>
        </nav>

        <div className="system-telemetry">
          <div className="health-pill" title={backendHealthy ? 'API Connection Healthy' : 'API Unreachable'}>
            <span className={`status-dot ${backendHealthy ? 'dot-online' : 'dot-offline'}`} />
            <span className="health-text">{backendHealthy ? 'API ONLINE' : 'API OFFLINE'}</span>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setPollingEnabled(!pollingEnabled)}
            title="Toggle background polling loop"
            id="toggle-sync-btn"
          >
            {pollingEnabled ? 'Sync: 3.5s' : 'Sync: PAUSED'}
          </button>

          <span className="sync-time font-mono" title="Last background poll">
            {lastSync.toLocaleTimeString()}
          </span>
        </div>
      </header>

      {/* Main Operational View */}
      <main className="app-main">
        {!backendHealthy && (
          <div className="banner banner-alert" role="alert">
            <strong>BACKEND UNREACHABLE:</strong> Verify FastAPI ingestion backend is listening on{' '}
            <code>http://localhost:8000</code>.
          </div>
        )}

        {view === 'operations' && (
          <OperationsPage
            integrations={integrations}
            incidents={incidents}
            onSelectIntegration={handleSelectIntegration}
            onSelectIncident={handleSelectIncident}
            onNavigateToSimulator={() => setView('demo')}
          />
        )}

        {view === 'integrations' && (
          <IntegrationsPage
            integrations={integrations}
            incidents={incidents}
            selectedIntegrationId={selectedIntegrationId}
            onSelectIntegration={handleSelectIntegration}
            onSelectIncident={handleSelectIncident}
            onRefresh={fetchGlobalData}
            isLoading={isLoading}
          />
        )}

        {view === 'incident' && (
          <IncidentPage
            incidentId={selectedIncidentId}
            incidents={incidents}
            integrations={integrations}
            onBack={() => setView('operations')}
            onSelectIncident={handleSelectIncident}
            onSelectIntegration={handleSelectIntegration}
          />
        )}

        {view === 'demo' && (
          <DemoPage
            integrations={integrations}
            onSelectIntegration={handleSelectIntegration}
            onNavigateToIncidents={() => setView('incident')}
          />
        )}
      </main>
    </div>
  );
};

export default App;
