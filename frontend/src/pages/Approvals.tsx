import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, getStoredUser } from '../api/client';
import { ActionApprovalRecord } from '../types';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Play,
  RefreshCw,
  AlertTriangle,
  Clock,
  ExternalLink,
  Lock,
  ArrowRight,
  FileText,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronRight,
  Activity
} from 'lucide-react';

const RISK_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  low:      { bg: 'rgba(16,185,129,0.10)',  border: 'rgba(16,185,129,0.35)',  text: '#34d399' },
  medium:   { bg: 'rgba(245,158,11,0.10)',  border: 'rgba(245,158,11,0.35)',  text: '#fbbf24' },
  high:     { bg: 'rgba(244,63,94,0.10)',   border: 'rgba(244,63,94,0.35)',   text: '#fb7185' },
  critical: { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.50)',   text: '#f87171' },
};
function riskColor(level?: string | null) {
  return RISK_COLORS[(level || 'medium').toLowerCase()] ?? RISK_COLORS.medium;
}

export const Approvals: React.FC = () => {
  const currentUser = getStoredUser();
  const [approvals, setApprovals] = useState<ActionApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [rejectingApprovalId, setRejectingApprovalId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionOutput, setActionOutput] = useState<{ status: string; message: string; incidentId?: string } | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'approved' | 'executed' | 'rejected'>('all');

  const fetchApprovals = async () => {
    setLoading(true);
    try {
      const data = await api.getApprovals();
      setApprovals(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleDecision = async (approvalId: string, decision: 'approved' | 'rejected') => {
    try {
      const rec = await api.decideApproval(approvalId, decision, decision === 'rejected' ? rejectReason : undefined);
      setRejectReason('');
      setRejectingApprovalId(null);
      setActionOutput({
        status: decision === 'approved' ? 'Approved' : 'Rejected',
        message: decision === 'approved'
          ? `Remediation action '${rec.actionName}' approved. Ready for execution and automated health verification.`
          : `Remediation action '${rec.actionName}' rejected with rationale. Linked incident and ticket returned to active triage.`,
        incidentId: rec.incidentId
      });
      fetchApprovals();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleExecute = async (approval: ActionApprovalRecord) => {
    const approvalId = approval.id || (approval as any)._id || '';
    setExecutingId(approvalId);
    try {
      const res = await api.executeAction(approvalId);
      setActionOutput({ status: res.status, message: res.message, incidentId: approval.incidentId });
      fetchApprovals();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExecutingId(null);
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'pending':   return <span className="badge badge-warn"><Clock size={12} /> Pending SRE Review</span>;
      case 'approved':  return <span className="badge badge-resolved"><CheckCircle2 size={12} /> Approved</span>;
      case 'rejected':  return <span className="badge badge-critical"><XCircle size={12} /> Rejected</span>;
      case 'executing': return <span className="badge badge-info"><RefreshCw size={12} className="animate-spin" /> Executing Fix</span>;
      case 'executed':  return <span className="badge badge-info"><CheckCircle2 size={12} /> Executed</span>;
      case 'failed':    return <span className="badge badge-critical"><AlertCircle size={12} /> Failed</span>;
      default:          return <span className="badge">{s}</span>;
    }
  };

  const getVerificationBadge = (a: ActionApprovalRecord) => {
    if (a.verificationStatus === 'verified') {
      return (
        <span className="badge badge-resolved" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(16,185,129,0.18)', border: '1px solid #10b981', color: '#34d399' }}>
          <CheckCircle2 size={12} /> Recovery Verified (Resolved)
        </span>
      );
    }
    if (a.verificationStatus === 'failed') {
      return (
        <span className="badge badge-critical" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(239,68,68,0.18)', border: '1px solid #ef4444', color: '#f87171' }}>
          <AlertTriangle size={12} /> Health Check Failed (Escalated)
        </span>
      );
    }
    if (a.status === 'executed' && !a.verificationStatus) {
      return (
        <span className="badge badge-info" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(56,189,248,0.15)', border: '1px solid #38bdf8', color: '#38bdf8' }}>
          <RefreshCw size={12} className="animate-spin" /> Verifying Health Checks...
        </span>
      );
    }
    return null;
  };

  const pendingCount = approvals.filter(a => a.status === 'pending').length;
  const approvedCount = approvals.filter(a => a.status === 'approved').length;
  const executedCount = approvals.filter(a => a.status === 'executed').length;
  const rejectedCount = approvals.filter(a => a.status === 'rejected').length;

  const filteredApprovals = approvals.filter(a => {
    if (activeTab === 'all') return true;
    return a.status === activeTab;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>Protected Remediation Approvals</h2>
            <span className="badge badge-resolved" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
              <Lock size={11} /> Zero-Shell RBAC Enforced
            </span>
            {pendingCount > 0 && (
              <span className="badge badge-warn" style={{ fontSize: '12px' }}>{pendingCount} Pending</span>
            )}
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Senior SRE approval queue. Enforces backend-validated authorization and blocks unauthorized production modifications.
          </p>
        </div>
        <button onClick={fetchApprovals} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Execution Result Banner */}
      {actionOutput && (
        <div className="glass-panel" style={{ padding: '18px 22px', background: 'rgba(56,189,248,0.1)', border: '1px solid var(--border-accent)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
              Execution Status: {actionOutput.status}
            </div>
            <div style={{ fontSize: '13px', color: '#fff' }}>{actionOutput.message}</div>
          </div>
          {actionOutput.incidentId && (
            <Link to={`/incidents/${actionOutput.incidentId}`} className="btn btn-primary" style={{ fontSize: '12px', padding: '6px 14px' }}>
              <span>View Incident Recovery Verification</span>
              <ArrowRight size={14} />
            </Link>
          )}
        </div>
      )}

      {/* Main Panel */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <h3 style={{ fontSize: '16px', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="var(--accent-cyan)" />
            <span>Remediation Requests ({approvals.length})</span>
          </h3>

          {/* Filter Tabs */}
          <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-tertiary)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <button
              className="btn"
              onClick={() => setActiveTab('all')}
              style={{
                fontSize: '12px',
                padding: '4px 10px',
                background: activeTab === 'all' ? 'var(--bg-secondary)' : 'transparent',
                color: activeTab === 'all' ? '#fff' : 'var(--text-dim)',
                border: activeTab === 'all' ? '1px solid var(--border-subtle)' : 'none'
              }}
            >
              All ({approvals.length})
            </button>
            <button
              className="btn"
              onClick={() => setActiveTab('pending')}
              style={{
                fontSize: '12px',
                padding: '4px 10px',
                background: activeTab === 'pending' ? 'rgba(245,158,11,0.2)' : 'transparent',
                color: activeTab === 'pending' ? '#fbbf24' : 'var(--text-dim)',
                border: activeTab === 'pending' ? '1px solid rgba(245,158,11,0.4)' : 'none'
              }}
            >
              Pending ({pendingCount})
            </button>
            <button
              className="btn"
              onClick={() => setActiveTab('approved')}
              style={{
                fontSize: '12px',
                padding: '4px 10px',
                background: activeTab === 'approved' ? 'rgba(52,211,153,0.2)' : 'transparent',
                color: activeTab === 'approved' ? '#34d399' : 'var(--text-dim)',
                border: activeTab === 'approved' ? '1px solid rgba(52,211,153,0.4)' : 'none'
              }}
            >
              Approved ({approvedCount})
            </button>
            <button
              className="btn"
              onClick={() => setActiveTab('executed')}
              style={{
                fontSize: '12px',
                padding: '4px 10px',
                background: activeTab === 'executed' ? 'rgba(56,189,248,0.2)' : 'transparent',
                color: activeTab === 'executed' ? '#38bdf8' : 'var(--text-dim)',
                border: activeTab === 'executed' ? '1px solid rgba(56,189,248,0.4)' : 'none'
              }}
            >
              Executed ({executedCount})
            </button>
            <button
              className="btn"
              onClick={() => setActiveTab('rejected')}
              style={{
                fontSize: '12px',
                padding: '4px 10px',
                background: activeTab === 'rejected' ? 'rgba(244,63,94,0.2)' : 'transparent',
                color: activeTab === 'rejected' ? '#fb7185' : 'var(--text-dim)',
                border: activeTab === 'rejected' ? '1px solid rgba(244,63,94,0.4)' : 'none'
              }}
            >
              Rejected ({rejectedCount})
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredApprovals.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
              <ShieldCheck size={36} style={{ opacity: 0.4, marginBottom: '12px' }} />
              <div style={{ fontSize: '15px', fontWeight: 600, color: '#fff' }}>No Requests Matching Filter</div>
              <p style={{ fontSize: '13px', marginTop: '4px' }}>
                There are no remediation requests currently under the '{activeTab}' status tab.
              </p>
            </div>
          ) : (
            filteredApprovals.map(a => {
              const approvalId = a.id || (a as any)._id || '';
              const isExpanded = expandedId === approvalId;
              const rc = riskColor(a.riskLevel);
              const isSelfRequest = currentUser && a.requestedBy === currentUser.username;

              return (
                <div
                  key={approvalId}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${a.status === 'pending' ? 'rgba(245,158,11,0.25)' : 'var(--border-subtle)'}`,
                    borderRadius: '10px',
                    overflow: 'hidden',
                    transition: 'border-color 0.2s'
                  }}
                >
                  {/* Card Header (always visible) */}
                  <div
                    style={{ padding: '16px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', cursor: 'pointer' }}
                    onClick={() => setExpandedId(isExpanded ? null : approvalId)}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        {isExpanded ? <ChevronDown size={16} color="var(--text-dim)" /> : <ChevronRight size={16} color="var(--text-dim)" />}
                        <span style={{ fontWeight: 700, fontSize: '15px', color: '#fff' }}>{a.actionName}</span>
                        {getStatusBadge(a.status)}
                        {getVerificationBadge(a)}
                        {a.riskLevel && (
                          <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '9999px', background: rc.bg, border: `1px solid ${rc.border}`, color: rc.text, textTransform: 'uppercase' }}>
                            {a.riskLevel} risk
                          </span>
                        )}
                        {a.incidentId && (
                          <Link
                            to={`/incidents/${a.incidentId}`}
                            onClick={e => e.stopPropagation()}
                            style={{ fontSize: '12px', color: 'var(--accent-cyan)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(56,189,248,0.08)', padding: '2px 8px', borderRadius: '4px' }}
                          >
                            <span>Incident: {a.incidentId.slice(0, 8)}...</span>
                            <ExternalLink size={11} />
                          </Link>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-dim)', lineHeight: '1.4' }}>
                        Requested by <strong style={{ color: '#fff' }}>{a.requestedBy}</strong> ({a.requestedByRole}) at {new Date(a.createdAt).toLocaleTimeString()}
                        {a.approvedBy && (
                          <span style={{ marginLeft: '8px', color: '#34d399' }}>
                            &bull; Decided by <strong>{a.approvedBy}</strong> ({a.approvedByRole})
                          </span>
                        )}
                        {a.rejectionReason && (
                          <span style={{ marginLeft: '8px', color: '#fb7185' }}>
                            &bull; Rejection reason: <em>{a.rejectionReason}</em>
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }} onClick={e => e.stopPropagation()}>
                      {a.status === 'pending' && (
                        <>
                          {isSelfRequest ? (
                            <span
                              className="badge badge-warn"
                              style={{ padding: '6px 12px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', color: '#fbbf24' }}
                              title="Dual authorization policy blocks self-approval. An independent senior approver must review this request."
                            >
                              <Lock size={13} /> Your Request (Awaiting Peer Review)
                            </span>
                          ) : (
                            <>
                              <button className="btn btn-success" style={{ padding: '6px 14px', fontSize: '13px' }} onClick={() => handleDecision(approvalId, 'approved')}>
                                <CheckCircle2 size={15} /> Approve
                              </button>
                              <button className="btn btn-danger" style={{ padding: '6px 14px', fontSize: '13px' }} onClick={() => { setRejectingApprovalId(approvalId); setRejectReason(''); }}>
                                <XCircle size={15} /> Reject
                              </button>
                            </>
                          )}
                        </>
                      )}

                      {a.status === 'approved' && (
                        <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '13px' }} disabled={executingId === approvalId} onClick={() => handleExecute(a)}>
                          <Play size={15} className={executingId === approvalId ? 'animate-spin' : ''} />
                          <span>{executingId === approvalId ? 'Executing...' : 'Execute and Verify'}</span>
                        </button>
                      )}

                      {a.status === 'executed' && a.incidentId && (
                        <Link to={`/incidents/${a.incidentId}`} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                          <span>Check Incident</span>
                          <ArrowRight size={13} />
                        </Link>
                      )}
                    </div>
                  </div>

                  {/* Expanded evidence panel */}
                  {isExpanded && (
                    <div style={{ padding: '0 18px 18px', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginTop: '16px' }}>

                        {/* Justification */}
                        {a.justification && (
                          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                              <Info size={11} /> Justification
                            </div>
                            <div style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: '1.5' }}>{a.justification}</div>
                          </div>
                        )}

                        {/* Expected Outcome */}
                        {a.expectedOutcome && (
                          <div style={{ background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                              <Activity size={11} /> Expected Outcome
                            </div>
                            <div style={{ fontSize: '13px', color: '#34d399', lineHeight: '1.5' }}>{a.expectedOutcome}</div>
                          </div>
                        )}
                      </div>

                      {/* Supporting Evidence */}
                      {a.supportingEvidence && a.supportingEvidence.length > 0 && (
                        <div style={{ marginTop: '14px', background: 'var(--bg-tertiary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                            <FileText size={11} /> Supporting Evidence from Logs
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {a.supportingEvidence.map((ev, i) => (
                              <div key={i} className="code-block" style={{ fontSize: '11px' }}>{ev}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Runbook reference */}
                      {a.runbookReference && (
                        <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                          <FileText size={13} />
                          <strong>Runbook / Historical Reference:</strong> {a.runbookReference}
                        </div>
                      )}

                      {/* Risk + meta */}
                      <div style={{ marginTop: '14px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '12px', color: 'var(--text-dim)' }}>
                        {a.riskLevel && (
                          <div>Risk: <span style={{ color: rc.text, fontWeight: 700 }}>{a.riskLevel.toUpperCase()}</span></div>
                        )}
                        <div>Created: {new Date(a.createdAt).toLocaleString()}</div>
                        <div>Approval ID: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{approvalId.slice(0, 16)}...</span></div>
                      </div>

                      {/* Approver action warning for self-request */}
                      {isSelfRequest && a.status === 'pending' && (
                        <div style={{ marginTop: '14px', padding: '10px 14px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: '8px', fontSize: '12px', color: '#fbbf24', display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <Lock size={13} />
                          Self-approval is blocked by dual-authorization policy. A different Senior Approver must review this request.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Rejection Modal */}
      {rejectingApprovalId && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ width: '90%', maxWidth: '480px', padding: '24px', backgroundColor: '#0c1017', border: '1px solid var(--border-accent)', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: '#fff' }}>Reject Remediation Request</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Please provide a clear reason for rejecting this remediation action. This will be recorded in the immutable audit log and reflected on the incident.
            </p>
            <textarea
              className="input-control"
              rows={3}
              placeholder="e.g., Target service is scheduled for standard release window, manual failover preferred..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              style={{ width: '100%', marginBottom: '16px', fontSize: '13px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn btn-secondary" onClick={() => setRejectingApprovalId(null)}>Cancel</button>
              <button className="btn btn-danger" disabled={!rejectReason.trim()} onClick={() => handleDecision(rejectingApprovalId, 'rejected')}>
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
