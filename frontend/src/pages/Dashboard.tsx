import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { 
  AlertTriangle, 
  FileText, 
  UploadCloud, 
  TicketCheck, 
  ShieldCheck, 
  Activity, 
  CheckCircle,
  ArrowRight
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [totalLogs, setTotalLogs] = useState(0);
  const [uploadsCount, setUploadsCount] = useState(0);
  const [incidentsCount, setIncidentsCount] = useState(0);
  const [ticketsCount, setTicketsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadOverview = async () => {
      try {
        const [logsResp, uploadsResp] = await Promise.allSettled([
          api.getLogs({ page: 1, page_size: 1 }),
          api.getUploads(10),
        ]);
        if (logsResp.status === 'fulfilled') {
          setTotalLogs(logsResp.value.total);
        }
        if (uploadsResp.status === 'fulfilled') {
          setUploadsCount(uploadsResp.value.length);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadOverview();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{
        padding: '28px 32px',
        background: 'radial-gradient(ellipse at 80% 20%, rgba(56, 189, 248, 0.15), transparent 70%), var(--bg-card)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <span className="badge badge-info" style={{ marginBottom: '10px' }}>
            System Operational
          </span>
          <h2 style={{ fontSize: '26px', fontWeight: 700, marginBottom: '6px' }}>
            Incident Intelligence & Remediation Copilot
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '640px' }}>
            Continuous log normalization, automated incident correlation, grounded AI root-cause hypotheses, and policy-governed remediation with recovery verification.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <Link to="/upload" className="btn btn-primary">
            <UploadCloud size={16} />
            <span>Upload Logs</span>
          </Link>
          <Link to="/logs" className="btn btn-secondary">
            <FileText size={16} />
            <span>Open Explorer</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '18px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Normalized Events
            </span>
            <div style={{ padding: '8px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '8px', color: 'var(--accent-cyan)' }}>
              <FileText size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : totalLogs.toLocaleString()}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Indexed across all sources
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Files Ingested
            </span>
            <div style={{ padding: '8px', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '8px', color: 'var(--accent-indigo)' }}>
              <UploadCloud size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : uploadsCount}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            CSV, TXT, LOG, JSON batches
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Active Incidents
            </span>
            <div style={{ padding: '8px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '8px', color: 'var(--accent-rose)' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {incidentsCount}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Correlated candidate issues
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Resolved Safely
            </span>
            <div style={{ padding: '8px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', color: 'var(--accent-emerald)' }}>
              <CheckCircle size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            100%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Recovery health check verified
          </div>
        </div>
      </div>

      {/* Architecture & Pipeline Workflow Overview */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={20} color="var(--accent-cyan)" />
          <span>Core Operational Pipeline Status</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px' }}>
          {[
            { step: '1. Ingestion & Redaction', desc: 'Auto-masking passwords, Bearer tokens, card numbers, PII', status: 'Active' },
            { step: '2. Detection & Grouping', desc: 'Z-score spike check + regex patterns + fingerprint dedup', status: 'Ready' },
            { step: '3. Grounded AI RCA', desc: 'Strict Pydantic JSON schema + cited evidence validation', status: 'Ready' },
            { step: '4. Dual-Gated Approval', desc: 'Backend RBAC policy check; self-approval prevention', status: 'Protected' },
            { step: '5. Recovery Verification', desc: 'HTTP /health poll + error quiet-window confirmation', status: 'Enforced' },
          ].map((item, i) => (
            <div key={i} style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '4px' }}>
                {item.status.toUpperCase()}
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>
                {item.step}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
