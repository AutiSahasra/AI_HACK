import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, getStoredUser } from '../api/client';
import { Incident, LogEvent, ActionApprovalRecord, RemediationRecommendation } from '../types';
import { hasPermission } from '../auth/permissions';
import {
  ArrowLeft,
  AlertTriangle,
  Clock,
  Layers,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  Wrench,
  ShieldCheck,
  XCircle,
  Zap,
  RefreshCw,
  Info,
  AlertCircle,
  CheckCheck,
  FileText,
  Target
} from 'lucide-react';

const RISK_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  low:      { bg: 'rgba(16,185,129,0.10)',  border: 'rgba(16,185,129,0.35)',  text: '#34d399' },
  medium:   { bg: 'rgba(245,158,11,0.10)',  border: 'rgba(245,158,11,0.35)',  text: '#fbbf24' },
  high:     { bg: 'rgba(244,63,94,0.10)',   border: 'rgba(244,63,94,0.35)',   text: '#fb7185' },
  critical: { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.50)',   text: '#f87171' },
};

function riskColor(level: string) {
  return RISK_COLORS[level?.toLowerCase()] ?? RISK_COLORS.medium;
}

function confidencePct(c: number) {
  return `${Math.round(c * 100)}%`;
}

export const IncidentDetail: React.FC = () => {
  const currentUser = getStoredUser();
  const userRole = currentUser?.role;

  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [requests, setRequests] = useState<ActionApprovalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<boolean | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [recommendations, setRecommendations] = useState<RemediationRecommendation[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [recsError, setRecsError] = useState<string | null>(null);

  // Approval-request modal (admin / support_engineer)
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestStep, setRequestStep] = useState<'recommendations' | 'form'>('recommendations');
  const [selectedRec, setSelectedRec] = useState<RemediationRecommendation | null>(null);
  const [reqAction, setReqAction] = useState('restart_demo_service');
  const [reqJustification, setReqJustification] = useState('');
  const [reqExpectedOutcome, setReqExpectedOutcome] = useState('');
  const [reqRiskLevel, setReqRiskLevel] = useState('medium');
  const [reqRunbook, setReqRunbook] = useState('');
  const [reqEvidence, setReqEvidence] = useState<string[]>([]);
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [actionErrorMsg, setActionErrorMsg] = useState<string | null>(null);

  // Direct-execute modal (approver)
  const [showDirectModal, setShowDirectModal] = useState(false);
  const [directRec, setDirectRec] = useState<RemediationRecommendation | null>(null);
  const [directAction, setDirectAction] = useState('restart_demo_service');
  const [directJustification, setDirectJustification] = useState('');
  const [directSubmitting, setDirectSubmitting] = useState(false);
  const [directResult, setDirectResult] = useState<{ status: string; message: string; executionId?: string } | null>(null);

  const incidentId = incident ? (incident.id || (incident as any)._id || id || '') : '';

  const fetchIncidentData = useCallback(async () => {
    if (!id) return;
    try {
      const inc = await api.getIncident(id);
      setIncident(inc);
      const evs = await api.getLogs({ fingerprint: inc.fingerprint || undefined, service: inc.service });
      setEvents(evs.items);
      try {
        const reqs = await api.getIncidentRequests(id);
        setRequests(reqs);
      } catch { /* non-fatal */ }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchRecommendations = useCallback(async () => {
    if (!id) return;
    setRecsLoading(true);
    setRecsError(null);
    try {
      const recs = await api.getRecommendations(id);
      setRecommendations(recs);
    } catch (e: any) {
      setRecsError(e.message || 'Could not load recommendations');
    } finally {
      setRecsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchIncidentData();
    const interval = setInterval(fetchIncidentData, 6000);
    return () => clearInterval(interval);
  }, [fetchIncidentData]);

  const handleTriggerRca = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      await api.triggerRca(id);
      await fetchIncidentData();
    } catch (e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  const handleFeedback = async (useful: boolean) => {
    if (!id) return;
    try { await api.submitFeedback(id, useful); setFeedbackSent(useful); }
    catch (e) { console.error(e); }
  };

  const openRequestModal = async () => {
    setActionErrorMsg(null);
    setActionSuccessMsg(null);
    setRequestStep('recommendations');
    setSelectedRec(null);
    setReqAction('restart_demo_service');
    setReqJustification('');
    setReqExpectedOutcome('');
    setReqRiskLevel('medium');
    setReqRunbook('');
    setReqEvidence([]);
    setShowRequestModal(true);
    await fetchRecommendations();
  };

  const selectRecommendation = (rec: RemediationRecommendation) => {
    setSelectedRec(rec);
    setReqAction(rec.actionName);
    setReqJustification(rec.relevanceReason);
    setReqExpectedOutcome(rec.expectedOutcome);
    setReqRiskLevel(rec.riskLevel);
    setReqRunbook(rec.runbookReference || '');
    setReqEvidence(rec.supportingEvidence || []);
    setRequestStep('form');
  };

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentId) { setActionErrorMsg('Error: Incident ID missing.'); return; }
    if (!reqJustification.trim()) { setActionErrorMsg('Justification is required before submitting.'); return; }
    setActionSubmitting(true);
    setActionErrorMsg(null);
    try {
      const res = await api.requestAction({
        incidentId,
        actionName: reqAction,
        justification: reqJustification,
        expectedOutcome: reqExpectedOutcome || undefined,
        riskLevel: reqRiskLevel || undefined,
        supportingEvidence: reqEvidence.length ? reqEvidence : undefined,
        runbookReference: reqRunbook || undefined,
      });
      setActionSuccessMsg(
        `Remediation request '${reqAction}' submitted (ID: ${res.id?.slice(0, 8)}). ` +
        `Status: ${res.status}. Routed to Senior Approver queue.`
      );
      setShowRequestModal(false);
      await fetchIncidentData();
    } catch (err: any) {
      setActionErrorMsg(err.message || 'Failed to submit remediation request');
    } finally {
      setActionSubmitting(false);
    }
  };

  const openDirectModal = async (rec?: RemediationRecommendation) => {
    setDirectResult(null);
    setDirectJustification('');
    if (rec) { setDirectRec(rec); setDirectAction(rec.actionName); }
    else { setDirectRec(null); setDirectAction('restart_demo_service'); }
    setShowDirectModal(true);
    if (recommendations.length === 0) await fetchRecommendations();
  };

  const handleDirectExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentId) return;
    setDirectSubmitting(true);
    try {
      const res = await api.directExecuteAction({
        incidentId,
        actionName: directAction,
        justification: directJustification || 'Direct Approver Resolution',
        parameters: directRec?.parameters || {},
      });
      setDirectResult(res);
      await fetchIncidentData();
    } catch (err: any) {
      setDirectResult({ status: 'error', message: err.message || 'Execution failed' });
    } finally {
      setDirectSubmitting(false);
    }
  };

  if (loading || !incident) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-dim)' }}>
        <RefreshCw size={24} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
        Loading incident investigation details...
      </div>
    );
  }

  const lifecycleStages = ['new', 'analyzing', 'analyzed', 'awaiting_approval', 'remediating', 'verifying', 'resolved'];
  const isApprover = userRole === 'approver';
  const canDirectExecute = hasPermission(userRole, 'EXECUTE_REMEDIATION');
  const canSendRequest = hasPermission(userRole, 'SEND_APPROVAL_REQUEST');
  const topCause = incident.probableCauses?.[0];

  const directIsRisky = directRec?.riskLevel === 'high' || directRec?.riskLevel === 'critical' || directAction === 'rollback_demo_config';
  const execResultFailed = directResult?.status === 'error' || directResult?.status === 'failed';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Header */}
      <div>
        <Link to="/incidents" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', textDecoration: 'none', fontSize: '13px', marginBottom: '12px' }}>
          <ArrowLeft size={16} /> Back to Incidents Feed
        </Link>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span className={`badge badge-${incident.severity.toLowerCase()}`}>{incident.severity}</span>
              <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>Status: {incident.status}</span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)' }}>{incident.service}</span>
              {incident.isRepeated && <span className="badge badge-critical">Repeated Outage</span>}
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>{incident.title}</h1>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {canDirectExecute && isApprover && (
              <button
                id="btn-direct-execute"
                onClick={() => openDirectModal()}
                className="btn btn-primary"
                style={{ background: 'linear-gradient(135deg,#10b981 0%,#059669 100%)', boxShadow: '0 2px 10px rgba(16,185,129,0.35)' }}
              >
                <Zap size={16} />
                <span>Resolve Issue Directly</span>
              </button>
            )}
            {canSendRequest && (
              <button id="btn-send-approval" onClick={openRequestModal} className="btn btn-secondary">
                <Wrench size={16} />
                <span>Send Approval Request</span>
              </button>
            )}
            <button id="btn-run-rca" onClick={handleTriggerRca} className="btn btn-primary" disabled={analyzing}>
              <Sparkles size={16} />
              <span>{analyzing ? 'Analyzing...' : 'Run Copilot RCA'}</span>
            </button>
          </div>
        </div>

        {actionSuccessMsg && (
          <div className="glass-panel" style={{ marginTop: '14px', padding: '12px 18px', background: 'rgba(52,211,153,0.15)', border: '1px solid var(--accent-emerald)', color: '#34d399', fontSize: '13px' }}>
            {actionSuccessMsg}
          </div>
        )}
        {actionErrorMsg && (
          <div className="glass-panel" style={{ marginTop: '14px', padding: '12px 18px', background: 'rgba(244,63,94,0.15)', border: '1px solid var(--accent-rose)', color: '#fb7185', fontSize: '13px' }}>
            {actionErrorMsg}
          </div>
        )}

        {incident.ticketId && (
          <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-dim)' }}>
            Linked Ticket: <Link to="/tickets" style={{ color: 'var(--accent-cyan)', fontWeight: 600, textDecoration: 'none' }}>{incident.ticketId}</Link>
          </div>
        )}

        {incident.status === 'awaiting_approval' && (
          <div style={{ marginTop: '14px', padding: '14px 18px', background: 'rgba(245,158,11,0.12)', border: '1px solid #f59e0b', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldCheck size={20} color="#f59e0b" />
              <div>
                <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '14px' }}>Remediation Request Pending SRE Approval</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>A remediation action has been requested and is awaiting review by a Senior Approver.</div>
              </div>
            </div>
            {hasPermission(userRole, 'VIEW_APPROVALS_QUEUE') ? (
              <Link to="/approvals" className="btn btn-secondary" style={{ borderColor: '#f59e0b', color: '#f59e0b', fontSize: '12px' }}>Review in Approvals Queue</Link>
            ) : (
              <span className="badge badge-warn" style={{ fontSize: '12px', padding: '6px 12px' }}>Awaiting Senior Approver Decision</span>
            )}
          </div>
        )}

        {incident.status === 'verifying' && (
          <div style={{ marginTop: '14px', padding: '14px 18px', background: 'rgba(56,189,248,0.12)', border: '1px solid var(--border-accent)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <RefreshCw size={20} color="var(--accent-cyan)" className="animate-spin" />
            <div>
              <div style={{ fontWeight: 700, color: 'var(--accent-cyan)', fontSize: '14px' }}>Automated Recovery Verification In Progress</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Remediation was executed. System is polling target health check endpoints to verify complete service restoration.</div>
            </div>
          </div>
        )}

        {incident.status === 'resolved' && (
          <div style={{ marginTop: '14px', padding: '14px 18px', background: 'rgba(16,185,129,0.12)', border: '1px solid var(--accent-emerald)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <CheckCircle2 size={20} color="var(--accent-emerald)" />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--accent-emerald)', fontSize: '14px' }}>Incident Resolved and Verified</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Remediation was executed and post-action health checks confirmed healthy recovery.</div>
              </div>
            </div>
            {incident.ticketId && <Link to="/tickets" className="btn btn-secondary" style={{ fontSize: '12px' }}>Check Ticket Status</Link>}
          </div>
        )}

        {incident.status === 'escalated' && (
          <div style={{ marginTop: '14px', padding: '14px 18px', background: 'rgba(244,63,94,0.10)', border: '1px solid var(--accent-rose)', borderRadius: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={20} color="var(--accent-rose)" />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--accent-rose)', fontSize: '14px' }}>Incident Escalated - Manual Review Required</div>
                {incident.escalationReason && <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>{incident.escalationReason}</div>}
              </div>
            </div>
          </div>
        )}

        {requests.length > 0 && (
          <div className="glass-panel" style={{ marginTop: '16px', padding: '16px 20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Remediation Request History and Status ({requests.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {requests.map(req => {
                const reqId = req.id || (req as any)._id || '';
                return (
                  <div key={reqId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'var(--bg-secondary)', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '13px', gap: '12px' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontWeight: 600, color: '#fff' }}>{req.actionName}</span>
                      <span style={{ color: 'var(--text-dim)', marginLeft: '10px', fontSize: '12px' }}>
                        Requested by <strong>{req.requestedBy}</strong> ({req.requestedByRole}) at {new Date(req.createdAt).toLocaleTimeString()}
                      </span>
                      {req.justification && <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '3px' }}>Justification: {req.justification}</div>}
                      {req.expectedOutcome && <div style={{ color: 'var(--text-dim)', fontSize: '12px', marginTop: '2px' }}>Expected: {req.expectedOutcome}</div>}
                      {req.riskLevel && <div style={{ fontSize: '12px', marginTop: '2px' }}><span style={{ color: riskColor(req.riskLevel).text }}>Risk: {req.riskLevel}</span></div>}
                      {req.rejectionReason && <div style={{ color: '#fb7185', fontSize: '12px', marginTop: '4px' }}>Rejection Reason: {req.rejectionReason}</div>}
                      {req.approvedBy && req.status === 'approved' && <div style={{ color: '#34d399', fontSize: '12px', marginTop: '4px' }}>Approved by: {req.approvedBy}</div>}
                    </div>
                    <div style={{ flexShrink: 0 }}>
                      {req.status === 'pending'  && <span className="badge badge-warn"><Clock size={11} /> Pending</span>}
                      {req.status === 'approved' && <span className="badge badge-resolved"><CheckCircle2 size={11} /> Approved</span>}
                      {req.status === 'rejected' && <span className="badge badge-critical"><XCircle size={11} /> Rejected</span>}
                      {req.status === 'executed' && <span className="badge badge-info"><CheckCircle2 size={11} /> Executed</span>}
                      {req.status === 'failed'   && <span className="badge badge-critical"><AlertCircle size={11} /> Failed</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Lifecycle Progress */}
      <div className="glass-panel" style={{ padding: '16px 24px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '12px', textTransform: 'uppercase' }}>Resolution Lifecycle</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
          {lifecycleStages.map((stage, idx) => {
            const isCurrent = incident.status === stage;
            const isPassed = lifecycleStages.indexOf(incident.status) > idx;
            return (
              <div key={stage} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 2 }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700, background: isCurrent ? 'var(--accent-cyan)' : isPassed ? 'var(--accent-emerald)' : 'var(--bg-secondary)', color: isCurrent || isPassed ? '#fff' : 'var(--text-dim)', border: isCurrent ? '2px solid #fff' : '1px solid var(--border-subtle)', boxShadow: isCurrent ? 'var(--glow-cyan)' : undefined }}>
                  {isPassed ? 'v' : idx + 1}
                </div>
                <span style={{ fontSize: '11px', marginTop: '6px', color: isCurrent ? '#fff' : 'var(--text-dim)', textTransform: 'capitalize' }}>{stage.replace('_', ' ')}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* RCA Findings */}
      {incident.probableCauses && incident.probableCauses.length > 0 && (
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid var(--border-accent)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={20} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '18px', margin: 0 }}>AI Root-Cause Hypotheses and Diagnostic Plan</h3>
              <span className="badge badge-info" style={{ fontSize: '11px' }}>Hypothesis - Unverified</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Was this diagnosis helpful?</span>
              <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px', background: feedbackSent === true ? 'rgba(16,185,129,0.2)' : undefined }} onClick={() => handleFeedback(true)}>
                <ThumbsUp size={14} /> Yes
              </button>
              <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px', background: feedbackSent === false ? 'rgba(244,63,94,0.2)' : undefined }} onClick={() => handleFeedback(false)}>
                <ThumbsDown size={14} /> No
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
            {incident.probableCauses.map((cause, idx) => (
              <div key={idx} style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>Rank #{cause.rank}</span>
                  <span className={`badge badge-${cause.confidenceTier === 'high' ? 'resolved' : cause.confidenceTier === 'medium' ? 'warn' : 'critical'}`}>
                    Confidence: {(cause.confidence * 100).toFixed(0)}% ({cause.confidenceTier})
                  </span>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>{cause.description}</div>
                {cause.supportingEvidence && cause.supportingEvidence.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>Cited Log Evidence Excerpt:</div>
                    {cause.supportingEvidence.map((ev, i) => (
                      <div key={i} className="code-block" style={{ marginTop: '4px', fontSize: '12px' }}>{ev.excerpt}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ background: 'rgba(16,21,36,0.8)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={16} /> Observed Facts (Directly Verified in Logs)
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--text-main)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {incident.observedFacts?.map((fact, i) => <li key={i}>{fact}</li>)}
              </ul>
            </div>
            <div style={{ background: 'rgba(16,21,36,0.8)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-purple)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={16} /> AI Inferences (Model Hypotheses)
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--text-main)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {incident.aiInferences?.map((inf, i) => <li key={i}>{inf}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Event Timeline */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--accent-cyan)" />
          <span>Related Log Events Timeline ({events.length} captured)</span>
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {events.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)' }}>No correlated events found for this incident.</div>
          ) : (
            events.map(ev => {
              const evId = ev.id || ev._id || '';
              const isExpanded = expandedEventId === evId;
              return (
                <div key={evId} style={{ background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-subtle)', padding: '12px 16px', cursor: 'pointer' }} onClick={() => setExpandedEventId(isExpanded ? null : evId)}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                    <span className={`badge badge-${ev.severity.toLowerCase()}`}>{ev.severity}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-dim)' }}>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: '#fff' }}>{ev.message.split('\n')[0]}</span>
                  </div>
                  {isExpanded && (
                    <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                      <div className="code-block" style={{ whiteSpace: 'pre-wrap' }}>{ev.message}</div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ================================================================
          MODAL: Approver Direct-Execute
          ================================================================ */}
      {showDirectModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.82)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div className="glass-panel" style={{ maxWidth: '640px', width: '100%', padding: '28px', border: '1px solid rgba(16,185,129,0.45)', boxShadow: '0 24px 48px rgba(0,0,0,0.6)', maxHeight: '90vh', overflowY: 'auto' }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <Zap size={22} color="#10b981" />
              <h3 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#10b981' }}>Resolve Issue Directly</h3>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              As a Senior Approver, you may execute eligible (non-Critical) remediation actions without a second approval cycle. The backend enforces all policy constraints -- this UI does not bypass authorization.
            </p>

            {topCause && (
              <div style={{ background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.25)', borderRadius: '10px', padding: '14px 16px', marginBottom: '18px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={13} /> AI Root-Cause Hypothesis
                </div>
                <div style={{ fontSize: '14px', color: '#fff', fontWeight: 600, marginBottom: '4px' }}>{topCause.description}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Confidence: <strong style={{ color: '#fbbf24' }}>{confidencePct(topCause.confidence)}</strong> ({topCause.confidenceTier}) -- Service: <strong style={{ color: 'var(--accent-cyan)' }}>{incident.service}</strong>
                </div>
                {topCause.supportingEvidence?.[0] && (
                  <div className="code-block" style={{ marginTop: '8px', fontSize: '11px' }}>{topCause.supportingEvidence[0].excerpt}</div>
                )}
              </div>
            )}

            {recommendations.length > 0 && !directResult && (
              <div style={{ marginBottom: '18px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-dim)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Recommended Remediations (click to select)</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {recommendations.map((rec, i) => {
                    const rc = riskColor(rec.riskLevel);
                    const isSelected = directAction === rec.actionName;
                    return (
                      <div
                        key={i}
                        onClick={() => { setDirectAction(rec.actionName); setDirectRec(rec); }}
                        style={{ padding: '12px 14px', borderRadius: '8px', border: `1px solid ${isSelected ? 'var(--accent-emerald)' : 'var(--border-subtle)'}`, background: isSelected ? 'rgba(16,185,129,0.08)' : 'var(--bg-secondary)', cursor: 'pointer', transition: 'all 0.18s' }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600, color: '#fff', fontSize: '14px' }}>{rec.actionTitle}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{rec.relevanceReason}</div>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0, marginLeft: '12px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '9999px', background: rc.bg, border: `1px solid ${rc.border}`, color: rc.text, textTransform: 'uppercase' }}>{rec.riskLevel}</span>
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{confidencePct(rec.confidence)} confidence</span>
                          </div>
                        </div>
                        {rec.supportingEvidence?.[0] && (
                          <div className="code-block" style={{ marginTop: '8px', fontSize: '11px' }}>{rec.supportingEvidence[0]}</div>
                        )}
                        <div style={{ fontSize: '12px', color: '#34d399', marginTop: '6px' }}>Expected: {rec.expectedOutcome}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {directResult && (
              <div style={{ padding: '16px', borderRadius: '10px', marginBottom: '18px', background: execResultFailed ? 'rgba(244,63,94,0.12)' : 'rgba(16,185,129,0.12)', border: `1px solid ${execResultFailed ? 'var(--accent-rose)' : 'var(--accent-emerald)'}` }}>
                <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '6px', color: execResultFailed ? '#fb7185' : '#34d399', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {execResultFailed ? <XCircle size={16} /> : <CheckCheck size={16} />}
                  {directResult.status === 'executing_recovery_verification' ? 'Action Executed -- Verifying Recovery' : `Execution: ${directResult.status}`}
                </div>
                <div style={{ fontSize: '13px', color: '#fff' }}>{directResult.message}</div>
                {directResult.executionId && (
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px', fontFamily: 'var(--font-mono)' }}>Execution ID: {directResult.executionId}</div>
                )}
                {directResult.status === 'executing_recovery_verification' && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                    Post-remediation health checks are running asynchronously. Refresh in a few seconds to confirm resolution.
                  </div>
                )}
              </div>
            )}

            {!directResult && (
              <form onSubmit={handleDirectExecute} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Remediation Action</label>
                  <select className="input-control" value={directAction} onChange={e => { setDirectAction(e.target.value); setDirectRec(null); }} style={{ width: '100%', fontSize: '13px' }}>
                    <option value="restart_demo_service">restart_demo_service -- Recycle container and connection pool</option>
                    <option value="clear_demo_cache">clear_demo_cache -- Flush in-memory cache and heap buffers</option>
                    <option value="rollback_demo_config">rollback_demo_config -- Rollback to last verified config (High risk)</option>
                  </select>
                </div>

                {directIsRisky && (
                  <div style={{ padding: '10px 14px', background: 'rgba(244,63,94,0.10)', border: '1px solid rgba(244,63,94,0.30)', borderRadius: '8px', fontSize: '12px', color: '#fb7185', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
                    <div><strong>High-risk action:</strong> This action modifies system configuration. Proceed only if root cause has been confirmed. Critical-risk actions are blocked by backend policy regardless of role.</div>
                  </div>
                )}

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Justification (optional)</label>
                  <textarea className="input-control" rows={2} placeholder="Brief rationale for direct execution..." value={directJustification} onChange={e => setDirectJustification(e.target.value)} style={{ width: '100%', fontSize: '13px', resize: 'vertical' }} />
                </div>

                <div style={{ background: 'rgba(56,189,248,0.08)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)', fontSize: '12px', color: 'var(--text-muted)' }}>
                  Authorization is enforced on the backend against the remediation allow-list, role permissions, and action risk classification. Critical-risk and dual-approval actions will be rejected even from approver roles.
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowDirectModal(false)} disabled={directSubmitting}>Cancel</button>
                  <button type="submit" className="btn" id="btn-confirm-direct-execute" style={{ background: 'linear-gradient(135deg,#10b981 0%,#059669 100%)', color: '#fff', boxShadow: '0 2px 10px rgba(16,185,129,0.35)' }} disabled={directSubmitting}>
                    <Zap size={15} />
                    {directSubmitting ? 'Executing...' : `Execute and Verify -- ${directAction}`}
                  </button>
                </div>
              </form>
            )}

            {directResult && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button className="btn btn-secondary" onClick={() => setShowDirectModal(false)}>Close</button>
                {execResultFailed && <button className="btn btn-primary" onClick={() => setDirectResult(null)}>Try Again</button>}
                {directResult.status === 'executing_recovery_verification' && (
                  <button className="btn btn-secondary" onClick={() => { setShowDirectModal(false); fetchIncidentData(); }}>
                    <RefreshCw size={14} /> Refresh Incident
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================================================================
          MODAL: Admin/Support Engineer AI-Recommended Approval Request
          ================================================================ */}
      {showRequestModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.82)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div className="glass-panel" style={{ maxWidth: '700px', width: '100%', padding: '28px', border: '1px solid var(--border-accent)', boxShadow: '0 24px 48px rgba(0,0,0,0.6)', maxHeight: '92vh', overflowY: 'auto' }}>

            {requestStep === 'recommendations' && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <Sparkles size={22} color="var(--accent-cyan)" />
                  <h3 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>AI-Recommended Remediation Requests</h3>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                  The analysis engine reviewed this incident's log evidence, patterns, and runbook knowledge base. Select a recommendation to pre-fill the request form, or proceed manually.
                </p>

                <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '12px 16px', marginBottom: '18px', display: 'flex', gap: '20px', flexWrap: 'wrap', fontSize: '13px' }}>
                  <div><span style={{ color: 'var(--text-dim)' }}>Incident: </span><strong style={{ color: '#fff' }}>{incident.title}</strong></div>
                  <div><span style={{ color: 'var(--text-dim)' }}>Severity: </span><span className={`badge badge-${incident.severity.toLowerCase()}`} style={{ fontSize: '11px' }}>{incident.severity}</span></div>
                  <div><span style={{ color: 'var(--text-dim)' }}>Service: </span><strong style={{ color: 'var(--accent-cyan)' }}>{incident.service}</strong></div>
                  {topCause && <div><span style={{ color: 'var(--text-dim)' }}>Top Hypothesis: </span><span style={{ color: '#fff' }}>{topCause.description.slice(0, 80)}{topCause.description.length > 80 ? '...' : ''}</span></div>}
                </div>

                {recsLoading && (
                  <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                    <RefreshCw size={24} style={{ opacity: 0.6 }} />
                    Analyzing incident evidence and retrieving recommendations...
                  </div>
                )}

                {recsError && !recsLoading && (
                  <div style={{ padding: '16px', background: 'rgba(244,63,94,0.10)', border: '1px solid var(--accent-rose)', borderRadius: '8px', color: '#fb7185', fontSize: '13px', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <AlertCircle size={14} />
                    {recsError} -- You can still submit a manual request below.
                  </div>
                )}

                {!recsLoading && !recsError && recommendations.length === 0 && (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)', background: 'var(--bg-secondary)', borderRadius: '8px', marginBottom: '16px' }}>
                    <Info size={20} style={{ opacity: 0.5, marginBottom: '8px' }} />
                    <div style={{ fontWeight: 600, color: '#fff' }}>Insufficient evidence for confident recommendation</div>
                    <p style={{ fontSize: '13px', marginTop: '4px' }}>The analysis engine could not determine a specific remediation pattern for this incident. Please use the manual form.</p>
                  </div>
                )}

                {!recsLoading && recommendations.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
                    {recommendations.map((rec, i) => {
                      const rc = riskColor(rec.riskLevel);
                      return (
                        <div key={i} style={{ background: 'var(--bg-secondary)', border: `1px solid ${i === 0 ? 'var(--border-accent)' : 'var(--border-subtle)'}`, borderRadius: '10px', padding: '16px 18px' }}>
                          {i === 0 && (
                            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                              <Target size={11} /> Best Match
                            </div>
                          )}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontWeight: 700, color: '#fff', fontSize: '15px', marginBottom: '2px' }}>{rec.actionTitle}</div>
                              <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{rec.actionName}</div>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0 }}>
                              <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 10px', borderRadius: '9999px', background: rc.bg, border: `1px solid ${rc.border}`, color: rc.text, textTransform: 'uppercase' }}>
                                {rec.riskLevel} risk
                              </span>
                              <span style={{ fontSize: '11px', color: rec.requiresApproval ? '#fbbf24' : '#34d399' }}>
                                {rec.requiresApproval ? 'Requires Approval' : 'No Approval Needed'}
                              </span>
                            </div>
                          </div>

                          <div style={{ fontSize: '13px', color: 'var(--text-main)', marginBottom: '10px', lineHeight: '1.5' }}>{rec.relevanceReason}</div>

                          {rec.supportingEvidence && rec.supportingEvidence.length > 0 && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                                <FileText size={11} /> Supporting Evidence
                              </div>
                              {rec.supportingEvidence.map((ev, j) => (
                                <div key={j} className="code-block" style={{ marginTop: '4px', fontSize: '11px' }}>{ev}</div>
                              ))}
                            </div>
                          )}

                          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--text-muted)', flexWrap: 'wrap', marginBottom: '12px' }}>
                            <div><strong>Expected:</strong> {rec.expectedOutcome}</div>
                            <div><strong>Service:</strong> {rec.affectedService}</div>
                            {rec.runbookReference && <div><strong>Runbook:</strong> {rec.runbookReference}</div>}
                            <div><strong>Confidence:</strong> <span style={{ color: '#fbbf24', fontWeight: 700 }}>{confidencePct(rec.confidence)}</span></div>
                          </div>

                          <button
                            className="btn btn-primary"
                            id={`btn-select-rec-${i}`}
                            style={{ width: '100%', justifyContent: 'center', fontSize: '13px' }}
                            onClick={() => selectRecommendation(rec)}
                          >
                            <CheckCheck size={15} /> Select This Request
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-dim)' }}>Prefer manual selection?</span>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button className="btn btn-secondary" onClick={() => setShowRequestModal(false)}>Cancel</button>
                    <button className="btn btn-secondary" onClick={() => setRequestStep('form')}>
                      <Wrench size={14} /> Fill Manually
                    </button>
                  </div>
                </div>
              </>
            )}

            {requestStep === 'form' && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <Wrench size={22} color="var(--accent-cyan)" />
                  <h3 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>Submit Remediation Request</h3>
                  {selectedRec && <span className="badge badge-info" style={{ fontSize: '11px' }}>AI Pre-filled</span>}
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                  Review and edit the fields below. You must explicitly submit -- AI recommendations do not auto-submit. Justification is required.
                </p>

                {selectedRec && (
                  <div style={{ padding: '10px 14px', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.25)', borderRadius: '8px', fontSize: '12px', color: 'var(--accent-cyan)', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <Info size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
                    Pre-filled from AI recommendation: <strong>{selectedRec.actionTitle}</strong>. Review all fields carefully before submitting.
                  </div>
                )}

                <form onSubmit={handleRequestSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Incident ID</label>
                    <input type="text" className="input-control" value={incidentId} disabled style={{ opacity: 0.65, fontFamily: 'var(--font-mono)', fontSize: '12px' }} />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Remediation Action</label>
                    <select className="input-control" value={reqAction} onChange={e => setReqAction(e.target.value)} style={{ width: '100%', fontSize: '13px' }}>
                      <option value="restart_demo_service">restart_demo_service -- Recovers DB pool exhaustion, 503, deadlock</option>
                      <option value="clear_demo_cache">clear_demo_cache -- Recovers memory leak, OOM, rate limits</option>
                      <option value="rollback_demo_config">rollback_demo_config -- Recovers bad configuration deployments</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Risk Classification</label>
                    <select className="input-control" value={reqRiskLevel} onChange={e => setReqRiskLevel(e.target.value)} style={{ width: '100%', fontSize: '13px' }}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>
                      Business / Operational Justification <span style={{ color: '#fb7185' }}>*</span>
                    </label>
                    <textarea className="input-control" rows={3} placeholder="Why is this action necessary? What evidence supports it?" value={reqJustification} onChange={e => setReqJustification(e.target.value)} required style={{ width: '100%', fontSize: '13px', resize: 'vertical' }} />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Expected Outcome</label>
                    <input type="text" className="input-control" placeholder="What should this action achieve?" value={reqExpectedOutcome} onChange={e => setReqExpectedOutcome(e.target.value)} style={{ fontSize: '13px' }} />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Runbook / Historical Incident Reference</label>
                    <input type="text" className="input-control" placeholder="e.g. Runbook: Demo-App Recovery Standard" value={reqRunbook} onChange={e => setReqRunbook(e.target.value)} style={{ fontSize: '13px' }} />
                  </div>

                  {reqEvidence.length > 0 && (
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>Supporting Evidence</label>
                      {reqEvidence.map((ev, i) => <div key={i} className="code-block" style={{ marginBottom: '4px', fontSize: '11px' }}>{ev}</div>)}
                    </div>
                  )}

                  {actionErrorMsg && (
                    <div style={{ padding: '10px 14px', background: 'rgba(244,63,94,0.12)', border: '1px solid var(--accent-rose)', borderRadius: '8px', color: '#fb7185', fontSize: '13px' }}>
                      {actionErrorMsg}
                    </div>
                  )}

                  <div style={{ background: 'rgba(56,189,248,0.08)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(56,189,248,0.2)', fontSize: '12px', color: 'var(--text-muted)' }}>
                    Dual-Authorization Guardrail: Zero shell execution. Requesters cannot approve their own actions. Post-remediation health checks verify recovery before the incident is marked resolved.
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                    <button type="button" className="btn btn-secondary" onClick={() => setRequestStep('recommendations')}>
                      <ArrowLeft size={14} /> Back to Recommendations
                    </button>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button type="button" className="btn btn-secondary" onClick={() => setShowRequestModal(false)} disabled={actionSubmitting}>Cancel</button>
                      <button type="submit" id="btn-submit-request" className="btn btn-primary" disabled={actionSubmitting || !reqJustification.trim()}>
                        {actionSubmitting ? 'Submitting...' : 'Submit Request to Senior Approver'}
                      </button>
                    </div>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
