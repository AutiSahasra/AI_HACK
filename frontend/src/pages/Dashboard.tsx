import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident } from '../types';
import { 
  AlertTriangle, 
  FileText, 
  UploadCloud, 
  TicketCheck, 
  ShieldCheck, 
  Activity, 
  CheckCircle,
  ArrowRight,
  RefreshCw,
  Flame,
  Zap,
  Server,
  Layers,
  ChevronRight,
  Sparkles,
  RotateCcw
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [recentIncidents, setRecentIncidents] = useState<Incident[]>([]);
  const [demoStatus, setDemoStatus] = useState<{ status: string; active_fault?: string; service?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simMessage, setSimMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [statsRes, incsRes, demoRes] = await Promise.allSettled([
        api.getDashboardStats(),
        api.getIncidents(),
        api.getDemoStatus(),
      ]);

      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value);
      }
      if (incsRes.status === 'fulfilled') {
        setRecentIncidents(incsRes.value.slice(0, 5));
      }
      if (demoRes.status === 'fulfilled') {
        setDemoStatus(demoRes.value);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleInjectFault = async (faultType: string, label: string) => {
    setSimulating(true);
    setSimMessage(null);
    try {
      await api.injectDemoFault(faultType);
      setSimMessage(`Injected '${label}'. Stream collector is tailing simulated logs...`);
      await loadData();
    } catch (err: any) {
      setSimMessage(`Fault injection error: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleResetFault = async () => {
    setSimulating(true);
    try {
      await api.resetDemoFault();
      setSimMessage('Fault cleared. Target service restored to healthy state.');
      await loadData();
    } catch (err: any) {
      setSimMessage(`Reset error: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const totalLogs = stats?.totalLogs || 0;
  const totalIncidents = stats?.totalIncidents || 0;
  const totalTickets = stats?.totalTickets || 0;
  const pendingApprovals = stats?.pendingApprovals || 0;
  const satisfactionRate = stats?.feedbackSummary?.satisfactionRate ?? 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{
        padding: '28px 32px',
        background: 'radial-gradient(ellipse at 85% 20%, rgba(56, 189, 248, 0.16), transparent 70%), var(--bg-card)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={13} className="animate-pulse" /> Live Telemetry System
            </span>
            {demoStatus?.active_fault ? (
              <span className="badge badge-critical" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Flame size={13} /> Active Fault: {demoStatus.active_fault}
              </span>
            ) : (
              <span className="badge badge-resolved" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle size={13} /> Demo Target: Healthy
              </span>
            )}
          </div>
          <h2 style={{ fontSize: '26px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
            AI Root Cause Analysis & Intelligent Ticket Resolution
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '700px', lineHeight: '1.5' }}>
            Unified log intelligence, anomaly grouping, anti-hallucination AI root-cause hypotheses with evidence citations, allow-listed remediation, and dual-gated SRE approvals.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <Link to="/upload" className="btn btn-secondary">
            <UploadCloud size={16} />
            <span>Upload Logs</span>
          </Link>
          <Link to="/logs" className="btn btn-secondary">
            <FileText size={16} />
            <span>Log Explorer</span>
          </Link>
          <Link to="/incidents" className="btn btn-primary">
            <AlertTriangle size={16} />
            <span>Incidents Feed</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '18px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Normalized Logs
            </span>
            <div style={{ padding: '8px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '8px', color: 'var(--accent-cyan)' }}>
              <FileText size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : totalLogs.toLocaleString()}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Secret-redacted & indexed
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Correlated Incidents
            </span>
            <div style={{ padding: '8px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '8px', color: 'var(--accent-rose)' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : totalIncidents}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Auto-grouped clusters
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Pending Approvals
            </span>
            <div style={{ 
              padding: '8px', 
              background: pendingApprovals > 0 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.1)', 
              borderRadius: '8px', 
              color: pendingApprovals > 0 ? '#f59e0b' : 'var(--accent-indigo)' 
            }}>
              <ShieldCheck size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: pendingApprovals > 0 ? '#f59e0b' : '#fff' }}>
            {loading ? '...' : pendingApprovals}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {pendingApprovals > 0 ? (
              <Link to="/approvals" style={{ color: '#f59e0b', textDecoration: 'none', fontWeight: 600 }}>
                Review in Approvals queue &rarr;
              </Link>
            ) : (
              'Protected dual-gate queue'
            )}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Active Tickets
            </span>
            <div style={{ padding: '8px', background: 'rgba(168, 85, 247, 0.1)', borderRadius: '8px', color: '#c084fc' }}>
              <TicketCheck size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : totalTickets}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Lifecycle & assignment tracked
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              AI Hypothesis Accuracy
            </span>
            <div style={{ padding: '8px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', color: 'var(--accent-emerald)' }}>
              <Sparkles size={18} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {satisfactionRate}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Operator feedback & verification
          </div>
        </div>
      </div>

      {/* Live Interactive Fault Simulator Card */}
      <div className="glass-panel" style={{
        padding: '24px',
        border: demoStatus?.active_fault ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid var(--border-subtle)',
        background: demoStatus?.active_fault 
          ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.08), rgba(6, 9, 14, 0.9))' 
          : 'var(--bg-card)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Flame size={20} color={demoStatus?.active_fault ? '#f43f5e' : 'var(--accent-cyan)'} />
              <h3 style={{ fontSize: '18px', margin: 0, color: '#fff' }}>
                Live Incident Simulation Lab
              </h3>
              <span className="badge" style={{ fontSize: '11px', background: 'rgba(255,255,255,0.08)' }}>
                Target: order-service (:8001)
              </span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0, maxWidth: '720px' }}>
              Click any fault button below to inject an anomaly into the demo service. The live log collector tailer will stream the error, triggering automatic grouping, ticket creation, and AI root cause analysis.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {demoStatus?.active_fault && (
              <button 
                onClick={handleResetFault} 
                className="btn btn-secondary" 
                disabled={simulating}
                style={{ borderColor: 'var(--accent-emerald)', color: '#34d399' }}
              >
                <RotateCcw size={14} />
                <span>Reset Fault</span>
              </button>
            )}
            <button onClick={loadData} className="btn btn-secondary" style={{ padding: '8px 12px' }} title="Refresh State">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {simMessage && (
          <div style={{ 
            padding: '10px 14px', 
            borderRadius: '6px', 
            background: 'rgba(56, 189, 248, 0.12)', 
            border: '1px solid var(--border-accent)',
            fontSize: '13px',
            color: 'var(--accent-cyan)',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Zap size={15} />
            <span>{simMessage}</span>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <button
            onClick={() => handleInjectFault('db_connection_timeout', 'Database Pool Exhaustion')}
            disabled={simulating}
            className="btn"
            style={{
              background: demoStatus?.active_fault === 'db_connection_timeout' ? 'rgba(244, 63, 94, 0.3)' : 'var(--bg-secondary)',
              border: demoStatus?.active_fault === 'db_connection_timeout' ? '1px solid #f43f5e' : '1px solid var(--border-subtle)',
              padding: '14px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#f43f5e' }}>Database Pool Exhaustion</span>
              <Server size={15} color="#f43f5e" />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Times out worker connections & saturates 20/20 DB pool
            </div>
          </button>

          <button
            onClick={() => handleInjectFault('memory_leak', 'Heap Memory Leak Spike')}
            disabled={simulating}
            className="btn"
            style={{
              background: demoStatus?.active_fault === 'memory_leak' ? 'rgba(244, 63, 94, 0.3)' : 'var(--bg-secondary)',
              border: demoStatus?.active_fault === 'memory_leak' ? '1px solid #f43f5e' : '1px solid var(--border-subtle)',
              padding: '14px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#f59e0b' }}>OutOfMemory Heap Leak</span>
              <Activity size={15} color="#f59e0b" />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Allocates 512KB buffers, triggers GC overhead limit error
            </div>
          </button>

          <button
            onClick={() => handleInjectFault('bad_config_deploy', 'Bad Config Deployment')}
            disabled={simulating}
            className="btn"
            style={{
              background: demoStatus?.active_fault === 'bad_config_deploy' ? 'rgba(244, 63, 94, 0.3)' : 'var(--bg-secondary)',
              border: demoStatus?.active_fault === 'bad_config_deploy' ? '1px solid #f43f5e' : '1px solid var(--border-subtle)',
              padding: '14px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#38bdf8' }}>Bad Config Deployment</span>
              <FileText size={15} color="#38bdf8" />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Simulates missing mandatory environment variable DB_HOST
            </div>
          </button>

          <button
            onClick={() => handleInjectFault('downstream_503', 'Downstream 503 Outage')}
            disabled={simulating}
            className="btn"
            style={{
              background: demoStatus?.active_fault === 'downstream_503' ? 'rgba(244, 63, 94, 0.3)' : 'var(--bg-secondary)',
              border: demoStatus?.active_fault === 'downstream_503' ? '1px solid #f43f5e' : '1px solid var(--border-subtle)',
              padding: '14px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: '#ec4899' }}>Downstream 503 Outage</span>
              <AlertTriangle size={15} color="#ec4899" />
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Emits billing gateway unavailable cascade errors
            </div>
          </button>
        </div>
      </div>

      {/* Two Column Section: Recent Incidents & End-to-End Workflow */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '24px' }}>
        {/* Active Incidents Quick-Action Queue */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '17px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#fff' }}>
              <Layers size={18} color="var(--accent-cyan)" />
              <span>Recent Correlated Incidents</span>
            </h3>
            <Link to="/incidents" style={{ fontSize: '13px', color: 'var(--accent-cyan)', textDecoration: 'none' }}>
              View All ({totalIncidents}) &rarr;
            </Link>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {recentIncidents.length === 0 ? (
              <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-dim)' }}>
                No active incidents right now. Click a fault injection above or upload logs to simulate one.
              </div>
            ) : (
              recentIncidents.map(inc => {
                const incId = inc.id || (inc as any)._id || '';
                return (
                  <div
                    key={incId}
                    style={{
                      background: 'var(--bg-secondary)',
                      borderRadius: '8px',
                      padding: '14px 16px',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxWidth: '70%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`badge badge-${inc.severity.toLowerCase()}`}>
                          {inc.severity}
                        </span>
                        <span className="badge badge-info" style={{ fontSize: '11px' }}>
                          {inc.status}
                        </span>
                        <span style={{ fontWeight: 600, color: 'var(--accent-cyan)', fontSize: '13px' }}>
                          {inc.service}
                        </span>
                      </div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {inc.title}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                        {inc.eventCount} events &bull; Last seen: {new Date(inc.lastSeen).toLocaleTimeString()}
                      </div>
                    </div>

                    <Link
                      to={`/incidents/${incId}`}
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: '12px', whiteSpace: 'nowrap' }}
                    >
                      <span>Investigate</span>
                      <ChevronRight size={14} />
                    </Link>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Step-by-Step Resolution Workflow Guide */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '17px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#fff' }}>
            <Activity size={18} color="var(--accent-cyan)" />
            <span>Log Issue Resolution Lifecycle</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid var(--accent-cyan)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '2px' }}>
                1. Ingestion & Secret Masking
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Files or live tailer ingest logs. Passwords, auth tokens, and PII are redacted before indexing.
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid #6366f1' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '2px' }}>
                2. Anomaly Grouping & Deduplication
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Error bursts match regex & spike rules, auto-clustering correlated events into candidate incidents.
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid #c084fc' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '2px' }}>
                3. Evidence-Grounded AI Root Cause
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Anti-hallucination engine cites exact log lines, computes confidence score, and suggests allow-listed runbooks.
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid #10b981' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '2px' }}>
                4. Dual-Gate Remediation & Recovery Check
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Support engineer requests fix &rarr; Senior SRE approves &rarr; Zero-shell executor runs action &rarr; Health check polls confirm recovery.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
