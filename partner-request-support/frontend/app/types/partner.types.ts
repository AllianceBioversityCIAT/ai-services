export interface ClarisaMatch {
  clarisa_id: string;
  name: string;
  acronym: string;
  countries: string[];
  institution_type: string;
  website: string;
  scores: {
    cosine_similarity: number;
    fuzz_name_score: number;
    fuzz_acronym_score: number;
    final_score: number;
  };
}

export interface WebSearch {
  success: boolean;
  result?: string;
  error?: string;
}

export interface Partner {
  id: string;
  name: string;
  acronym: string;
  website: string;
  country: string;
  match_found: boolean;
  clarisa_match: ClarisaMatch | null;
  top_candidates: ClarisaMatch[];
  web_search: WebSearch | null;
  match_quality: 'excellent' | 'good' | 'fair' | 'no_match' | 'error';
  api_data?: {
    request_id: number;
    request_source: string;
    external_user: string;
    created_at: string;
  };
}

export type MatchQuality = 'excellent' | 'good' | 'fair' | 'no_match' | 'error';

export type ModalType = 'clarisa' | 'websearch' | 'candidates' | 'accept' | 'reject';
