export type GmailSource =
  | "workday"
  | "greenhouse"
  | "lever"
  | "linkedin"
  | "indeed"
  | "company_email"
  | "unknown";

export type GmailClassificationLabel =
  | "NEW_APPLICATION"
  | "APPLICATION_UPDATE"
  | "INTERVIEW"
  | "REJECTION"
  | "OFFER"
  | "JOB_ALERT"
  | "IRRELEVANT"
  | "UNKNOWN";

export type GmailImportAction = "create" | "update" | "skip";
export type GmailImportStatus = "pending" | "imported" | "skipped" | "failed";
export type GmailImportPreviewSessionStatus = "queued" | "processing" | "completed" | "failed" | "preview";

export interface GmailCandidate {
  value: string;
  confidence: number;
  source: string;
}

export interface GmailIdentifierCandidates {
  gmail_thread_id: GmailCandidate[];
}

export interface GmailEmailContent {
  snippet?: string | null;
  body_text?: string | null;
  from_email?: string | null;
  from_domain?: string | null;
}

export interface GmailClassificationResult {
  label: GmailClassificationLabel;
  confidence: number;
  reasons: string[];
}

export interface GmailJobDraft {
  title?: string | null;
  company?: string | null;
  location?: string | null;
  job_description?: string | null;
  applied_date?: string | null;
  follow_up_date?: string | null;
  resume_path?: string | null;
  status?: string | null;
  job_board_id?: string | null;
  job_link?: string | null;
  source?: string | null;
  notes?: string | null;
  gmail_thread_id?: string | null;
}

export interface GmailUpdateItems {
  status?: string | null;
  follow_up_date?: string | null;
  job_link?: string | null;
  job_board_id?: string | null;
  company?: string | null;
  title?: string | null;
  notes?: string | null;
  gmail_thread_id?: string | null;
}

export interface GmailExtractionCandidates {
  title: GmailCandidate[];
  company: GmailCandidate[];
  location: GmailCandidate[];
  identifiers: GmailIdentifierCandidates;
}

export interface GmailMatchCandidate {
  job_id: number;
  company: string;
  title: string;
  status?: string | null;
  match_level: "thread" | "company_title";
  match_score: number;
  match_reasons: string[];
  requires_review: boolean;
}

export interface GmailParsedMessageReview {
  gmail_message_id: string;
  thread_id?: string | null;
  from: string;
  subject: string;
  date?: string | null;
  source: GmailSource;
  email_content: GmailEmailContent;
  classification: GmailClassificationResult;
  job_draft?: GmailJobDraft | null;
  update_items?: GmailUpdateItems | null;
  extraction_candidates: GmailExtractionCandidates;
  match_candidates: GmailMatchCandidate[];
  best_match?: GmailMatchCandidate | null;
  import_item_id?: number | null;
  import_status?: GmailImportStatus | null;
  selected_action?: GmailImportAction | null;
  linked_job_id?: number | null;
  already_processed: boolean;
  needs_review: boolean;
}

export interface GmailImportSessionSummary {
  id: number;
  start_date: string;
  end_date: string;
  status: GmailImportPreviewSessionStatus;
  total_emails: number;
  new_items: number;
  cached_items: number;
  cache_hit: boolean;
  imported_items: number;
  skipped_items: number;
  failed_items: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GmailImportPreviewStartResponse {
  session: GmailImportSessionSummary;
}

export interface GmailImportPreviewResponse {
  session: GmailImportSessionSummary;
  count: number;
  jobs: GmailParsedMessageReview[];
}

export interface GmailImportItemSelection {
  gmail_message_id: string;
  action: GmailImportAction;
  target_job_id?: number | null;
  job_draft?: GmailJobDraft | null;
  update_items?: GmailUpdateItems | null;
}

export interface GmailImportCommitRequest {
  session_id: number;
  items: GmailImportItemSelection[];
}

export interface GmailImportCommitResult {
  gmail_message_id: string;
  action: GmailImportAction;
  status: GmailImportStatus;
  linked_job_id?: number | null;
  error?: string | null;
}

export interface GmailImportCommitResponse {
  session: GmailImportSessionSummary;
  results: GmailImportCommitResult[];
}

export interface GmailStatusResponse {
  authorized: boolean;
  message?: string;
  token_expired?: boolean;
  requires_reauth?: boolean;
  detail?: string;
}
