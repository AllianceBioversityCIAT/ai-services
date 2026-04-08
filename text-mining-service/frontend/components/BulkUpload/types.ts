export interface RawInstitution {
  institution_name: string;
  institution_id: string | null;
  similarity_score: number;
}

export interface RawUser {
  name: string;
  code: string | null;
  similarity_score: number;
}

export interface RawLanguage {
  name: string;
  code: string;
}

export interface RawCountry {
  code: string;
  areas?: string[];
}

export interface RawEvidence {
  evidence_link: string;
  evidence_description: string;
}

export interface BulkUploadResult {
  id: string | number;
  indicator?: string;
  title: string;
  description?: string;
  year?: string | number;
  contract_code?: string;
  sdg_targets?: string[];
  training_category?: string;
  training_type?: string;
  training_purpose?: string;
  start_date?: string;
  end_date?: string;
  delivery_modality?: string;
  length_of_training?: string;
  total_participants?: number;
  male_participants?: number;
  female_participants?: number;
  non_binary_participants?: number;
  degree?: string;
  trainee_name?: string;
  trainee_gender?: string;
  geoscope_level?: string;
  keywords?: string[];
  main_contact_person?: RawUser;
  training_supervisor?: RawUser;
  trainee_affiliation?: RawInstitution;
  language?: RawLanguage;
  partners?: RawInstitution[];
  trainees?: string;
  trainees_description?: RawInstitution[];
  countries?: RawCountry[];
  regions?: number[];
  evidences?: RawEvidence[];
  trainee_nationality?: RawCountry;
  asset_ip_owner_id?: number | string;
  asset_ip_owner_description?: string;
  publicity_restriction?: string;
  publicity_restriction_description?: string;
  potential_asset?: string;
  potential_asset_description?: string;
  requires_further_development?: string;
  requires_further_development_description?: string;
  batch_number?: number;
  [key: string]: unknown;
}

export interface UnmappedInstitution {
  record_id: string;
  record_title: string;
  source_field: string;
  institution_name: string;
  institution_id: string | null;
  similarity_score: number;
}

export interface RecordStatus {
  status: 'pending' | 'complete' | 'failed';
  link: string | null;
  errorMessage?: string;
}

export interface DynamoStatuses {
  complete: string[];
  failed: string[];
  links: Record<string, string>;
}

export interface StarApiResponse {
  data?: {
    results_created?: StarCreatedResult[];
    results_errors?: StarErrorResult[];
  };
}

export interface StarCreatedResult {
  error: boolean;
  title?: string;
  result_official_code?: string;
}

export interface StarErrorResult {
  error: boolean;
  title?: string;
  message_error?: string;
}

export type DocSource = 'upload' | 's3';

export type AppStep = 'upload' | 'unmapped' | 'results';

export type TabType = 'pending' | 'submitted';

export interface ColumnDef {
  key: string;
  label: string;
  type: 'checkbox' | 'text' | 'number' | 'textarea' | 'select' | 'status' | 'link' | 'chips' | 'partners' | 'sdg' | 'evidence_desc' | 'evidence_link' | 'training_purpose' | 'date' | 'countries' | 'regions' | 'affiliation' | 'nationality' | 'language';
  readonly?: boolean;
  required?: boolean;
  options?: string[];
  tooltip?: string;
  enabledWhen?: { field: string; values: (string | number)[] };
}
