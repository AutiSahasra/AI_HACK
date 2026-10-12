import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ActionApprovalRecord } from '../types';
import { ShieldCheck, CheckCircle2, XCircle, Play, RefreshCw, AlertTriangle, Clock } from 'lucide-react';

export const Approvals: React.FC = () => {
  const [approvals, setApprovals] = useState<ActionApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<ActionApprovalRecord | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionOutput, setActionOutput] = useState<any>(null);

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
      fetchApprovals();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleExecute = async (approvalId: string) => {
    try {
      const res = await api.executeAction(approvalId);
      setActionOutput(res);
      fetchApprovals();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'pending': return <span className="badge badge-warn"><Clock size={12} /> Pending Approval</span>;
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
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Protected Remediation Approvals
          </h2>
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
        <div className="glass-panel" style={{ padding: '16px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid var(--border-accent)' }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
            Execution Status: {actionOutput.status}
          </div>
          <div style={{ fontSize: '13px' }}>{actionOutput.message}</div>
        </div>
      )}

      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={18} color="var(--accent-cyan)" />
          <span>Remediation Requests ({approvals.length})</span>
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {approvals.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-dim)' }}>
              No approval requests pending. Requests submitted from incident investigation will appear here.
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
                    padding: '16px 20px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontWeight: 700, fontSize: '15px', color: '#fff' }}>
                        {a.actionName}
                      </span>
                      {getStatusBadge(a.status)}
                      <span style={{ fontSize: '12px', color: 'var(--accent-cyan)' }}>
                        Incident: {a.incidentId ? a.incidentId.slice(0, 8) : 'N/A'}...
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      Requested by <strong>{a.requestedBy}</strong> ({a.requestedByRole}) at {new Date(a.createdAt).toLocaleTimeString()}
                      {a.approvedBy && (
                        <span style={{ marginLeft: '8px', color: '#34d399' }}>
                          • Decided by {a.approvedBy} ({a.approvedByRole})
                        </span>
                      )}
                      {a.rejectionReason && (
                        <span style={{ marginLeft: '8px', color: '#fb7185' }}>
                          • Reason: {a.rejectionReason}
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
                            const r = prompt('Enter rejection reason:');
                            if (r) {
                              setRejectReason(r);
                              handleDecision(approvalId, 'rejected');
                            }
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
                        onClick={() => handleExecute(approvalId)}
                      >
                        <Play size={15} /> Execute & Verify
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
