export interface Claim {
  statement: string;
  citation_id: string;
  typology?: string;
}

export interface AgentArgument {
  summary: string;
  claims: Claim[];
}

export interface Verdict {
  verdict: "escalate" | "close" | "needs_review";
  confidence: number;
  narrative: string;
  citations: string[];
}

export interface InvestigationResult {
  case_id: string;
  prosecutor: AgentArgument;
  defense: AgentArgument;
  verdict: Verdict;
  flagged_for_review: boolean;
  uncited_claims: string[];
  source: "live" | "cache";
}

export type DemoRole = "junior_investigator" | "senior_investigator" | "compliance_officer";

export type Typology = "structuring" | "round_tripping" | "mule_hub" | "none";

export interface CaseSummary {
  case_id: string;
  typology_guess: Typology;
  risk_score: number;
  status: string;
  account_count: number;
  alert_count: number;
}

export interface ClientProfile {
  age_range: string;
  generation: string;
  tenure_years: number;
  income_after_tax_range: string;
  credit_score_range: string;
  occupation: string;
  residence_country: string;
  non_resident_tax_flag: number;
  new_to_canada_segment: number;
  digital_enrolled: number;
  digital_active_ind: number;
  mobile_auth_ind: number;
  active_product_count: number;
  total_relationship_balance: number;
  profitability_segment: string;
  vulnerability_segment: string;
  wallet_band_segment: string;
  client_product_segment: string;
  staff_flag: number;
}

export interface Account {
  account_id: string;
  display_name: string;
  account_type: string;
  kyc_notes: string;
  profile: ClientProfile | null;
}

export interface Transaction {
  txn_id: string;
  from_account: string;
  to_account: string;
  amount: number;
  ts: string;
}

export interface Alert {
  alert_id: string;
  account_id: string;
  txn_id: string;
  reason: string;
  raised_at: string;
}

export interface PlaybookItem {
  id: string;
  criterion: string;
  matched: boolean;
  evidence: string;
}

export interface BehavioralSignal {
  account_id: string;
  signal: string;
  label: string;
  detail: string;
}

export interface CaseDetail {
  case_id: string;
  typology_guess: Typology;
  risk_score: number;
  status: string;
  accounts: Account[];
  transactions: Transaction[];
  alerts: Alert[];
  playbook: PlaybookItem[];
  behavioral_signals: BehavioralSignal[];
}

export interface AuditEntry {
  action: string;
  actor: string;
  payload: Record<string, unknown>;
  timestamp: string;
  row_hash: string;
}
