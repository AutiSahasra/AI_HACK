import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, getStoredUser } from '../api/client';
import { Incident } from '../types';
import { getRoleDisplayName, hasPermission } from '../auth/permissions';
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
  Sparkles,
  RotateCcw,
  Clock,
  XCircle,
  Shield,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Info,
  Calendar,
  ExternalLink,
  Cpu,
  BarChart3,
  HelpCircle,
  PlayCircle
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const currentUser = getStoredUser();
  const userRole = currentUser?.role;

  // Filter States
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');
  const [selectedService, setSelectedService] = useState<string>('');
  const [stats, setStats] = useState<any>(null);
  const [demoStatus, setDemoStatus] = useState<{ status: string; active_fault?: string; service?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simMessage, setSimMessage] = useState<string | null>(null);
  const [hoveredTrendIdx, setHoveredTrendIdx] = useState<number | null>(null);

  const loadData = async () => {
    try {
      const promises: Promise<any>[] = [
        api.getDashboardStats(timeRange, selectedService || undefined),
      ];

      // Only admin is authorized to query live demo status & fault injection
      if (userRole === 'admin') {
        promises.push(api.getDemoStatus());
      }

      const results = await Promise.allSettled(promises);

      if (results[0].status === 'fulfilled') {
        setStats(results[0].value);
      }
      if (userRole === 'admin' && results[1]?.status === 'fulfilled') {
        setDemoStatus((results[1] as PromiseFulfilledResult<any>).value);
      }
    } catch (e) {
      console.error('Failed to load dashboard analytics:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [userRole, timeRange, selectedService]);

  const handleInjectFault = async (faultType: string, label: string) => {
    setSimulating(true);
    setSimMessage(null);
    try {
      await api.injectDemoFault(faultType);
      setSimMessage(`Injected '${label}'. Collector is tailing live simulated failure logs...`);
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
      setSimMessage('Fault cleared. Target demo microservice restored to healthy state.');
      await loadData();
    } catch (err: any) {
      setSimMessage(`Reset error: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  // Safe extraction of analytics payload
  const kpis = stats?.kpis || {};
  const totalIncidents = kpis.totalIncidents?.value ?? (stats?.totalIncidents || 0);
  const totalIncTrend = kpis.totalIncidents?.pctChange;
  const unresolvedTickets = kpis.unresolvedTickets?.value ?? (stats?.activeTickets || 0);
  const totalTickets = kpis.unresolvedTickets?.totalTickets ?? (stats?.totalTickets || 0);
  const criticalErrors = kpis.criticalErrors?.value ?? 0;
  const critTrend = kpis.criticalErrors?.pctChange;
  const mttd = kpis.mttd;
  const mttr = kpis.mttr;
  const successRate = kpis.resolutionSuccessRate;
  const pendingApprovals = stats?.pendingApprovals || 0;

  const incidentTrends = stats?.incidentTrends || [];
  const failureProneServices = stats?.failureProneServices || [];
  const severityBreakdown = stats?.severityBreakdown || [];
  const recentIncidents = stats?.recentIncidents || [];
  const uptimeData = stats?.uptimeData || {};
  const availableServices: string[] = stats?.availableServices || ['order-service'];

  // Status badge styling helper
  const renderIncidentStatusBadge = (status: string) => {
    switch (status) {
      case 'resolved':
        return <span className="badge badge-status-resolved">Resolved</span>;
      case 'awaiting_approval':
        return <span className="badge badge-status-pending-approval">Awaiting Approval</span>;
      case 'remediating':
        return <span className="badge badge-status-in-progress">Remediating</span>;
      case 'verifying':
        return <span className="badge badge-status-verifying">Verifying</span>;
      case 'escalated':
        return <span className="badge badge-status-escalated">Escalated</span>;
      default:
        return <span className="badge badge-status-open">{status.replace('_', ' ')}</span>;
    }
  };

  const renderSeverityBadge = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return <span className="badge badge-critical">Critical</span>;
      case 'ERROR':
        return <span className="badge badge-error">High</span>;
      case 'WARN':
        return <span className="badge badge-warn">Medium</span>;
      default:
        return <span className="badge badge-info">Low</span>;
    }
  };

  // Calculate SVG curve coordinates for Incident Trends Chart
  const renderTrendsChart = () => {
    if (!incidentTrends || incidentTrends.length === 0) {
      return (
        <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-dim)' }}>
          No incident trend records for selected time range.
        </div>
      );
    }

    const width = 640;
    const height = 180;
    const padding = { top: 20, right: 20, bottom: 30, left: 35 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const maxVal = Math.max(
      4,
      ...incidentTrends.map((d: any) => Math.max(d.total || 0, d.critical || 0, d.resolved || 0))
    );

    const getX = (i: number) => padding.left + (i / Math.max(1, incidentTrends.length - 1)) * chartW;
    const getY = (val: number) => padding.top + chartH - (val / maxVal) * chartH;

    // Create polyline paths
    const totalPoints = incidentTrends.map((d: any, i: number) => `${getX(i)},${getY(d.total || 0)}`).join(' ');
    const criticalPoints = incidentTrends.map((d: any, i: number) => `${getX(i)},${getY(d.critical || 0)}`).join(' ');
    const resolvedPoints = incidentTrends.map((d: any, i: number) => `${getX(i)},${getY(d.resolved || 0)}`).join(' ');

    // Area closed path for total
    const areaTotal = `${getX(0)},${padding.top + chartH} ` + totalPoints + ` ${getX(incidentTrends.length - 1)},${padding.top + chartH}`;

    const hoveredData = hoveredTrendIdx !== null ? incidentTrends[hoveredTrendIdx] : null;

    return (
      <div style={{ position: 'relative', width: '100%' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', overflow: 'visible', display: 'block' }}
        >
          <defs>
            <linearGradient id="totalAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="critLineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#fb923c" />
              <stop offset="100%" stopColor="#f43f5e" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.5, 1].map((ratio, idx) => {
            const yPos = padding.top + chartH * ratio;
            const val = Math.round(maxVal * (1 - ratio));
            return (
              <g key={idx}>
                <line
                  x1={padding.left}
                  y1={yPos}
                  x2={width - padding.right}
                  y2={yPos}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 8}
                  y={yPos + 4}
                  fill="var(--text-dim)"
                  fontSize="10"
                  textAnchor="end"
                  fontFamily="var(--font-mono)"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Area Fill for Total Incidents */}
          <polygon points={areaTotal} fill="url(#totalAreaGrad)" />

          {/* Lines */}
          <polyline
            points={totalPoints}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            points={criticalPoints}
            fill="none"
            stroke="url(#critLineGrad)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <polyline
            points={resolvedPoints}
            fill="none"
            stroke="#10b981"
            strokeWidth="2"
            strokeDasharray="3 3"
            strokeLinecap="round"
          />

          {/* Interactive Hover Slices & Points */}
          {incidentTrends.map((d: any, i: number) => {
            const cx = getX(i);
            const isHovered = hoveredTrendIdx === i;
            return (
              <g key={i}>
                {/* Invisible hover trigger column */}
                <rect
                  x={cx - (chartW / incidentTrends.length) / 2}
                  y={padding.top}
                  width={chartW / incidentTrends.length}
                  height={chartH}
                  fill="transparent"
                  cursor="pointer"
                  onMouseEnter={() => setHoveredTrendIdx(i)}
                  onMouseLeave={() => setHoveredTrendIdx(null)}
                />
                {isHovered && (
                  <>
                    <line
                      x1={cx}
                      y1={padding.top}
                      x2={cx}
                      y2={padding.top + chartH}
                      stroke="rgba(255, 255, 255, 0.3)"
                      strokeWidth="1.5"
                      strokeDasharray="2 2"
                    />
                    <circle cx={cx} cy={getY(d.total || 0)} r="5" fill="#38bdf8" stroke="#fff" strokeWidth="2" />
                    <circle cx={cx} cy={getY(d.critical || 0)} r="4" fill="#fb923c" stroke="#fff" strokeWidth="1.5" />
                  </>
                )}
              </g>
            );
          })}

          {/* X Axis Time Labels */}
          {incidentTrends.map((d: any, i: number) => {
            const step = Math.ceil(incidentTrends.length / 6);
            if (i % step === 0 || i === incidentTrends.length - 1) {
              return (
                <text
                  key={i}
                  x={getX(i)}
                  y={height - 8}
                  fill="var(--text-dim)"
                  fontSize="10"
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                >
                  {d.label}
                </text>
              );
            }
            return null;
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredData && hoveredTrendIdx !== null && (
          <div
            style={{
              position: 'absolute',
              top: '12px',
              left: `${Math.min(75, Math.max(15, (hoveredTrendIdx / incidentTrends.length) * 100))}%`,
              transform: 'translateX(-50%)',
              background: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid var(--border-accent)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
              borderRadius: '8px',
              padding: '8px 12px',
              pointerEvents: 'none',
              fontSize: '11px',
              zIndex: 10,
              minWidth: '130px',
            }}
          >
            <div style={{ color: '#fff', fontWeight: 700, marginBottom: '4px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '3px' }}>
              {hoveredData.label} ({timeRange})
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38bdf8', marginBottom: '2px' }}>
              <span>Total Incidents:</span>
              <strong>{hoveredData.total || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fb923c', marginBottom: '2px' }}>
              <span>Critical / High:</span>
              <strong>{hoveredData.critical || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#34d399' }}>
              <span>Resolved:</span>
              <strong>{hoveredData.resolved || 0}</strong>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* 1. DASHBOARD HEADER */}
      <div
        className="glass-panel"
        style={{
          padding: '24px 28px',
          background: 'radial-gradient(ellipse at 85% 20%, rgba(56, 189, 248, 0.12), transparent 70%), var(--bg-card)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
            <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={13} className="animate-pulse" /> Live Telemetry System
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
              Updated {stats?.lastUpdated ? new Date(stats.lastUpdated).toLocaleTimeString() : new Date().toLocaleTimeString()}
            </span>
            {userRole && (
              <span className="badge badge-secondary" style={{ fontSize: '11px' }}>
                Role: {getRoleDisplayName(userRole)}
              </span>
            )}
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 4px 0', color: '#fff' }}>
            Incident Analytics Dashboard
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0, maxWidth: '680px' }}>
            Real-time application health, incident intelligence, and resolution performance across distributed microservices.
          </p>
        </div>

        {/* Global Controls: Time Range Selector, Service Filter, Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Service Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} color="var(--text-muted)" />
            <select
              className="input-control"
              value={selectedService}
              onChange={e => setSelectedService(e.target.value)}
              style={{ fontSize: '12px', padding: '6px 10px', minWidth: '130px' }}
            >
              <option value="">All Services</option>
              {availableServices.map(s => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Time Range Selector */}
          <div
            style={{
              display: 'flex',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '2px',
            }}
          >
            {(['1h', '24h', '7d', '30d'] as const).map(tr => (
              <button
                key={tr}
                onClick={() => setTimeRange(tr)}
                style={{
                  padding: '5px 11px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: 'none',
                  background: timeRange === tr ? 'var(--accent-cyan)' : 'transparent',
                  color: timeRange === tr ? '#000' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}
              >
                {tr === '1h' ? '1 Hour' : tr === '24h' ? '24 Hours' : tr === '7d' ? '7 Days' : '30 Days'}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button onClick={loadData} className="btn btn-secondary" disabled={loading} style={{ fontSize: '12px', padding: '6px 12px' }}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Senior Approver Queue Banner (Visible to approver roles when requests are pending) */}
      {hasPermission(userRole, 'VIEW_APPROVALS') && pendingApprovals > 0 && (
        <div
          style={{
            background: 'linear-gradient(90deg, rgba(245, 158, 11, 0.15) 0%, rgba(168, 85, 247, 0.12) 100%)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            borderRadius: '10px',
            padding: '14px 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '8px', background: 'rgba(245, 158, 11, 0.2)', borderRadius: '8px', color: '#f59e0b' }}>
              <ShieldCheck size={20} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>
                {pendingApprovals} Remediation {pendingApprovals === 1 ? 'Approval' : 'Approvals'} Awaiting Senior Authorization
              </div>
              <div style={{ fontSize: '12px', color: '#fbbf24' }}>
                Dual-authorization guard active. High-risk remediations require explicit Senior Approver sign-off.
              </div>
            </div>
          </div>
          <Link
            to="/approvals"
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '6px 14px', background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: '#000', fontWeight: 700 }}
          >
            <span>Review Approvals Queue</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      )}

      {/* 2. PRIMARY KPI CARDS (6 CARDS GRID) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
        {/* CARD 1: Total Incidents */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Count of incidents created within the selected time range."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Total Incidents
            </span>
            <div style={{ padding: '7px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '7px', color: 'var(--accent-cyan)' }}>
              <AlertTriangle size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : totalIncidents}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', marginTop: '4px' }}>
            {totalIncTrend !== null && totalIncTrend !== undefined ? (
              <span style={{ color: totalIncTrend > 0 ? '#fb7185' : '#34d399', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                {totalIncTrend > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {totalIncTrend > 0 ? `+${totalIncTrend}%` : `${totalIncTrend}%`}
              </span>
            ) : null}
            <span style={{ color: 'var(--text-muted)' }}>vs prev {timeRange}</span>
          </div>
        </div>

        {/* CARD 2: Unresolved Tickets */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Number of tickets in Open, In Progress, or Pending Approval. Excludes Resolved and Closed."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Unresolved Tickets
            </span>
            <div style={{ padding: '7px', background: 'rgba(168, 85, 247, 0.1)', borderRadius: '7px', color: '#c084fc' }}>
              <TicketCheck size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : unresolvedTickets}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            <Link to="/tickets" style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>
              {totalTickets > 0 ? `${unresolvedTickets} active of ${totalTickets} total →` : 'All resolved/closed'}
            </Link>
          </div>
        </div>

        {/* CARD 3: Critical Errors */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Count of critical-severity log events within selected time range."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Critical Errors
            </span>
            <div style={{ padding: '7px', background: 'rgba(244, 63, 94, 0.1)', borderRadius: '7px', color: 'var(--accent-rose)' }}>
              <Flame size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: criticalErrors > 0 ? '#fb7185' : '#fff' }}>
            {loading ? '...' : criticalErrors}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', marginTop: '4px' }}>
            {critTrend !== null && critTrend !== undefined ? (
              <span style={{ color: critTrend > 0 ? '#fb7185' : '#34d399', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 600 }}>
                {critTrend > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {critTrend > 0 ? `+${critTrend}%` : `${critTrend}%`}
              </span>
            ) : null}
            <span style={{ color: 'var(--text-muted)' }}>in {timeRange} log corpus</span>
          </div>
        </div>

        {/* CARD 4: Mean Time to Detect (MTTD) */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Average time between earliest known incident-causing event (firstSeen) and incident detection (createdAt)."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Mean Time to Detect
            </span>
            <div style={{ padding: '7px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '7px', color: '#38bdf8' }}>
              <Clock size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : mttd?.available ? mttd.formatted : 'N/A'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {mttd?.available ? `Sample: ${mttd.sampleSize} incidents` : 'Insufficient detection deltas'}
          </div>
        </div>

        {/* CARD 5: Mean Time to Resolve (MTTR) */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Average time between incident detection/creation and verified resolution. Excludes unresolved incidents."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Mean Time to Resolve
            </span>
            <div style={{ padding: '7px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '7px', color: 'var(--accent-emerald)' }}>
              <CheckCircle2 size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#fff' }}>
            {loading ? '...' : mttr?.available ? mttr.formatted : 'N/A'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {mttr?.available ? `Sample: ${mttr.sampleSize} verified resolved` : '0 resolved in selected range'}
          </div>
        </div>

        {/* CARD 6: Resolution Success Rate */}
        <div
          className="glass-panel"
          style={{ padding: '20px' }}
          title="Percentage of remediation attempts that completed successfully and passed post-execution health verification."
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>
              Resolution Success Rate
            </span>
            <div style={{ padding: '7px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '7px', color: '#60a5fa' }}>
              <ShieldCheck size={16} />
            </div>
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: successRate?.available ? '#34d399' : '#fff' }}>
            {loading ? '...' : successRate?.available ? `${successRate.rate}%` : 'N/A'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {successRate?.available
              ? `${successRate.successful}/${successRate.totalAttempts} verified executions`
              : 'No remediation attempts in range'}
          </div>
        </div>
      </div>

      {/* 3. INCIDENT TRENDS CHART & MOST FAILURE-PRONE SERVICES (2-COLUMN GRID) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1.1fr', gap: '20px' }}>
        {/* Panel 1: Incident Trends Chart */}
        <div className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h2 style={{ fontSize: '16px', margin: '0 0 2px 0', color: '#fff' }}>Incident Trends</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Temporal distribution of incident clusters in {timeRange} window
              </div>
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8' }} />
                <span style={{ color: 'var(--text-muted)' }}>Total Incidents</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fb923c' }} />
                <span style={{ color: 'var(--text-muted)' }}>Critical / High</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
                <span style={{ color: 'var(--text-muted)' }}>Resolved</span>
              </div>
            </div>
          </div>

          {/* Render Responsive SVG Chart */}
          {renderTrendsChart()}
        </div>

        {/* Panel 2: Most Failure-Prone Services */}
        <div className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '16px', margin: '0 0 2px 0', color: '#fff' }}>Most Failure-Prone Services</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Ranked by incident frequency & live health state
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '280px' }}>
            {failureProneServices.length === 0 ? (
              <div style={{ padding: '40px 10px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '13px' }}>
                No microservice incidents recorded in this window.
              </div>
            ) : (
              failureProneServices.map((svc: any) => {
                const maxSvcInc = failureProneServices[0]?.incidentCount || 1;
                const pct = Math.round((svc.incidentCount / maxSvcInc) * 100);

                return (
                  <div
                    key={svc.service}
                    style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Server size={14} color="var(--accent-cyan)" />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>{svc.service}</span>
                      </div>

                      {/* Live Health Badge */}
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontWeight: 600,
                          background:
                            svc.healthStatus === 'healthy'
                              ? 'rgba(16, 185, 129, 0.15)'
                              : svc.healthStatus === 'degraded'
                              ? 'rgba(245, 158, 11, 0.15)'
                              : 'rgba(148, 163, 184, 0.15)',
                          color:
                            svc.healthStatus === 'healthy'
                              ? '#34d399'
                              : svc.healthStatus === 'degraded'
                              ? '#fbbf24'
                              : '#94a3b8',
                          border: `1px solid ${
                            svc.healthStatus === 'healthy'
                              ? 'rgba(16, 185, 129, 0.3)'
                              : svc.healthStatus === 'degraded'
                              ? 'rgba(245, 158, 11, 0.3)'
                              : 'rgba(148, 163, 184, 0.3)'
                          }`,
                        }}
                      >
                        {svc.healthStatus === 'healthy'
                          ? '● Healthy'
                          : svc.healthStatus === 'degraded'
                          ? '● Degraded'
                          : '● Unknown'}
                      </span>
                    </div>

                    {/* Progress distribution bar */}
                    <div style={{ width: '100%', height: '5px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: 'var(--grad-primary)', borderRadius: '3px' }} />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-dim)' }}>
                      <span>
                        <strong style={{ color: '#fff' }}>{svc.incidentCount}</strong> {svc.incidentCount === 1 ? 'incident' : 'incidents'}
                        {svc.criticalCount > 0 && <span style={{ color: '#fb7185' }}> ({svc.criticalCount} critical)</span>}
                      </span>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <Link to={`/incidents?service=${svc.service}`} style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>
                          View Incidents &rarr;
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 4. SEVERITY DISTRIBUTION & APPLICATION UPTIME (2-COLUMN GRID) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '20px' }}>
        {/* Severity Distribution Panel */}
        <div className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 2px 0', color: '#fff' }}>Incident Severity Distribution</h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Categorization by impact classification taxonomy</div>
          </div>

          {/* Segmented Progress Bar */}
          <div style={{ display: 'flex', width: '100%', height: '10px', borderRadius: '5px', overflow: 'hidden', gap: '2px' }}>
            {severityBreakdown.map((s: any) =>
              s.count > 0 ? (
                <div
                  key={s.severity}
                  style={{
                    width: `${s.percentage}%`,
                    background: s.color,
                    transition: 'all 0.3s',
                  }}
                  title={`${s.label}: ${s.count} (${s.percentage}%)`}
                />
              ) : null
            )}
            {severityBreakdown.every((s: any) => s.count === 0) && (
              <div style={{ width: '100%', background: 'rgba(255, 255, 255, 0.08)' }} />
            )}
          </div>

          {/* Detailed Severity Breakdown Rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {severityBreakdown.map((s: any) => (
              <div
                key={s.severity}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  fontSize: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: s.color }} />
                  <span style={{ color: '#fff', fontWeight: 600 }}>{s.label}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{s.percentage}%</span>
                  <span style={{ fontWeight: 700, color: '#fff', minWidth: '24px', textAlign: 'right' }}>{s.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Application Availability / Service Uptime Panel */}
        <div className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ fontSize: '16px', margin: '0 0 2px 0', color: '#fff' }}>Application Availability & Service Uptime</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Target service: <strong style={{ color: 'var(--accent-cyan)' }}>{uptimeData.service || 'order-service'}</strong>
              </div>
            </div>

            {uptimeData.isAvailable && (
              <span
                style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: uptimeData.currentHealth === 'healthy' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                  color: uptimeData.currentHealth === 'healthy' ? '#34d399' : '#fb7185',
                  border: `1px solid ${uptimeData.currentHealth === 'healthy' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                }}
              >
                {uptimeData.currentHealth === 'healthy' ? 'PROBE HEALTHY' : 'PROBE DEGRADED'}
              </span>
            )}
          </div>

          {uptimeData.isAvailable ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
                <span style={{ fontSize: '36px', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
                  {uptimeData.availabilityPct}%
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  measured uptime in {timeRange}
                </span>
              </div>

              {/* Simulated Uptime Timeline Blocks */}
              <div style={{ display: 'flex', gap: '3px', width: '100%' }}>
                {Array.from({ length: 30 }).map((_, idx) => {
                  const isDegraded = uptimeData.currentHealth === 'degraded' && idx >= 27;
                  return (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        height: '24px',
                        borderRadius: '3px',
                        background: isDegraded ? '#fb7185' : '#10b981',
                        opacity: isDegraded ? 0.9 : 0.75 + (idx % 3) * 0.1,
                      }}
                      title={isDegraded ? 'Service degraded' : 'Service healthy (200 OK)'}
                    />
                  );
                })}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)' }}>
                <span>Healthy Duration: <strong style={{ color: '#fff' }}>{uptimeData.healthyDuration}</strong></span>
                <span>Unhealthy Duration: <strong style={{ color: '#fb7185' }}>{uptimeData.unhealthyDuration}</strong></span>
              </div>

              <div style={{ fontSize: '11px', color: 'var(--text-dim)', background: 'rgba(255, 255, 255, 0.02)', padding: '8px 12px', borderRadius: '6px' }}>
                <Info size={12} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />
                {uptimeData.telemetryNote}
              </div>
            </>
          ) : (
            <div style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-dim)' }}>
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>
                Not Available
              </div>
              <div style={{ fontSize: '12px', maxWidth: '380px', margin: '0 auto' }}>
                {uptimeData.telemetryNote || 'Dedicated synthetic monitoring ping telemetry is not configured for this service.'}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 5. RECENT INCIDENTS TABLE */}
      <div className="glass-panel" style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 2px 0', color: '#fff' }}>Recent Incidents</h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Operational incidents requiring investigation, root-cause analysis, and safe remediation
            </div>
          </div>
          <Link to="/incidents" className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 12px' }}>
            <span>View All in Incidents Feed</span>
            <ExternalLink size={13} />
          </Link>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Incident ID</th>
                <th>Incident Title</th>
                <th style={{ width: '130px' }}>Service</th>
                <th style={{ width: '90px' }}>Severity</th>
                <th style={{ width: '130px' }}>Status</th>
                <th style={{ width: '110px' }}>Detected</th>
                <th style={{ width: '110px' }}>Assignee</th>
                <th style={{ width: '100px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)' }}>
                    No recent incidents matching selected time window and service filter.
                  </td>
                </tr>
              ) : (
                recentIncidents.map((inc: any) => (
                  <tr key={inc.id}>
                    <td>
                      <Link
                        to={`/incidents/${inc.id}`}
                        style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)', textDecoration: 'none' }}
                      >
                        {inc.id.slice(0, 10)}...
                      </Link>
                    </td>
                    <td style={{ fontWeight: 600, color: '#fff' }}>
                      {inc.title}
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{inc.service}</span>
                    </td>
                    <td>{renderSeverityBadge(inc.severity)}</td>
                    <td>{renderIncidentStatusBadge(inc.status)}</td>
                    <td style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      {inc.createdAt ? new Date(inc.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                    </td>
                    <td style={{ fontSize: '12px', color: inc.assignee ? '#fff' : 'var(--text-dim)' }}>
                      {inc.assignee || 'Unassigned'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '11px', gap: '4px' }}
                      >
                        <span>Investigate</span>
                        <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. ADMIN-ONLY CHAOS INJECTION & FAULT SIMULATION (Preserved existing capability) */}
      {userRole === 'admin' && (
        <div
          className="glass-panel"
          style={{
            padding: '22px',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            background: 'radial-gradient(ellipse at 95% 50%, rgba(244, 63, 94, 0.08), transparent 70%), var(--bg-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Flame size={18} color="var(--accent-rose)" />
                <h2 style={{ fontSize: '16px', margin: 0, color: '#fff' }}>Chaos & Failure Injection Engine</h2>
                <span className="badge badge-critical" style={{ fontSize: '10px' }}>ADMIN RESTRICTED</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Trigger controlled microservice failures on target demo app to test AI RCA and allow-listed remediation
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ fontSize: '12px', color: demoStatus?.active_fault ? '#fb7185' : '#34d399', fontWeight: 600 }}>
                {demoStatus?.active_fault ? `Active Outage: ${demoStatus.active_fault}` : 'Target Service Healthy'}
              </div>
              {demoStatus?.active_fault && (
                <button
                  className="btn btn-secondary"
                  disabled={simulating}
                  onClick={handleResetFault}
                  style={{ fontSize: '12px', padding: '5px 12px', color: '#34d399', borderColor: '#34d399' }}
                >
                  <RotateCcw size={13} />
                  <span>Clear Fault</span>
                </button>
              )}
            </div>
          </div>

          {simMessage && (
            <div
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                background: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: 'var(--accent-cyan)',
              }}
            >
              {simMessage}
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {[
              { key: 'db_connection_timeout', label: 'DB Pool Timeout Spike', service: 'order-service' },
              { key: 'memory_leak', label: 'Heap Saturation OOM', service: 'payment-service' },
              { key: 'bad_config_deploy', label: 'Missing Env Var Deploy', service: 'inventory-service' },
              { key: 'auth_failure_spike', label: 'Credential Anomaly Spike', service: 'auth-service' },
              { key: 'downstream_503', label: 'Downstream 503 Outage', service: 'billing-gateway' },
            ].map(f => (
              <button
                key={f.key}
                disabled={simulating || demoStatus?.active_fault === f.key}
                onClick={() => handleInjectFault(f.key, f.label)}
                className="btn btn-secondary"
                style={{
                  fontSize: '12px',
                  padding: '7px 13px',
                  background: demoStatus?.active_fault === f.key ? 'rgba(244, 63, 94, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  borderColor: demoStatus?.active_fault === f.key ? '#f43f5e' : 'var(--border-subtle)',
                  color: demoStatus?.active_fault === f.key ? '#fb7185' : 'var(--text-main)',
                }}
              >
                <Zap size={13} color={demoStatus?.active_fault === f.key ? '#fb7185' : 'var(--accent-amber)'} />
                <span>{f.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
