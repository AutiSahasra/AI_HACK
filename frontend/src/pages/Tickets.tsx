import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Ticket, TicketPriority, TicketStatus } from '../types';
import { TicketCheck, MessageSquare, User, RefreshCw, Send, CheckCircle2 } from 'lucide-react';

export const Tickets: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [assigneeInput, setAssigneeInput] = useState('');

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets();
      setTickets(data);
      if (selectedTicket) {
        const refreshed = data.find(t => t.id === selectedTicket.id);
        if (refreshed) setSelectedTicket(refreshed);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const interval = setInterval(fetchTickets, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStatusChange = async (ticketId: string, status: string) => {
    try {
      const updated = await api.updateTicketStatus(ticketId, status);
      setSelectedTicket(updated);
      fetchTickets();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !assigneeInput.trim()) return;
    try {
      const updated = await api.assignTicket(selectedTicket.id, assigneeInput.trim());
      setSelectedTicket(updated);
      setAssigneeInput('');
      fetchTickets();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !commentText.trim()) return;
    try {
      const updated = await api.addTicketComment(selectedTicket.id, commentText.trim());
      setSelectedTicket(updated);
      setCommentText('');
      fetchTickets();
    } catch (e: any) {
      alert(e.message);
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

  const getStatusBadge = (s: TicketStatus) => {
    switch (s) {
      case 'resolved':
      case 'closed':
        return <span className="badge badge-resolved">{s}</span>;
      case 'verifying':
      case 'pending_approval':
        return <span className="badge badge-warn">{s}</span>;
      default:
        return <span className="badge badge-info">{s}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Incident Tickets & Resolution Board
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Auto-created operational tickets linked to correlated log incidents with strict lifecycle enforcement.
          </p>
        </div>
        <button onClick={fetchTickets} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedTicket ? '1.2fr 1fr' : '1fr', gap: '20px' }}>
        {/* Ticket List */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TicketCheck size={18} color="var(--accent-cyan)" />
            <span>Active Tickets ({tickets.length})</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {tickets.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-dim)' }}>
                No tickets created yet. Ingesting errors will auto-generate tickets.
              </div>
            ) : (
              tickets.map(t => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTicket(t)}
                  style={{
                    padding: '14px 18px',
                    background: selectedTicket?.id === t.id ? 'rgba(56, 189, 248, 0.08)' : 'var(--bg-secondary)',
                    border: selectedTicket?.id === t.id ? '1px solid var(--border-accent)' : '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '13px', color: 'var(--accent-cyan)' }}>
                        {t.id}
                      </span>
                      {getPriorityBadge(t.priority)}
                      {getStatusBadge(t.status)}
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      {new Date(t.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>
                    {t.title}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--text-dim)' }}>
                    <span>Assignee: <strong style={{ color: t.assignee ? '#fff' : 'var(--text-dim)' }}>{t.assignee || 'Unassigned'}</strong></span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MessageSquare size={13} /> {t.comments?.length || 0}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Selected Ticket Detail */}
        {selectedTicket && (
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px', color: 'var(--accent-cyan)' }}>
                    {selectedTicket.id}
                  </span>
                  {getPriorityBadge(selectedTicket.priority)}
                  {getStatusBadge(selectedTicket.status)}
                </div>
                <h3 style={{ fontSize: '16px', margin: 0 }}>{selectedTicket.title}</h3>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '12px' }}
                onClick={() => setSelectedTicket(null)}
              >
                Close
              </button>
            </div>

            {/* Lifecycle Controls */}
            <div style={{ background: 'var(--bg-secondary)', padding: '14px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '8px' }}>
                TRANSITION STATUS
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {['in_progress', 'pending_approval', 'resolved', 'closed'].map(st => (
                  <button
                    key={st}
                    className="btn btn-secondary"
                    style={{ fontSize: '12px', padding: '5px 10px', textTransform: 'capitalize' }}
                    onClick={() => handleStatusChange(selectedTicket.id, st)}
                  >
                    Set {st.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Assignment */}
            <form onSubmit={handleAssign} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="text"
                className="input-control"
                placeholder="Assign to engineer (e.g. support, approver)..."
                value={assigneeInput}
                onChange={e => setAssigneeInput(e.target.value)}
                style={{ fontSize: '13px' }}
              />
              <button type="submit" className="btn btn-primary" style={{ whiteSpace: 'nowrap', fontSize: '12px' }}>
                Assign
              </button>
            </form>

            {/* Comments Thread */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                Activity & Comments ({selectedTicket.comments?.length || 0})
              </div>
              <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedTicket.comments?.length === 0 ? (
                  <div style={{ fontSize: '12px', color: 'var(--text-dim)', padding: '8px' }}>
                    No comments yet. Post an update below.
                  </div>
                ) : (
                  selectedTicket.comments?.map(c => (
                    <div key={c.id} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px 12px', borderRadius: '6px', fontSize: '13px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px' }}>
                        <span><strong>{c.author}</strong> ({c.authorRole})</span>
                        <span>{new Date(c.createdAt).toLocaleTimeString()}</span>
                      </div>
                      <div>{c.text}</div>
                    </div>
                  ))
                )}
              </div>

              {/* Add Comment */}
              <form onSubmit={handleAddComment} style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <input
                  type="text"
                  className="input-control"
                  placeholder="Add resolution note or comment..."
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  style={{ fontSize: '13px' }}
                />
                <button type="submit" className="btn btn-primary" style={{ padding: '8px 14px' }}>
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
