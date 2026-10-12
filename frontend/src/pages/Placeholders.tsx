import React from 'react';

export const Incidents: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Incidents Feed</h2>
    <p style={{ color: 'var(--text-muted)' }}>Configured detection rules group incoming errors into actionable incident candidates.</p>
  </div>
);

export const IncidentDetail: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Incident Investigation & RCA</h2>
    <p style={{ color: 'var(--text-muted)' }}>Evidence-grounded root causes, runbook recommendations, and diagnostic checks.</p>
  </div>
);

export const Tickets: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Incident Tickets Board</h2>
    <p style={{ color: 'var(--text-muted)' }}>Persistent ticket management with P1-P4 priority routing and lifecycle enforcement.</p>
  </div>
);

export const Approvals: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Protected Remediation Approvals</h2>
    <p style={{ color: 'var(--text-muted)' }}>Senior approver review queue for protected actions. Enforces backend-validated authorization.</p>
  </div>
);

export const AuditLog: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Append-Only Audit Trail</h2>
    <p style={{ color: 'var(--text-muted)' }}>Immutable log of user actions, approvals, automated remediation runs, and recovery verification outcomes.</p>
  </div>
);

export const Knowledge: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Approved Runbooks & Past Incident Archive</h2>
    <p style={{ color: 'var(--text-muted)' }}>Historical incident resolutions and operational runbooks indexed for copilot retrieval.</p>
  </div>
);

export const AdminSettings: React.FC = () => (
  <div className="glass-panel" style={{ padding: '24px' }}>
    <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Admin Configuration & Sources</h2>
    <p style={{ color: 'var(--text-muted)' }}>Log source API keys, detection rule thresholds, model provider settings, and action allow-lists.</p>
  </div>
);
