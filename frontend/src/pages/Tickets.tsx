import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, getStoredUser } from '../api/client';
import { Ticket, TicketPriority, TicketStatus } from '../types';
import { hasPermission } from '../auth/permissions';
import {
  TicketCheck,
  MessageSquare,
  User as UserIcon,
  RefreshCw,
  Send,
  CheckCircle2,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  CircleDot,
  PlayCircle,
  ShieldAlert,
  CheckCheck,
  AlertTriangle,
  RotateCcw,
  Clock,
  Filter,
  Check,
  Zap,
  ArrowRight,
  Activity,
  AlertCircle,
  XCircle,
  Lock
} from 'lucide-react';

interface StatusConfig {
  label: string;
  badgeClass: string;
  color: string;
  bg: string;
  border: string;
  icon: React.ReactNode;
  description: string;
  displayStatusText: string;
}

const STATUS_CONFIG: Record<TicketStatus, StatusConfig> = {
  open: {
    label: 'Open',
    badgeClass: 'badge-status-open',
    color: '#60a5fa', // Blue
    bg: 'rgba(59, 130, 246, 0.16)',
    border: 'rgba(59, 130, 246, 0.45)',
    icon: <CircleDot size={12} />,
    description: 'Ticket is open and awaiting triage, assignment, and root cause investigation.',
    displayStatusText: 'Currently Open',
  },
  in_progress: {
    label: 'In Progress',
    badgeClass: 'badge-status-in-progress',
    color: '#fb923c', // Orange
    bg: 'rgba(249, 115, 22, 0.16)',
    border: 'rgba(249, 115, 22, 0.45)',
    icon: <PlayCircle size={12} />,
    description: 'Active root-cause investigation and remediation preparation underway.',
    displayStatusText: 'Currently In Progress',
  },
  pending_approval: {
    label: 'Pending Approval',
    badgeClass: 'badge-status-pending-approval',
    color: '#c084fc', // Purple / Amber
    bg: 'rgba(168, 85, 247, 0.16)',
    border: 'rgba(168, 85, 247, 0.45)',
    icon: <ShieldAlert size={12} />,
    description: 'Remediation request submitted. Awaiting dual-authorization decision from Senior Approver.',
    displayStatusText: 'Pending Approval',
  },
  verifying: {
    label: 'Verifying',
    badgeClass: 'badge-status-verifying',
    color: '#38bdf8', // Cyan
    bg: 'rgba(56, 189, 248, 0.16)',
    border: 'rgba(56, 189, 248, 0.45)',
    icon: <RefreshCw size={12} className="animate-spin" />,
    description: 'Post-remediation automated health checks are confirming recovery of target service.',
    displayStatusText: 'Currently Verifying Recovery',
  },
  resolved: {
    label: 'Resolved',
    badgeClass: 'badge-status-resolved',
    color: '#34d399', // Green
    bg: 'rgba(16, 185, 129, 0.16)',
    border: 'rgba(16, 185, 129, 0.45)',
    icon: <CheckCircle2 size={12} />,
    description: 'Remediation executed and verified. The operational issue has been resolved.',
    displayStatusText: 'Currently Resolved',
  },
  closed: {
    label: 'Closed',
    badgeClass: 'badge-status-closed',
    color: '#94a3b8', // Neutral gray
    bg: 'rgba(148, 163, 184, 0.14)',
    border: 'rgba(148, 163, 184, 0.35)',
    icon: <CheckCheck size={12} />,
    description: 'Ticket lifecycle concluded. Archived in append-only system audit log.',
    displayStatusText: 'Currently Closed',
  },
  escalated: {
    label: 'Escalated',
    badgeClass: 'badge-status-escalated',
    color: '#fb7185', // Crimson
    bg: 'rgba(244, 63, 94, 0.16)',
    border: 'rgba(244, 63, 94, 0.45)',
    icon: <AlertTriangle size={12} />,
    description: 'Incident escalated due to failed health recovery verification, policy conflict, or severe outage.',
    displayStatusText: 'Currently Escalated',
  },
  reopened: {
    label: 'Reopened',
    badgeClass: 'badge-status-reopened',
    color: '#e879f9', // Violet
    bg: 'rgba(217, 70, 239, 0.16)',
    border: 'rgba(217, 70, 239, 0.45)',
    icon: <RotateCcw size={12} />,
    description: 'Ticket reopened due to recurrence of symptoms or secondary anomalies.',
    displayStatusText: 'Currently Reopened',
  },
};

// Valid lifecycle transitions enforced by backend policy
const BACKEND_VALID_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  open: ['in_progress', 'escalated', 'closed'],
  in_progress: ['pending_approval', 'verifying', 'resolved', 'escalated'],
  pending_approval: ['in_progress', 'verifying', 'escalated'],
  verifying: ['resolved', 'escalated', 'in_progress'],
  resolved: ['closed', 'reopened'],
  closed: ['reopened'],
  escalated: ['in_progress', 'closed'],
  reopened: ['in_progress', 'escalated'],
};

export const Tickets: React.FC = () => {
  const currentUser = getStoredUser();
  const userRole = currentUser?.role || 'support_engineer';

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'active' | 'all' | 'open' | 'in_progress' | 'pending_approval' | 'resolved' | 'closed'>('active');
  const [searchQuery, setSearchQuery] = useState('');
  const [commentText, setCommentText] = useState('');
  const [assigneeInput, setAssigneeInput] = useState('');
  const [showAdminOverride, setShowAdminOverride] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets();
      setTickets(data);
      if (selectedTicket) {
        const refreshed = data.find(t => t.id === selectedTicket.id);
        if (refreshed) setSelectedTicket(refreshed);
      }
    } catch (e: any) {
      console.error('Failed to fetch tickets:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 5000);
    return () => clearInterval(interval);
  }, []);

  // Update status handler with authoritative backend sync
  const handleStatusChange = async (ticketId: string, newStatus: string) => {
    setIsUpdatingStatus(true);
    setStatusError(null);
    try {
      const updated = await api.updateTicketStatus(ticketId, newStatus);
      // Immediately reflect persisted status in UI to prevent stale states
      setSelectedTicket(updated);
      setTickets(prev => prev.map(t => (t.id === updated.id ? updated : t)));
      // Re-fetch to sync backend authoritative state
      await fetchTickets();
    } catch (e: any) {
      setStatusError(e.message || `Failed to transition status to ${newStatus}`);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !assigneeInput.trim()) return;
    try {
      const updated = await api.assignTicket(selectedTicket.id, assigneeInput.trim());
      setSelectedTicket(updated);
      setTickets(prev => prev.map(t => (t.id === updated.id ? updated : t)));
      setAssigneeInput('');
      await fetchTickets();
    } catch (e: any) {
      setStatusError(e.message);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !commentText.trim()) return;
    try {
      const updated = await api.addTicketComment(selectedTicket.id, commentText.trim());
      setSelectedTicket(updated);
      setTickets(prev => prev.map(t => (t.id === updated.id ? updated : t)));
      setCommentText('');
      await fetchTickets();
    } catch (e: any) {
      setStatusError(e.message);
    }
  };

  const getPriorityBadge = (p: TicketPriority) => {
    switch (p) {
      case 'P1': return <span className="badge badge-critical">P1 Critical</span>;
      case 'P2': return <span className="badge badge-error">P2 High</span>;
      case 'P3': return <span className="badge badge-warn">P3 Medium</span>;
      case 'P4': return <span className="badge badge-info">P4 Low</span>;
    }
  };

  // Reusable, prominent Status Badge
  const getStatusBadge = (s: TicketStatus, size: 'sm' | 'md' = 'sm') => {
    const cfg = STATUS_CONFIG[s] || STATUS_CONFIG.open;
    return (
      <span
        className={`badge ${cfg.badgeClass}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: size === 'md' ? '4px 12px' : '3px 9px',
          fontSize: size === 'md' ? '12px' : '11px',
          fontWeight: 600,
          borderRadius: '6px',
          letterSpacing: '0.02em',
          textTransform: 'none',
          boxShadow: size === 'md' ? `0 0 12px ${cfg.bg}` : 'none',
        }}
      >
        {cfg.icon}
        <span>{cfg.label}</span>
      </span>
    );
  };

  // Accurate Ticket Counts
  // Active tickets must strictly exclude 'resolved' and 'closed'
  const activeTickets = tickets.filter(t => t.status !== 'resolved' && t.status !== 'closed');
  const activeCount = activeTickets.length;
  const totalCount = tickets.length;
  const openCount = tickets.filter(t => t.status === 'open').length;
  const inProgressCount = tickets.filter(t => t.status === 'in_progress').length;
  const pendingApprovalCount = tickets.filter(t => t.status === 'pending_approval').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;
  const closedCount = tickets.filter(t => t.status === 'closed').length;

  // Filtered tickets based on active filter and optional search query
  const displayedTickets = tickets.filter(t => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match = t.id.toLowerCase().includes(q) || t.title.toLowerCase().includes(q);
      if (!match) return false;
    }
    if (filter === 'active') return t.status !== 'resolved' && t.status !== 'closed';
    if (filter === 'all') return true;
    return t.status === filter;
  });

  // Allowed transitions for current user role and current status
  const getAllowedTransitions = (currStatus: TicketStatus): TicketStatus[] => {
    if ((userRole as string) === 'admin' && showAdminOverride) {
      return ['open', 'in_progress', 'pending_approval', 'verifying', 'resolved', 'closed', 'escalated', 'reopened'].filter(
        st => st !== currStatus
      ) as TicketStatus[];
    }

    const standardAllowed = BACKEND_VALID_TRANSITIONS[currStatus] || [];

    // Filter by role safety:
    // Support engineers cannot transition directly to verifying (verifying is managed by automated health checks)
    if (userRole === 'support_engineer') {
      return standardAllowed.filter(st => st !== 'verifying');
    }

    return standardAllowed;
  };

  // Compact Visual Lifecycle Indicator Builder
  const renderLifecycleStepper = (ticket: Ticket) => {
    // Determine whether ticket has ever entered pending_approval
    // "Show Pending Approval only when the ticket actually enters that state; it should not be treated as mandatory for every ticket."
    const hasEnteredApproval =
      ticket.status === 'pending_approval' ||
      Boolean(
        ticket.comments?.some(
          c =>
            c.text.toLowerCase().includes('approval') ||
            c.text.toLowerCase().includes('pending_approval')
        )
      );

    const stages: Array<{ key: TicketStatus; label: string }> = [
      { key: 'open', label: 'Open' },
      { key: 'in_progress', label: 'In Progress' },
      ...(hasEnteredApproval ? [{ key: 'pending_approval' as TicketStatus, label: 'Pending Approval' }] : []),
      { key: 'resolved', label: 'Resolved' },
      { key: 'closed', label: 'Closed' },
    ];

    const stageKeys = stages.map(s => s.key);
    const currKey = ticket.status;

    // Determine current step index
    let currentStepIdx = stageKeys.indexOf(currKey);
    let isSpecialState = false;
    let specialLabel = '';

    if (currKey === 'verifying') {
      // verifying sits between in_progress/pending_approval and resolved
      currentStepIdx = stageKeys.indexOf('resolved') - 0.5;
      isSpecialState = true;
      specialLabel = 'Verifying Recovery';
    } else if (currKey === 'escalated') {
      currentStepIdx = Math.max(0, stageKeys.indexOf('in_progress'));
      isSpecialState = true;
      specialLabel = 'Escalated / Paused';
    } else if (currKey === 'reopened') {
      currentStepIdx = stageKeys.indexOf('in_progress');
      isSpecialState = true;
      specialLabel = 'Reopened';
    }

    // Check if comments indicate rejected / failed remediation
    const hasFailedOrRejectedComment = ticket.comments?.some(c => {
      const lower = c.text.toLowerCase();
      return lower.includes('rejected') || lower.includes('failed') || lower.includes('error');
    });

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {/* Stepper track */}
        <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '6px' }}>
          {stages.map((stage, idx) => {
            const isCompleted =
              currKey === 'closed'
                ? true
                : currKey === 'resolved'
                ? stage.key !== 'closed'
                : idx < currentStepIdx;

            const isCurrent =
              currKey === stage.key ||
              (currKey === 'closed' && stage.key === 'closed') ||
              (currKey === 'resolved' && stage.key === 'resolved');

            const isFuture = !isCompleted && !isCurrent;
            const cfg = STATUS_CONFIG[stage.key];

            return (
              <React.Fragment key={stage.key}>
                {/* Step Item */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    flex: '1 0 auto',
                  }}
                >
                  {/* Step Circle */}
                  <div
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '11px',
                      fontWeight: 700,
                      background: isCurrent
                        ? cfg.bg
                        : isCompleted
                        ? 'rgba(16, 185, 129, 0.2)'
                        : 'rgba(255, 255, 255, 0.04)',
                      border: isCurrent
                        ? `2px solid ${cfg.color}`
                        : isCompleted
                        ? '2px solid #10b981'
                        : '1px solid rgba(255, 255, 255, 0.15)',
                      color: isCurrent ? cfg.color : isCompleted ? '#34d399' : 'var(--text-dim)',
                      boxShadow: isCurrent ? `0 0 10px ${cfg.bg}` : 'none',
                      transition: 'all 0.2s',
                    }}
                  >
                    {isCompleted ? <Check size={13} strokeWidth={3} /> : idx + 1}
                  </div>

                  {/* Step Label */}
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: isCurrent ? 700 : isCompleted ? 600 : 400,
                      color: isCurrent ? '#fff' : isCompleted ? '#cbd5e1' : 'var(--text-dim)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {stage.label}
                    {isCurrent && (
                      <span
                        style={{
                          marginLeft: '4px',
                          fontSize: '10px',
                          padding: '1px 5px',
                          borderRadius: '4px',
                          background: cfg.bg,
                          color: cfg.color,
                        }}
                      >
                        Current
                      </span>
                    )}
                  </div>
                </div>

                {/* Connector line between steps */}
                {idx < stages.length - 1 && (
                  <div
                    style={{
                      flex: 1,
                      height: '2px',
                      background:
                        idx < currentStepIdx || (currKey === 'closed' && idx < stages.length)
                          ? '#10b981'
                          : isCurrent
                          ? `linear-gradient(90deg, ${cfg.color}, rgba(255, 255, 255, 0.1))`
                          : 'rgba(255, 255, 255, 0.1)',
                      minWidth: '12px',
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Dynamic Contextual Path / Anomaly Warnings */}
        {!hasEnteredApproval && (ticket.status === 'resolved' || ticket.status === 'closed') && (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>✓ Direct Resolution Path</span>
            <span>(Standard approval cycle bypassed by authorized Approver)</span>
          </div>
        )}

        {isSpecialState && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              background:
                ticket.status === 'escalated'
                  ? 'rgba(244, 63, 94, 0.1)'
                  : ticket.status === 'verifying'
                  ? 'rgba(56, 189, 248, 0.1)'
                  : 'rgba(217, 70, 239, 0.1)',
              border:
                ticket.status === 'escalated'
                  ? '1px solid rgba(244, 63, 94, 0.3)'
                  : ticket.status === 'verifying'
                  ? '1px solid rgba(56, 189, 248, 0.3)'
                  : '1px solid rgba(217, 70, 239, 0.3)',
              color:
                ticket.status === 'escalated'
                  ? '#fb7185'
                  : ticket.status === 'verifying'
                  ? '#38bdf8'
                  : '#e879f9',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {ticket.status === 'escalated' ? (
              <AlertTriangle size={15} />
            ) : ticket.status === 'verifying' ? (
              <RefreshCw size={15} className="animate-spin" />
            ) : (
              <RotateCcw size={15} />
            )}
            <span>
              <strong>{specialLabel}:</strong> {STATUS_CONFIG[ticket.status].description}
            </span>
          </div>
        )}

        {/* Explain rejected or failed remediation request without falsely advancing */}
        {hasFailedOrRejectedComment && ticket.status !== 'resolved' && ticket.status !== 'closed' && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              background: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              color: '#fbbf24',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={15} />
            <span>
              <strong>Notice:</strong> Previous remediation request was rejected or failed. The ticket was not advanced and remains in its current state.
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px', color: '#fff' }}>
            Incident Tickets & Resolution Board
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Auto-created operational tickets linked to correlated log incidents with strict lifecycle enforcement.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button onClick={fetchTickets} className="btn btn-secondary" disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Summary Counters Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '12px',
        }}
      >
        <div
          onClick={() => setFilter('active')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'active' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
            background: filter === 'active' ? 'rgba(56, 189, 248, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Active Tickets
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
            {activeCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Excludes Resolved/Closed</div>
        </div>

        <div
          onClick={() => setFilter('open')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'open' ? '1px solid rgba(59, 130, 246, 0.6)' : '1px solid var(--border-subtle)',
            background: filter === 'open' ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Open
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#60a5fa', marginTop: '2px' }}>
            {openCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Awaiting triage</div>
        </div>

        <div
          onClick={() => setFilter('in_progress')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'in_progress' ? '1px solid rgba(249, 115, 22, 0.6)' : '1px solid var(--border-subtle)',
            background: filter === 'in_progress' ? 'rgba(249, 115, 22, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            In Progress
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#fb923c', marginTop: '2px' }}>
            {inProgressCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Active investigation</div>
        </div>

        <div
          onClick={() => setFilter('pending_approval')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'pending_approval' ? '1px solid rgba(168, 85, 247, 0.6)' : '1px solid var(--border-subtle)',
            background: filter === 'pending_approval' ? 'rgba(168, 85, 247, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Pending Approval
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#c084fc', marginTop: '2px' }}>
            {pendingApprovalCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Awaiting Senior Approver</div>
        </div>

        <div
          onClick={() => setFilter('resolved')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'resolved' ? '1px solid rgba(16, 185, 129, 0.6)' : '1px solid var(--border-subtle)',
            background: filter === 'resolved' ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Resolved
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
            {resolvedCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Remediation verified</div>
        </div>

        <div
          onClick={() => setFilter('closed')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'closed' ? '1px solid rgba(148, 163, 184, 0.6)' : '1px solid var(--border-subtle)',
            background: filter === 'closed' ? 'rgba(148, 163, 184, 0.12)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Closed
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#94a3b8', marginTop: '2px' }}>
            {closedCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Archived in history</div>
        </div>

        <div
          onClick={() => setFilter('all')}
          className="glass-panel"
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            border: filter === 'all' ? '1px solid rgba(255, 255, 255, 0.4)' : '1px solid var(--border-subtle)',
            background: filter === 'all' ? 'rgba(255, 255, 255, 0.08)' : 'var(--bg-card)',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            All Tickets
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#fff', marginTop: '2px' }}>
            {totalCount}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>Total recorded</div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedTicket ? '1.15fr 1.1fr' : '1fr', gap: '20px' }}>
        {/* Ticket List Panel */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Header & Filter Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TicketCheck size={18} color="var(--accent-cyan)" />
              <span>
                {filter === 'active'
                  ? `Active Tickets (${activeCount})`
                  : filter === 'all'
                  ? `All Tickets (${totalCount})`
                  : `${STATUS_CONFIG[filter].label} Tickets (${displayedTickets.length})`}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontWeight: 400 }}>
                (Total: {totalCount})
              </span>
            </h3>

            {/* Search Input */}
            <input
              type="text"
              className="input-control"
              placeholder="Search by ID or title..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ width: '200px', fontSize: '12px', padding: '6px 10px' }}
            />
          </div>

          {/* Filter Pills Bar */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {[
              { key: 'active', label: `Active (${activeCount})` },
              { key: 'all', label: `All (${totalCount})` },
              { key: 'open', label: `Open (${openCount})` },
              { key: 'in_progress', label: `In Progress (${inProgressCount})` },
              { key: 'pending_approval', label: `Pending Approval (${pendingApprovalCount})` },
              { key: 'resolved', label: `Resolved (${resolvedCount})` },
              { key: 'closed', label: `Closed (${closedCount})` },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key as any)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '20px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border:
                    filter === tab.key
                      ? '1px solid var(--accent-cyan)'
                      : '1px solid rgba(255, 255, 255, 0.08)',
                  background:
                    filter === tab.key ? 'rgba(56, 189, 248, 0.16)' : 'rgba(255, 255, 255, 0.03)',
                  color: filter === tab.key ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Ticket Cards List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '720px', overflowY: 'auto' }}>
            {displayedTickets.length === 0 ? (
              <div
                style={{
                  padding: '40px 20px',
                  textAlign: 'center',
                  color: 'var(--text-dim)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  borderRadius: '8px',
                  border: '1px dashed var(--border-subtle)',
                }}
              >
                <TicketCheck size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>No tickets found</div>
                <div style={{ fontSize: '12px', marginTop: '4px' }}>
                  {filter === 'active'
                    ? 'All tickets are currently resolved or closed.'
                    : 'No tickets match the selected filter or search query.'}
                </div>
              </div>
            ) : (
              displayedTickets.map(t => {
                const isSelected = selectedTicket?.id === t.id;
                const statusCfg = STATUS_CONFIG[t.status] || STATUS_CONFIG.open;

                return (
                  <div
                    key={t.id}
                    onClick={() => {
                      setSelectedTicket(t);
                      setStatusError(null);
                    }}
                    style={{
                      padding: '14px 18px',
                      background: isSelected ? 'rgba(56, 189, 248, 0.09)' : 'var(--bg-secondary)',
                      border: isSelected
                        ? '1px solid var(--border-accent)'
                        : '1px solid var(--border-subtle)',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      boxShadow: isSelected ? '0 4px 20px rgba(0, 0, 0, 0.4)' : 'none',
                    }}
                  >
                    {/* Top Row: Ticket ID + Priority Badge + Prominent Status Badge */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '8px',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 700,
                            fontSize: '13px',
                            color: 'var(--accent-cyan)',
                          }}
                        >
                          {t.id}
                        </span>
                        {getPriorityBadge(t.priority)}
                        {/* Prominently highlighted status badge */}
                        {getStatusBadge(t.status, 'sm')}
                      </div>

                      {/* Timestamp */}
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                        {new Date(t.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    {/* Ticket Title */}
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 600,
                        color: '#fff',
                        marginBottom: '8px',
                        lineHeight: 1.4,
                      }}
                    >
                      {t.title}
                    </div>

                    {/* Bottom Metadata */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '12px',
                        color: 'var(--text-dim)',
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <UserIcon size={12} />
                        <span>
                          Assignee: <strong style={{ color: t.assignee ? '#fff' : 'var(--text-dim)' }}>{t.assignee || 'Unassigned'}</strong>
                        </span>
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MessageSquare size={12} /> {t.comments?.length || 0}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Ticket Details Panel */}
        {selectedTicket && (
          <div
            className="glass-panel"
            style={{
              padding: '22px',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px',
              position: 'sticky',
              top: '24px',
              maxHeight: 'calc(100vh - 48px)',
              overflowY: 'auto',
            }}
          >
            {/* Header: Title + Badges + Close button */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      fontSize: '15px',
                      color: 'var(--accent-cyan)',
                    }}
                  >
                    {selectedTicket.id}
                  </span>
                  {getPriorityBadge(selectedTicket.priority)}
                  {/* Status badge beside priority and title */}
                  {getStatusBadge(selectedTicket.status, 'md')}
                </div>
                <h3 style={{ fontSize: '17px', margin: 0, color: '#fff', lineHeight: 1.4 }}>
                  {selectedTicket.title}
                </h3>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setSelectedTicket(null)}
              >
                Close
              </button>
            </div>

            {/* Error Banner */}
            {statusError && (
              <div
                style={{
                  background: 'rgba(244, 63, 94, 0.12)',
                  border: '1px solid rgba(244, 63, 94, 0.4)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#fb7185',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <XCircle size={16} />
                <span style={{ flex: 1 }}>{statusError}</span>
                <button
                  onClick={() => setStatusError(null)}
                  style={{ background: 'transparent', border: 'none', color: '#fb7185', cursor: 'pointer', fontSize: '11px' }}
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* SECTION: Current Ticket Status & Lifecycle Progress */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: `1px solid ${STATUS_CONFIG[selectedTicket.status].border}`,
                borderRadius: '10px',
                padding: '16px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Current Ticket Status
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                  Updated {new Date(selectedTicket.updatedAt).toLocaleTimeString()}
                </span>
              </div>

              {/* Prominent Current Lifecycle State Text */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    background: STATUS_CONFIG[selectedTicket.status].bg,
                    border: `1px solid ${STATUS_CONFIG[selectedTicket.status].border}`,
                    color: STATUS_CONFIG[selectedTicket.status].color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {STATUS_CONFIG[selectedTicket.status].icon}
                </div>
                <div>
                  <div style={{ fontSize: '17px', fontWeight: 700, color: STATUS_CONFIG[selectedTicket.status].color }}>
                    {STATUS_CONFIG[selectedTicket.status].displayStatusText}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {STATUS_CONFIG[selectedTicket.status].description}
                  </div>
                </div>
              </div>

              {/* Compact Visual Lifecycle Stepper */}
              <div style={{ marginTop: '4px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                {renderLifecycleStepper(selectedTicket)}
              </div>
            </div>

            {/* Incident Link & Direct Remediation Bypass Action */}
            {selectedTicket.incidentId && (
              <div
                style={{
                  background: 'rgba(56, 189, 248, 0.08)',
                  border: '1px solid var(--border-accent)',
                  borderRadius: '8px',
                  padding: '14px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={16} color="var(--accent-cyan)" />
                  <span style={{ fontSize: '13px', color: '#fff' }}>
                    Correlated Incident:{' '}
                    <strong style={{ fontFamily: 'var(--font-mono)' }}>
                      {selectedTicket.incidentId.slice(0, 12)}...
                    </strong>
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {/* Approver Action: Direct Issue Resolution Bypass */}
                  {userRole === 'approver' &&
                    selectedTicket.status !== 'resolved' &&
                    selectedTicket.status !== 'closed' && (
                      <Link
                        to={`/incidents/${selectedTicket.incidentId}`}
                        className="btn btn-success"
                        style={{
                          padding: '6px 12px',
                          fontSize: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <Zap size={14} />
                        <span>Resolve Issue Directly</span>
                      </Link>
                    )}

                  {/* If Pending Approval: Link to Approvals Queue */}
                  {selectedTicket.status === 'pending_approval' && (
                    <Link
                      to="/approvals"
                      className="btn btn-secondary"
                      style={{
                        padding: '6px 12px',
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        color: '#c084fc',
                        borderColor: 'rgba(168, 85, 247, 0.4)',
                      }}
                    >
                      <ShieldCheck size={14} />
                      <span>Review in Approvals</span>
                    </Link>
                  )}

                  {/* General link to Root Cause Analysis */}
                  <Link
                    to={`/incidents/${selectedTicket.incidentId}`}
                    className="btn btn-primary"
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <span>View AI RCA Investigation</span>
                    <ExternalLink size={13} />
                  </Link>
                </div>
              </div>
            )}

            {/* Lifecycle Controls / Valid Transitions */}
            <div
              style={{
                background: 'var(--bg-secondary)',
                padding: '14px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '10px',
                }}
              >
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: 'var(--text-dim)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  Transition Ticket State
                </span>

                {(userRole as string) === 'admin' && (
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '11px',
                      color: 'var(--accent-purple)',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={showAdminOverride}
                      onChange={e => setShowAdminOverride(e.target.checked)}
                    />
                    <span>Admin Override Mode</span>
                  </label>
                )}
              </div>

              {/* State Transition Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {getAllowedTransitions(selectedTicket.status).length === 0 ? (
                  <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                    No valid manual transitions available from current state.
                  </div>
                ) : (
                  getAllowedTransitions(selectedTicket.status).map(targetStatus => {
                    const targetCfg = STATUS_CONFIG[targetStatus];
                    return (
                      <button
                        key={targetStatus}
                        className="btn btn-secondary"
                        disabled={isUpdatingStatus}
                        style={{
                          fontSize: '12px',
                          padding: '6px 12px',
                          border: `1px solid ${targetCfg.border}`,
                          background: targetCfg.bg,
                          color: targetCfg.color,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                        onClick={() => handleStatusChange(selectedTicket.id, targetStatus)}
                      >
                        {targetCfg.icon}
                        <span>Transition to {targetCfg.label}</span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Assignment Form */}
            <form onSubmit={handleAssign} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="text"
                className="input-control"
                placeholder="Assign to engineer (e.g. support, approver, admin)..."
                value={assigneeInput}
                onChange={e => setAssigneeInput(e.target.value)}
                style={{ fontSize: '13px' }}
              />
              <button
                type="submit"
                className="btn btn-primary"
                style={{ whiteSpace: 'nowrap', fontSize: '12px' }}
                disabled={!assigneeInput.trim()}
              >
                Assign
              </button>
            </form>

            {/* Comments & Activity Thread */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <MessageSquare size={14} />
                <span>Activity & Comments ({selectedTicket.comments?.length || 0})</span>
              </div>

              <div
                style={{
                  maxHeight: '220px',
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {selectedTicket.comments?.length === 0 ? (
                  <div
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-dim)',
                      padding: '12px',
                      background: 'rgba(255, 255, 255, 0.02)',
                      borderRadius: '6px',
                      textAlign: 'center',
                    }}
                  >
                    No activity notes yet. Post an update or remediation log below.
                  </div>
                ) : (
                  selectedTicket.comments?.map(c => (
                    <div
                      key={c.id}
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        fontSize: '13px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: 'var(--text-dim)',
                          marginBottom: '4px',
                        }}
                      >
                        <span>
                          <strong style={{ color: '#fff' }}>{c.author}</strong> ({c.authorRole})
                        </span>
                        <span>{new Date(c.createdAt).toLocaleTimeString()}</span>
                      </div>
                      <div style={{ color: '#e2e8f0', lineHeight: 1.4 }}>{c.text}</div>
                    </div>
                  ))
                )}
              </div>

              {/* Add Comment Input */}
              <form onSubmit={handleAddComment} style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <input
                  type="text"
                  className="input-control"
                  placeholder="Add resolution note, audit remark, or comment..."
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  style={{ fontSize: '13px' }}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ padding: '8px 14px' }}
                  disabled={!commentText.trim()}
                >
                  <Send size={15} />
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
