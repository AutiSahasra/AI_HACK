import { 
  AuthResponse, 
  User, 
  UploadRecord, 
  LogEvent, 
  Incident, 
  Ticket, 
  RemediationActionDef, 
  ActionApprovalRecord, 
  AuditLogEntry, 
  Runbook, 
  HistoricalIncident 
} from '../types';

const API_BASE = '/api';

function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string) {
  localStorage.setItem('token', token);
}

export function clearToken() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

export function getStoredUser(): User | null {
  const u = localStorage.getItem('user');
  return u ? JSON.parse(u) : null;
}

export function setStoredUser(user: User) {
  localStorage.setItem('user', JSON.stringify(user));
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Set json content type if not multipart
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (credentials: { username: string; password: string }): Promise<AuthResponse> => {
    return request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },
  getMe: async (): Promise<User> => {
    return request<User>('/auth/me');
  },

  // Uploads
  uploadLogs: async (file: File): Promise<UploadRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    return request<UploadRecord>('/uploads', {
      method: 'POST',
      body: formData,
    });
  },
  getUploads: async (limit = 50): Promise<UploadRecord[]> => {
    return request<UploadRecord[]>(`/uploads?limit=${limit}`);
  },
  getUploadDetail: async (id: string): Promise<UploadRecord> => {
    return request<UploadRecord>(`/uploads/${id}`);
  },

  // Logs
  getLogs: async (params: {
    service?: string;
    severity?: string;
    source_type?: string;
    search?: string;
    upload_id?: string;
    fingerprint?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ items: LogEvent[]; total: number; page: number; page_size: number }> => {
    const query = new URLSearchParams();
    if (params.service) query.append('service', params.service);
    if (params.severity) query.append('severity', params.severity);
    if (params.source_type) query.append('source_type', params.source_type);
    if (params.search) query.append('search', params.search);
    if (params.upload_id) query.append('upload_id', params.upload_id);
    if (params.fingerprint) query.append('fingerprint', params.fingerprint);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    return request(`/logs?${query.toString()}`);
  },
  getServices: async (): Promise<string[]> => {
    return request<string[]>('/logs/services');
  },

  // Incidents
  getIncidents: async (params?: {
    status?: string;
    severity?: string;
    service?: string;
  }): Promise<Incident[]> => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.severity) query.append('severity', params.severity);
    if (params?.service) query.append('service', params.service);
    return request<Incident[]>(`/incidents?${query.toString()}`);
  },
  getIncident: async (id: string): Promise<Incident> => {
    return request<Incident>(`/incidents/${id}`);
  },
  submitFeedback: async (id: string, useful: boolean, notes?: string): Promise<{ success: boolean }> => {
    return request(`/incidents/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ useful, notes }),
    });
  },
  triggerRca: async (id: string): Promise<{ message: string }> => {
    return request(`/incidents/${id}/analyze`, { method: 'POST' });
  },

  // Tickets
  getTickets: async (): Promise<Ticket[]> => {
    return request<Ticket[]>('/tickets');
  },
  getTicket: async (id: string): Promise<Ticket> => {
    return request<Ticket>(`/tickets/${id}`);
  },
  updateTicketStatus: async (id: string, status: string): Promise<Ticket> => {
    return request<Ticket>(`/tickets/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },
  assignTicket: async (id: string, assignee: string): Promise<Ticket> => {
    return request<Ticket>(`/tickets/${id}/assign`, {
      method: 'PATCH',
      body: JSON.stringify({ assignee }),
    });
  },
  addTicketComment: async (id: string, text: string): Promise<Ticket> => {
    return request<Ticket>(`/tickets/${id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  // Remediation & Approvals
  getRemediationActions: async (): Promise<RemediationActionDef[]> => {
    return request<RemediationActionDef[]>('/remediation/actions');
  },
  requestAction: async (incidentId: string, actionName: string): Promise<ActionApprovalRecord> => {
    return request<ActionApprovalRecord>('/remediation/request', {
      method: 'POST',
      body: JSON.stringify({ incidentId, actionName }),
    });
  },
  getApprovals: async (status?: string): Promise<ActionApprovalRecord[]> => {
    const q = status ? `?status=${status}` : '';
    return request<ActionApprovalRecord[]>(`/remediation/approvals${q}`);
  },
  decideApproval: async (approvalId: string, decision: 'approved' | 'rejected', reason?: string): Promise<ActionApprovalRecord> => {
    return request<ActionApprovalRecord>(`/remediation/approvals/${approvalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason }),
    });
  },
  executeAction: async (approvalId: string): Promise<{ status: string; message: string }> => {
    return request(`/remediation/execute/${approvalId}`, { method: 'POST' });
  },

  // Audit Logs
  getAuditLogs: async (limit = 100): Promise<AuditLogEntry[]> => {
    return request<AuditLogEntry[]>(`/audit?limit=${limit}`);
  },

  // Knowledge / Runbooks & Historical
  getRunbooks: async (service?: string): Promise<Runbook[]> => {
    const q = service ? `?service=${service}` : '';
    return request<Runbook[]>(`/runbooks${q}`);
  },
  getHistoricalIncidents: async (service?: string): Promise<HistoricalIncident[]> => {
    const q = service ? `?service=${service}` : '';
    return request<HistoricalIncident[]>(`/historical-incidents${q}`);
  },

  // Admin & Sources
  getLiveSources: async (): Promise<Array<{ id: string; name: string; status: string; lastSeenAt: string; eventCount: number }>> => {
    return request('/admin/sources');
  },
  getDashboardStats: async (): Promise<any> => {
    return request('/admin/dashboard/stats');
  },
  getDemoStatus: async (): Promise<{ status: string; active_fault?: string; service?: string }> => {
    return request('/admin/demo/status');
  },
  injectDemoFault: async (faultType: string): Promise<any> => {
    return request('/admin/demo/inject-fault', {
      method: 'POST',
      body: JSON.stringify({ faultType }),
    });
  },
  resetDemoFault: async (): Promise<any> => {
    return request('/admin/demo/reset-fault', {
      method: 'POST',
    });
  },
};

