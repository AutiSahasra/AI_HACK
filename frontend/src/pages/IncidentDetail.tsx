import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, LogEvent } from '../types';
import { 
  ArrowLeft, 
  AlertTriangle, 
  Clock, 
  Layers, 
  Activity, 
  CheckCircle2, 
  ChevronDown, 
  ChevronRight, 
  Sparkles, 
  ThumbsUp, 
  ThumbsDown,
  Wrench,
  BookOpen,
  ShieldCheck
} from 'lucide-react';


export const IncidentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<boolean | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const fetchIncidentData = async () => {
    if (!id) return;
    try {
      const inc = await api.getIncident(id);
      setIncident(inc);
      const evs = await api.getLogs({ fingerprint: inc.fingerprint || undefined, service: inc.service });
      setEvents(evs.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidentData();
    const interval = setInterval(fetchIncidentData, 6000);
    return () => clearInterval(interval);
  }, [id]);

  const handleTriggerRca = async () => {
    if (!id) return;
    setAnalyzing(true);
    try {
      await api.triggerRca(id);
      await fetchIncidentData();
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFeedback = async (useful: boolean) => {
    if (!id) return;
    try {
      await api.submitFeedback(id, useful);
      setFeedbackSent(useful);
    } catch (e) {
      console.error(e);
    }
  };

  const [showActionModal, setShowActionModal] = useState(false);
  const [selectedAction, setSelectedAction] = useState('restart_demo_service');
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [actionErrorMsg, setActionErrorMsg] = useState<string | null>(null);

  const incidentId = incident ? (incident.id || (incident as any)._id || id || '') : '';

  const handleRequestActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentId) {
      setActionErrorMsg('Error: Incident ID missing.');
      return;
    }
    setActionSubmitting(true);
    setActionErrorMsg(null);
    try {
      const res = await api.requestAction(incidentId, selectedAction);
      setActionSuccessMsg(`Remediation action '${selectedAction}' requested successfully! Status: ${res.status}. Sent to Senior Approver queue.`);
      setShowActionModal(false);
      await fetchIncidentData();
    } catch (err: any) {
      setActionErrorMsg(err.message || 'Failed to request remediation action');
    } finally {
      setActionSubmitting(false);
    }
  };

  if (loading || !incident) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-dim)' }}>
        Loading incident investigation details...
      </div>
    );
  }

  const lifecycleStages = [
    'new',
    'analyzing',
    'analyzed',
    'awaiting_approval',
    'remediating',
    'verifying',
    'resolved'
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Navigation Header */}
      <div>
        <Link to="/incidents" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', textDecoration: 'none', fontSize: '13px', marginBottom: '12px' }}>
          <ArrowLeft size={16} /> Back to Incidents Feed
        </Link>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className={`badge badge-${incident.severity.toLowerCase()}`}>
                {incident.severity}
              </span>
              <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>
                Status: {incident.status}
              </span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {incident.service}
              </span>
              {incident.isRepeated && (
                <span className="badge badge-critical">Repeated Outage</span>
              )}
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>
              {incident.title}
            </h1>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => {
                setActionErrorMsg(null);
                setShowActionModal(true);
              }}
              className="btn btn-secondary"
            >
              <Wrench size={16} />
              <span>Request Remediation Action</span>
            </button>
            <button
              onClick={handleTriggerRca}
              className="btn btn-primary"
              disabled={analyzing}
            >
              <Sparkles size={16} />
              <span>{analyzing ? 'Analyzing...' : 'Run Copilot RCA'}</span>
            </button>
          </div>
        </div>

        {actionSuccessMsg && (
          <div className="glass-panel" style={{ marginTop: '14px', padding: '12px 18px', background: 'rgba(52, 211, 153, 0.15)', border: '1px solid var(--accent-emerald)', color: '#34d399', fontSize: '13px' }}>
            ✓ {actionSuccessMsg}
          </div>
        )}

        {actionErrorMsg && (
          <div className="glass-panel" style={{ marginTop: '14px', padding: '12px 18px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid var(--accent-rose)', color: '#fb7185', fontSize: '13px' }}>
            ✗ {actionErrorMsg}
          </div>
        )}

        {incident.ticketId && (
          <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-dim)' }}>
            Linked Ticket: <Link to="/tickets" style={{ color: 'var(--accent-cyan)', fontWeight: 600, textDecoration: 'none' }}>{incident.ticketId}</Link>
          </div>
        )}

        {incident.status === 'awaiting_approval' && (
          <div style={{
            marginTop: '14px',
            padding: '14px 18px',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid #f59e0b',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldCheck size={20} color="#f59e0b" />
              <div>
                <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '14px' }}>
                  Remediation Request Pending SRE Approval
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  A remediation action has been requested and is awaiting review in the protected approvals queue.
                </div>
              </div>
            </div>
            <Link to="/approvals" className="btn btn-secondary" style={{ borderColor: '#f59e0b', color: '#f59e0b', fontSize: '12px' }}>
              Go to Approvals Queue &rarr;
            </Link>
          </div>
        )}

        {incident.status === 'resolved' && (
          <div style={{
            marginTop: '14px',
            padding: '14px 18px',
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid var(--accent-emerald)',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <CheckCircle2 size={20} color="var(--accent-emerald)" />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--accent-emerald)', fontSize: '14px' }}>
                  Incident Resolved & Verified
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Remediation was executed and post-action health checks confirmed healthy recovery with zero error recurrence.
                </div>
              </div>
            </div>
            {incident.ticketId && (
              <Link to="/tickets" className="btn btn-secondary" style={{ fontSize: '12px' }}>
                Check Ticket Status &rarr;
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Remediation Request Modal */}
      {showActionModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{
            maxWidth: '520px',
            width: '100%',
            padding: '24px',
            border: '1px solid var(--border-accent)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wrench size={20} color="var(--accent-cyan)" />
              Request Allow-Listed Remediation
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '18px' }}>
              Under enterprise policy, protected actions require authorization from a Senior Approver. Submitting routes this request to the Approver queue.
            </p>

            <form onSubmit={handleRequestActionSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>
                  Target Incident ID
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={incidentId}
                  disabled
                  style={{ opacity: 0.7, fontFamily: 'var(--font-mono)', fontSize: '12px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>
                  Select Allow-Listed Action
                </label>
                <select
                  className="input-field"
                  value={selectedAction}
                  onChange={(e) => setSelectedAction(e.target.value)}
                  style={{ width: '100%', fontSize: '13px' }}
                >
                  <option value="restart_demo_service">restart_demo_service (Recovers DB pool exhaustion, 503, deadlock)</option>
                  <option value="clear_demo_cache">clear_demo_cache (Recovers memory leak, OOM, rate limits, disk space)</option>
                  <option value="rollback_demo_config">rollback_demo_config (Recovers bad configuration deployments)</option>
                </select>
              </div>

              <div style={{ background: 'rgba(56, 189, 248, 0.08)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.2)', fontSize: '12px', color: 'var(--text-muted)' }}>
                🔒 <strong>Dual-Authorization Guardrail:</strong> Zero shell execution. Requesters cannot approve their own actions. The action will be verified by a post-remediation health check before the incident can be resolved.
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowActionModal(false)}
                  disabled={actionSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={actionSubmitting}
                >
                  {actionSubmitting ? 'Submitting Request...' : 'Submit Request to Senior Approver'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lifecycle Progress Bar */}
      <div className="glass-panel" style={{ padding: '16px 24px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '12px', textTransform: 'uppercase' }}>
          Resolution Lifecycle
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
          {lifecycleStages.map((stage, idx) => {
            const isCurrent = incident.status === stage;
            const isPassed = lifecycleStages.indexOf(incident.status) > idx;
            return (
              <div key={stage} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 2 }}>
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: isCurrent ? 'var(--accent-cyan)' : isPassed ? 'var(--accent-emerald)' : 'var(--bg-secondary)',
                  color: isCurrent || isPassed ? '#fff' : 'var(--text-dim)',
                  border: isCurrent ? '2px solid #fff' : '1px solid var(--border-subtle)',
                  boxShadow: isCurrent ? 'var(--glow-cyan)' : undefined
                }}>
                  {isPassed ? '✓' : idx + 1}
                </div>
                <span style={{ fontSize: '11px', marginTop: '6px', color: isCurrent ? '#fff' : 'var(--text-dim)', textTransform: 'capitalize' }}>
                  {stage.replace('_', ' ')}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* RCA Findings Section (Phase 3 integrated UI) */}
      {incident.probableCauses && incident.probableCauses.length > 0 && (
        <div className="glass-panel" style={{ padding: '24px', border: '1px solid var(--border-accent)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={20} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '18px', margin: 0 }}>AI Root-Cause Hypotheses & Diagnostic Plan</h3>
              <span className="badge badge-info" style={{ fontSize: '11px' }}>
                Hypothesis – Unverified
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Was this diagnosis helpful?</span>
              <button
                className={`btn btn-secondary`}
                style={{ padding: '4px 10px', fontSize: '12px', background: feedbackSent === true ? 'rgba(16, 185, 129, 0.2)' : undefined }}
                onClick={() => handleFeedback(true)}
              >
                <ThumbsUp size={14} /> Yes
              </button>
              <button
                className={`btn btn-secondary`}
                style={{ padding: '4px 10px', fontSize: '12px', background: feedbackSent === false ? 'rgba(244, 63, 94, 0.2)' : undefined }}
                onClick={() => handleFeedback(false)}
              >
                <ThumbsDown size={14} /> No
              </button>
            </div>
          </div>

          {/* Probable Causes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
            {incident.probableCauses.map((cause, idx) => (
              <div key={idx} style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>Rank #{cause.rank}</span>
                    <span className={`badge badge-${cause.confidenceTier === 'high' ? 'resolved' : cause.confidenceTier === 'medium' ? 'warn' : 'critical'}`}>
                      Confidence: {(cause.confidence * 100).toFixed(0)}% ({cause.confidenceTier})
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>
                  {cause.description}
                </div>
                {cause.supportingEvidence && cause.supportingEvidence.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>
                      Cited Log Evidence Excerpt:
                    </div>
                    {cause.supportingEvidence.map((ev, i) => (
                      <div key={i} className="code-block" style={{ marginTop: '4px', fontSize: '12px' }}>
                        {ev.excerpt}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Facts vs AI Inferences */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div style={{ background: 'rgba(16, 21, 36, 0.8)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={16} /> Observed Facts (Directly Verified in Logs)
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--text-main)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {incident.observedFacts?.map((fact, i) => <li key={i}>{fact}</li>)}
              </ul>
            </div>
            <div style={{ background: 'rgba(16, 21, 36, 0.8)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
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

      {/* Correlated Event Timeline */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '18px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--accent-cyan)" />
          <span>Related Log Events Timeline ({events.length} captured)</span>
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {events.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)' }}>
              No correlated events found for this incident.
            </div>
          ) : (
            events.map(ev => {
              const evId = ev.id || ev._id || '';
              const isExpanded = expandedEventId === evId;
              return (
                <div
                  key={evId}
                  style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                    padding: '12px 16px',
                    cursor: 'pointer'
                  }}
                  onClick={() => setExpandedEventId(isExpanded ? null : evId)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                      <span className={`badge badge-${ev.severity.toLowerCase()}`}>
                        {ev.severity}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-dim)' }}>
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: '#fff' }}>
                        {ev.message.split('\n')[0]}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                      <div className="code-block" style={{ whiteSpace: 'pre-wrap' }}>
                        {ev.message}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
