export type UserRole = 'support_engineer' | 'approver';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type LogSeverity = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
export type SourceType = 'manual_upload' | 'live';
export type ParseStatus = 'ok' | 'partial' | 'failed';

export interface LogSourceMeta {
  type: SourceType;
  sourceId: string;
  fileName?: string | null;
  uploadId?: string | null;
}

export interface LogEvent {
  id?: string;
  _id?: string;
  timestamp: string;
  ingestedAt: string;
  service: string;
  severity: LogSeverity;
  message: string;
  source: LogSourceMeta;
  traceId?: string | null;
  requestId?: string | null;
  hostId?: string | null;
  attributes: Record<string, unknown>;
  parseStatus: ParseStatus;
  parseError?: string | null;
  fingerprint: string;
  redacted: boolean;
}

export type UploadStatus = 'pending' | 'processing' | 'completed' | 'completed_with_errors' | 'failed';

export interface LineError {
  line: number;
  raw: string;
  error: string;
}

export interface UploadRecord {
  id: string;
  fileName: string;
  fileSize: number;
  detectedFormat: string;
  status: UploadStatus;
  parsedCount: number;
  failedCount: number;
  errors: LineError[];
  uploadedBy: string;
  createdAt: string;
  completedAt?: string | null;
}

// Phase 2 Incident Types
export type IncidentStatus = 
  | 'new' 
  | 'analyzing' 
  | 'analyzed' 
  | 'awaiting_approval' 
  | 'remediating' 
  | 'verifying' 
  | 'resolved' 
  | 'escalated' 
  | 'failed_analysis';

export interface ProbableCause {
  rank: number;
  description: string;
  confidence: number;
  confidenceTier: 'low' | 'medium' | 'high';
  supportingEvidence: Array<{ eventId?: string; excerpt: string }>;
  alternativeExplanations?: string;
  assumptions?: string;
  verified?: boolean;
}

export interface DiagnosticCheck {
  step: string;
  rationale: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: LogSeverity;
  service: string;
  status: IncidentStatus;
  sources: string[];
  eventRefs: string[];
  eventCount: number;
  firstSeen: string;
  lastSeen: string;
  matchedRules: string[];
  fingerprint?: string;
  probableCauses: ProbableCause[];
  observedFacts: string[];
  aiInferences: string[];
  diagnosticChecks: DiagnosticCheck[];
  recommendedRunbookIds: string[];
  overallUncertainty?: string;
  insufficientEvidence?: boolean;
  ticketId?: string | null;
  escalationReason?: string | null;
  isRepeated?: boolean;
  createdAt: string;
  updatedAt: string;
}

export type TicketPriority = 'P1' | 'P2' | 'P3' | 'P4';
export type TicketStatus = 'open' | 'in_progress' | 'pending_approval' | 'verifying' | 'resolved' | 'closed' | 'escalated' | 'reopened';

export interface TicketComment {
  id: string;
  author: string;
  authorRole: UserRole;
  text: string;
  createdAt: string;
}

export interface Ticket {
  id: string;
  incidentId: string;
  title: string;
  priority: TicketPriority;
  status: TicketStatus;
  assignee?: string | null;
  comments: TicketComment[];
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string | null;
}

export interface RemediationActionDef {
  id: string;
  name: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requiresApproval: boolean;
  requiresDualApproval?: boolean;
  allowedRoles: UserRole[];
  executorKey: string;
  associatedHealthCheck: string;
  timeoutSeconds: number;
}

export interface RemediationRecommendation {
  actionName: string;
  actionTitle: string;
  relevanceReason: string;
  supportingEvidence: string[];
  expectedOutcome: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  affectedService: string;
  parameters: Record<string, any>;
  requiresApproval: boolean;
  confidence: number;
  runbookReference?: string | null;
  historicalIncidentReference?: string | null;
}

export interface ActionApprovalRecord {
  id: string;
  incidentId: string;
  actionName: string;
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed';
  requestedBy: string;
  requestedByRole: UserRole;
  approvedBy?: string | null;
  approvedByRole?: UserRole | null;
  rejectionReason?: string | null;
  parameters?: Record<string, any>;
  justification?: string | null;
  riskLevel?: string | null;
  expectedOutcome?: string | null;
  supportingEvidence?: string[];
  runbookReference?: string | null;
  verificationStatus?: string | null;
  verificationError?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  actor: string;
  role: UserRole;
  entityType: string;
  entityId: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface Runbook {
  id: string;
  title: string;
  service: string;
  description: string;
  diagnosticSteps: string[];
  remediationSteps: string[];
  riskLevel: string;
  prerequisites: string[];
  recoveryCheck: string;
  suggestedAction?: string;
}

export interface HistoricalIncident {
  id: string;
  title: string;
  service: string;
  summary: string;
  verifiedCause: string;
  remediationPerformed: string;
  outcome: string;
  logExcerpt: string;
}
