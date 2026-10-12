import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
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
  ArrowRight
} from 'lucide-react';

export const Approvals: React.FC = () => {
  const [approvals, setApprovals] = useState<ActionApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [rejectingApprovalId, setRejectingApprovalId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionOutput, setActionOutput] = useState<{ status: string; message: string; incidentId?: string } | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);

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
    const interval = setInterval(fetchApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDecision = async (approvalId: string, decision: 'approved' | 'rejected') => {
    try {
      await api.decideApproval(approvalId, decision, decision === 'rejected' ? rejectReason : undefined);
      setRejectReason('');
      setRejectingApprovalId(null);
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
      setActionOutput({
        status: res.status,
        message: res.message,
        incidentId: approval.incidentId
      });
      fetchApprovals();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExecutingId(null);
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'pending': return <span className="badge badge-warn"><Clock size={12} /> Pending SRE Review</span>;
      case 'approved': return <span className="badge badge-resolved"><CheckCircle2 size={12} /> Approved</span>;
      case 'rejected': return <span className="badge badge-critical"><XCircle size={12} /> Rejected</span>;
      case 'executed': return <span className="badge badge-info"><CheckCircle2 size={12} /> Executed</span>;
      default: return <span className="badge">{s}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>
              Protected Remediation Approvals
            </h2>
            <span className="badge badge-resolved" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}>
              <Lock size={11} /> Zero-Shell RBAC Enforced
            </span>
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

      {actionOutput && (
        <div className="glass-panel" style={{
          padding: '18px 22px',
          background: 'rgba(56, 189, 248, 0.1)',
          border: '1px solid var(--border-accent)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
              Execution Status: {actionOutput.status}
            </div>
            <div style={{ fontSize: '13px', color: '#fff' }}>{actionOutput.message}</div>
          </div>
          {actionOutput.incidentId && (
            <Link
              to={`/incidents/${actionOutput.incidentId}`}
              className="btn btn-primary"
              style={{ fontSize: '12px', padding: '6px 14px' }}
            >
              <span>View Incident Recovery Verification</span>
              <ArrowRight size={14} />
            </Link>
          )}
        </div>
      )}

      {/* Main Approvals Panel */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={18} color="var(--accent-cyan)" />
          <span>Remediation Requests ({approvals.length})</span>
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {approvals.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
              <ShieldCheck size={36} style={{ opacity: 0.4, marginBottom: '12px' }} />
              <div style={{ fontSize: '15px', fontWeight: 600, color: '#fff' }}>No Pending Approval Requests</div>
              <p style={{ fontSize: '13px', marginTop: '4px' }}>
                When a support engineer requests remediation on an incident, it will appear here for senior sign-off.
              </p>
            </div>
          ) : (
            approvals.map(a => {
              const approvalId = a.id || (a as any)._id || '';
              return (
                <div
                  key={approvalId}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '10px',
                    padding: '18px 20px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '14px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '75%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, fontSize: '15px', color: '#fff' }}>
                        {a.actionName}
                      </span>
                      {getStatusBadge(a.status)}
                      {a.incidentId && (
                        <Link
                          to={`/incidents/${a.incidentId}`}
                          style={{
                            fontSize: '12px',
                            color: 'var(--accent-cyan)',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            background: 'rgba(56, 189, 248, 0.08)',
                            padding: '2px 8px',
                            borderRadius: '4px'
                          }}
                        >
                          <span>Incident: {a.incidentId.slice(0, 8)}...</span>
                          <ExternalLink size={11} />
                        </Link>
                      )}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)', lineHeight: '1.4' }}>
                      Requested by <strong>{a.requestedBy}</strong> ({a.requestedByRole}) at {new Date(a.createdAt).toLocaleTimeString()}
                      {a.approvedBy && (
                        <span style={{ marginLeft: '8px', color: '#34d399' }}>
                          &bull; Decided by <strong>{a.approvedBy}</strong> ({a.approvedByRole})
                        </span>
                      )}
                      {a.rejectionReason && (
                        <span style={{ marginLeft: '8px', color: '#fb7185' }}>
                          &bull; Reason: <em>{a.rejectionReason}</em>
                        </span>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {a.status === 'pending' && (
                      <>
                        <button
                          className="btn btn-success"
                          style={{ padding: '6px 14px', fontSize: '13px' }}
                          onClick={() => handleDecision(approvalId, 'approved')}
                        >
                          <CheckCircle2 size={15} /> Approve
                        </button>
                        <button
                          className="btn btn-danger"
                          style={{ padding: '6px 14px', fontSize: '13px' }}
                          onClick={() => {
                            setRejectingApprovalId(approvalId);
                            setRejectReason('');
                          }}
                        >
                          <XCircle size={15} /> Reject
                        </button>
                      </>
                    )}

                    {a.status === 'approved' && (
                      <button
                        className="btn btn-primary"
                        style={{ padding: '6px 14px', fontSize: '13px' }}
                        disabled={executingId === approvalId}
                        onClick={() => handleExecute(a)}
                      >
                        <Play size={15} className={executingId === approvalId ? 'animate-spin' : ''} />
                        <span>{executingId === approvalId ? 'Executing...' : 'Execute & Verify'}</span>
                      </button>
                    )}

                    {a.status === 'executed' && a.incidentId && (
                      <Link
                        to={`/incidents/${a.incidentId}`}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        <span>Check Incident</span>
                        <ArrowRight size={13} />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Rejection Modal */}
      {rejectingApprovalId && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div className="glass-panel" style={{
            width: '90%',
            maxWidth: '480px',
            padding: '24px',
            backgroundColor: '#0c1017',
            border: '1px solid var(--border-accent)',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: '#fff' }}>
              Reject Remediation Request
            </h3>
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
              <button
                className="btn btn-secondary"
                onClick={() => setRejectingApprovalId(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                disabled={!rejectReason.trim()}
                onClick={() => handleDecision(rejectingApprovalId, 'rejected')}
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
