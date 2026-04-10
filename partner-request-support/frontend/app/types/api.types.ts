export interface SyncInfo {
  sync_performed: boolean;
  institutions_before: number;
  institutions_after: number;
  new_institutions: number;
  modified_institutions: number;
  unchanged_institutions: number;
  total_processed: number;
  sync_message: string;
}

export interface ProcessingStats {
  total: number;
  matched: number;
  no_match: number;
  web_search_attempted: number;
  web_search_success: number;
  errors: number;
  excellent: number;
  good: number;
  fair: number;
  matched_percentage: number;
  no_match_percentage: number;
}

export interface CacheInfo {
  total_requests: number;
  cache_hits: number;
  cache_misses: number;
  from_cache: boolean;
  processed_new: boolean;
}

export interface ProcessingResults {
  partners: import('./partner.types').Partner[];
  stats: ProcessingStats;
  sync_info?: SyncInfo;
  cache_info?: CacheInfo;
}

export interface ApiPartnerRequest {
  id: number;
  partnerName: string;
  acronym: string;
  webPage: string | null;
  requestStatus: string;
  requestSource: string;
  externalUserName: string;
  created_at: string;
  countryDTO: {
    name: string;
    isoAlpha2: string;
  };
  institutionTypeDTO: {
    name: string;
  };
}

export interface ResponseMessage {
  type: 'success' | 'error';
  message: string;
}
