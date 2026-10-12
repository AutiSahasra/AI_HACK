import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { UploadRecord } from '../types';
import { UploadCloud, FileCheck, AlertTriangle, RefreshCw, FileText, CheckCircle2, XCircle } from 'lucide-react';

export const UploadLogs: React.FC = () => {
  const [uploads, setUploads] = useState<UploadRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedUpload, setSelectedUpload] = useState<UploadRecord | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchUploads = async () => {
    setLoading(true);
    try {
      const data = await api.getUploads();
      setUploads(data);
      if (selectedUpload) {
        const refreshed = data.find(u => u.id === selectedUpload.id);
        if (refreshed) setSelectedUpload(refreshed);
      }
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUploads();
    const interval = setInterval(fetchUploads, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (file: File) => {
    setErrorMsg(null);
    setUploading(true);
    try {
      const res = await api.uploadLogs(file);
      setSelectedUpload(res);
      await fetchUploads();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-resolved"><CheckCircle2 size={12} /> Completed</span>;
      case 'completed_with_errors':
        return <span className="badge badge-warn"><AlertTriangle size={12} /> Partial</span>;
      case 'failed':
        return <span className="badge badge-critical"><XCircle size={12} /> Failed</span>;
      case 'processing':
        return <span className="badge badge-info"><RefreshCw size={12} className="animate-spin" /> Processing</span>;
      default:
        return <span className="badge badge-info">{status}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Log File Ingestion
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Upload raw or structured logs (CSV, TXT, LOG, JSON, JSONL). Multi-line traces and sensitive fields are processed automatically.
          </p>
        </div>
        <button onClick={fetchUploads} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {errorMsg && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(244, 63, 94, 0.12)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '8px',
          color: '#fb7185',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: dragOver ? '2px dashed var(--accent-cyan)' : '2px dashed var(--border-subtle)',
          borderRadius: '16px',
          padding: '48px 24px',
          textAlign: 'center',
          background: dragOver ? 'rgba(56, 189, 248, 0.05)' : 'rgba(16, 21, 36, 0.4)',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.txt,.log,.json,.jsonl,.ndjson"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
            }
          }}
        />
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          background: 'rgba(56, 189, 248, 0.1)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          color: 'var(--accent-cyan)'
        }}>
          <UploadCloud size={32} />
        </div>
        <h3 style={{ fontSize: '17px', fontWeight: 600, marginBottom: '6px' }}>
          {uploading ? 'Parsing and normalizing log events...' : 'Drop log files here, or click to browse'}
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '480px', margin: '0 auto' }}>
          Supports CSV (auto-mapped headers), JSON array, newline-delimited JSONL, syslog, and raw app logs with multi-line exceptions. Up to 20MB.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedUpload ? '1fr 1fr' : '1fr', gap: '20px' }}>
        {/* Uploads History Table */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Ingestion History</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Parsed / Failed</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {uploads.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '24px' }}>
                      No uploads recorded yet. Upload a sample file above.
                    </td>
                  </tr>
                ) : (
                  uploads.map(u => (
                    <tr
                      key={u.id}
                      onClick={() => setSelectedUpload(u)}
                      style={{
                        cursor: 'pointer',
                        background: selectedUpload?.id === u.id ? 'rgba(56, 189, 248, 0.08)' : undefined
                      }}
                    >
                      <td style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileText size={16} color="var(--accent-cyan)" />
                        <span>{u.fileName}</span>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-muted)' }}>
                          {u.detectedFormat.toUpperCase()}
                        </span>
                      </td>
                      <td>{getStatusBadge(u.status)}</td>
                      <td>
                        <span style={{ color: '#34d399', fontWeight: 600 }}>{u.parsedCount}</span>
                        {u.failedCount > 0 && (
                          <span style={{ color: '#fb7185', fontWeight: 600, marginLeft: '6px' }}>
                            / {u.failedCount} err
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                        {new Date(u.createdAt).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Upload Details & Errors */}
        {selectedUpload && (
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileCheck size={18} color="var(--accent-cyan)" />
                <span>Upload Breakdown: {selectedUpload.fileName}</span>
              </h3>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '12px' }}
                onClick={() => setSelectedUpload(null)}
              >
                Close
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>STATUS</div>
                <div style={{ marginTop: '4px' }}>{getStatusBadge(selectedUpload.status)}</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>PARSED EVENTS</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#34d399' }}>
                  {selectedUpload.parsedCount}
                </div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>FAILED LINES</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: selectedUpload.failedCount > 0 ? '#fb7185' : 'var(--text-dim)' }}>
                  {selectedUpload.failedCount}
                </div>
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: '14px', marginBottom: '10px' }}>
                Line-by-Line Error Log ({selectedUpload.errors.length})
              </h4>
              {selectedUpload.errors.length === 0 ? (
                <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '8px', color: '#34d399', fontSize: '13px' }}>
                  All lines in this file parsed cleanly with 0 validation or syntax errors.
                </div>
              ) : (
                <div style={{ maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedUpload.errors.map((err, idx) => (
                    <div key={idx} style={{
                      padding: '10px 12px',
                      background: 'rgba(244, 63, 94, 0.08)',
                      border: '1px solid rgba(244, 63, 94, 0.2)',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#fb7185', fontWeight: 600 }}>
                        <span>Line {err.line}</span>
                        <span>{err.error}</span>
                      </div>
                      {err.raw && (
                        <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {err.raw}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
