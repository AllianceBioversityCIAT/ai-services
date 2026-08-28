import type { ColumnDef } from './types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_MINING_API_BASE_URL;
export const S3_BUCKET = 'ai-services-ibd';
export const FOLDER_PATH = 'star/text-mining/files/test/bulk_upload/';
export const STAR_BASE_URL = process.env.NEXT_PUBLIC_STAR_API_BASE_URL;
export const MANAGEMENT_BASE_URL = process.env.NEXT_PUBLIC_MANAGEMENT_API_BASE_URL;
export const CLARISA_BASE_URL = process.env.NEXT_PUBLIC_CLARISA_API_BASE_URL;
export const CLARISA_COUNTRIES_URL = `${CLARISA_BASE_URL}/countries`;
export const CLARISA_INSTITUTION_TYPES_URL = `${CLARISA_BASE_URL}/institution-types`;
export const CLARISA_PARTNER_REQUEST_CREATE_URL = `${CLARISA_BASE_URL}/partner-requests/create`;
export const PARTNER_REQUEST_MIS_ACRONYM = 'STAR';
export const ENVIRONMENT_URL = `${MANAGEMENT_BASE_URL}/`;
export const STAR_API_URL = `${STAR_BASE_URL}/results/ai/formalize/bulk`;

// Hoisted: module-level maps (js-index-maps, js-cache-function-results)
export const ASSET_IP_OWNER_NAME_TO_ID: Record<string, number> = {
  'International Center for Tropical Agriculture - CIAT': 1,
  'Bioversity International': 2,
  'Bioversity International and International Center for Tropical Agriculture - CIAT': 3,
  Others: 4,
};

export const ASSET_IP_OWNER_ID_TO_NAME: Record<number, string> = {
  1: 'International Center for Tropical Agriculture - CIAT',
  2: 'Bioversity International',
  3: 'Bioversity International and International Center for Tropical Agriculture - CIAT',
  4: 'Others',
};

// ── Primary Levers / Research Areas ──────────────────────────────────────────
// STAR renamed "Primary Levers" to "Research Areas" for the 2026-2030 portfolio.
// Both share the same field (`primary_levers`) but use disjoint id ranges:
// levers 1-9 (year < 2026) and research areas 10-17 (year >= 2026).
export interface CatalogOption {
  id: number;
  name: string;
}

/** First year of the 2026-2030 portfolio. Research Areas and Strategic
 *  Objectives both key off this boundary. */
export const PORTFOLIO_2026_MIN_YEAR = 2026;

export const PRIMARY_LEVERS: CatalogOption[] = [
  { id: 1, name: 'Lever 1: Food Environments and Consumer Behavior' },
  { id: 2, name: 'Lever 2: Multifunctional Landscapes' },
  { id: 3, name: 'Lever 3: Climate Action' },
  { id: 4, name: 'Lever 4: Biodiversity for Food and Agriculture' },
  { id: 5, name: 'Lever 5: Digital Inclusion' },
  { id: 6, name: 'Lever 6: Crops for Nutrition and Health' },
  { id: 7, name: 'Lever 7: Gender and Inclusion' },
  { id: 8, name: 'Lever 8: Performance, Innovation and Strategic Analysis for Impact' },
  { id: 9, name: 'Other' },
];

export const RESEARCH_AREAS: CatalogOption[] = [
  { id: 10, name: 'Food Environments and Consumer Behavior' },
  { id: 11, name: 'Multifunctional Landscapes' },
  { id: 12, name: 'Climate Action' },
  { id: 13, name: 'Biodiversity for Food and Agriculture' },
  { id: 14, name: 'Digital Inclusion' },
  { id: 15, name: 'Crops for Nutrition and Health' },
  { id: 16, name: 'Gender and Inclusion' },
  { id: 17, name: 'Performance, Innovation and Strategic Analysis for Impact' },
];

export const PRIMARY_LEVER_ID_TO_NAME: Record<number, string> = Object.fromEntries(
  [...PRIMARY_LEVERS, ...RESEARCH_AREAS].map((o) => [o.id, o.name]),
);

/** Parses a result year; returns null when it is missing or not a 4-digit year. */
export function parseResultYear(year: unknown): number | null {
  const n = Number(String(year ?? '').trim());
  return Number.isInteger(n) && n > 1900 && n < 2100 ? n : null;
}

/**
 * Option list for a result's year: Research Areas from 2026 onwards, Primary
 * Levers before that. Returns an empty list when the year is unknown — the ids
 * of the two ranges must never be mixed in the same record.
 */
export function getPrimaryLeverOptions(year: unknown): CatalogOption[] {
  const parsed = parseResultYear(year);
  if (parsed === null) return [];
  return parsed >= PORTFOLIO_2026_MIN_YEAR ? RESEARCH_AREAS : PRIMARY_LEVERS;
}

/** Keeps only the ids that are valid for the result's year. */
export function filterLeversForYear(values: number[], year: unknown): number[] {
  const allowed = new Set(getPrimaryLeverOptions(year).map((o) => o.id));
  return values.filter((v) => allowed.has(v));
}

// ── Strategic Objectives ─────────────────────────────────────────────────────
// Only applies to the 2026-2030 portfolio; results before 2026 have no such
// field. Ids are independent of the Primary Lever ids — do not merge the maps.
export const STRATEGIC_OBJECTIVES: CatalogOption[] = [
  { id: 1, name: 'Bank on Agrobiodiversity' },
  { id: 2, name: 'Make Farms and Landscapes Thrive' },
  { id: 3, name: 'Unlock Climate Action' },
  { id: 4, name: 'Enable Healthy Food Choices' },
  { id: 5, name: 'Boost Inclusion and Prosperity' },
];

export const STRATEGIC_OBJECTIVE_ID_TO_NAME: Record<number, string> = Object.fromEntries(
  STRATEGIC_OBJECTIVES.map((o) => [o.id, o.name]),
);

/** Strategic Objectives only exist from 2026 onwards. */
export function strategicObjectivesApply(year: unknown): boolean {
  const parsed = parseResultYear(year);
  return parsed !== null && parsed >= PORTFOLIO_2026_MIN_YEAR;
}

/** Option list for a result's year — empty when the field does not apply. */
export function getStrategicObjectiveOptions(year: unknown): CatalogOption[] {
  return strategicObjectivesApply(year) ? STRATEGIC_OBJECTIVES : [];
}

/** Keeps only ids that exist in the catalog, and only when the year allows it. */
export function filterObjectivesForYear(values: number[], year: unknown): number[] {
  if (!strategicObjectivesApply(year)) return [];
  const allowed = new Set(STRATEGIC_OBJECTIVES.map((o) => o.id));
  return values.filter((v) => allowed.has(v));
}

export const NON_CAPDEV_FIELDS = [
  'evidence_for_stage',
  'policy_type',
  'stage_in_policy_process',
  'short_title',
  'innovation_nature',
  'innovation_type',
  'anticipated_users',
  'assess_readiness',
  'innovation_actors_detailed',
  'organizations',
  'organization_type',
  'organization_sub_type',
  'other_organization_type',
];

export const NUMERIC_FIELDS = [
  'total_participants',
  'male_participants',
  'female_participants',
  'non_binary_participants',
];

export const JSON_FIELDS = [
  'keywords',
  'primary_levers',
  'strategic_objectives',
  'countries',
  'evidences',
  'partners',
  'trainees_description',
];

export const OPTIONAL_STRING_FIELDS = [
  'description',
  'geoscope_level',
  'training_category',
  'training_purpose',
  'trainee_name',
  'trainee_gender',
  'training_type',
  'delivery_modality',
  'start_date',
  'end_date',
  'length_of_training',
  'alliance_main_contact_person_first_name',
  'alliance_main_contact_person_last_name',
  'degree',
  'trainees',
];

export const OPTIONAL_NESTED_OBJECTS = [
  'trainee_affiliation',
  'training_supervisor',
  'main_contact_person',
  'language',
  'trainee_nationality',
];

export const IP_RIGHTS_DESCRIPTION_FIELDS = [
  'asset_ip_owner_description',
  'publicity_restriction_description',
  'potential_asset_description',
  'requires_further_development_description',
];

export const IP_RIGHTS_YES_NO_FIELDS = [
  'publicity_restriction',
  'potential_asset',
  'requires_further_development',
];

// Hoisted: static column definitions (rendering-hoist-jsx pattern for data)
export const RESULTS_TABLE_COLUMNS: ColumnDef[] = [
  { key: 'select', label: 'Select', type: 'checkbox', width: '55px' },
  { key: 'id', label: 'ID', type: 'text', readonly: true, width: '70px', showInSubmitted: true },
  { key: 'status', label: 'Status', type: 'status', readonly: true, width: '125px', showInSubmitted: true },
  { key: 'completeness', label: 'Completeness', submittedLabel: 'STAR Status', type: 'completeness', readonly: true, width: '150px', showInSubmitted: true },
  { key: 'star_link', label: 'STAR Link', type: 'link', readonly: true, width: '150px', showInSubmitted: true },
  { key: 'title', label: 'Title', type: 'textarea', required: true, width: '350px', showInSubmitted: true },
  { key: 'description', label: 'Description', type: 'textarea', width: '485px' },
  { key: 'year', label: 'Year', type: 'text', width: '90px', showInSubmitted: true },
  { key: 'main_contact_person', label: 'Main Contact Name', type: 'staff', riskFlag: true, width: '200px' },
  { key: 'keywords', label: 'Keywords', type: 'chips', width: '400px' },
  { key: 'contract_code', label: 'Contract Code', type: 'text', width: '155px', showInSubmitted: true },
  {
    key: 'primary_levers',
    label: 'Primary Levers / Research Areas',
    type: 'primary_levers',
    required: true,
    tooltip: 'For the 2026-2030 portfolio, Primary Levers became Research Areas. The list shown depends on the result year.',
    width: '300px',
  },
  {
    key: 'strategic_objectives',
    label: 'Strategic Objectives',
    type: 'strategic_objectives',
    required: true,
    tooltip: 'Only applies to the 2026-2030 portfolio.',
    width: '280px',
  },
  { key: 'training_type', label: 'Training Type', type: 'select', options: ['Individual training', 'Group training'], riskFlag: true, width: '185px' },
  { key: 'training_category', label: 'Training Category', type: 'select', options: ['Training', 'Engagement'], width: '175px' },
  { key: 'length_of_training', label: 'Length of Training', type: 'select', options: ['Short-term', 'Long-term'], width: '175px' },
  { key: 'degree', label: 'Degree', type: 'select', options: ['PhD', 'MSc', 'BSc', 'Other'], enabledWhen: { field: 'length_of_training', values: ['Long-term'] }, width: '155px' },
  { key: 'total_participants', label: 'Total Participants', type: 'number', enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '170px' },
  { key: 'male_participants', label: 'Male Participants', type: 'number', enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '170px' },
  { key: 'female_participants', label: 'Female Participants', type: 'number', enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '180px' },
  { key: 'non_binary_participants', label: 'Non-binary Participants', type: 'number', enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '210px' },
  { key: 'training_purpose', label: 'Training Purpose', type: 'training_purpose', riskFlag: true, enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '240px' },
  { key: 'trainees', label: 'Trainees', type: 'select', options: ['Yes', 'No'], enabledWhen: { field: 'training_type', values: ['Group training'] }, width: '155px' },
  { key: 'trainees_description', label: 'Trainees Organizations', type: 'partners', riskFlag: true, enabledWhen: [{ field: 'training_type', values: ['Group training'] }, { field: 'trainees', values: ['Yes'] }], width: '300px' },
  { key: 'trainee_name', label: 'Trainee Name', type: 'text', enabledWhen: { field: 'training_type', values: ['Individual training'] }, width: '155px' },
  {
    key: 'trainee_gender',
    label: 'Trainee Gender',
    type: 'select',
    options: ['male', 'female', 'non-binary'],
    enabledWhen: { field: 'training_type', values: ['Individual training'] },
    width: '155px',
  },
  { key: 'trainee_affiliation', label: 'Trainee Affiliation', type: 'affiliation', riskFlag: true, enabledWhen: { field: 'training_type', values: ['Individual training'] }, width: '205px' },
  { key: 'trainee_nationality', label: 'Trainee Nationality', type: 'nationality', enabledWhen: { field: 'training_type', values: ['Individual training'] }, width: '205px' },
  { key: 'training_supervisor', label: 'Training Supervisor', type: 'staff', riskFlag: true, width: '230px' },
  { key: 'language', label: 'Language', type: 'language', width: '205px' },
  { key: 'start_date', label: 'Start Date', type: 'date', width: '164px' },
  { key: 'end_date', label: 'End Date', type: 'date', width: '164px' },
  { key: 'delivery_modality', label: 'Delivery Modality', type: 'select', options: ['in-person', 'virtual', 'hybrid'], width: '170px' },
  { key: 'partners', label: 'Partners', type: 'partners', riskFlag: true, width: '250px' },
  {
    key: 'geoscope_level',
    label: 'Geoscope Level',
    type: 'select',
    riskFlag: true,
    options: [
      'Global',
      'Regional',
      'National',
      'Sub-national',
      'This is yet to be determined',
    ],
    width: '190px',
  },
  { key: 'countries', label: 'Countries', type: 'countries', width: '155px' },
  { key: 'regions', label: 'Regions', type: 'regions', width: '155px' },
  { key: 'evidences', label: 'Evidence Link', type: 'evidence_link', width: '400px' },
  { key: 'evidences', label: 'Evidence Description', type: 'evidence_desc', width: '300px' },
  {
    key: 'asset_ip_owner_id',
    label: 'Asset IP Owner',
    type: 'select',
    options: [
      'International Center for Tropical Agriculture - CIAT',
      'Bioversity International',
      'Bioversity International and International Center for Tropical Agriculture - CIAT',
      'Others',
    ],
    width: '300px',
  },
  { key: 'asset_ip_owner_description', label: 'Asset IP Owner Description', type: 'text', enabledWhen: { field: 'asset_ip_owner_id', values: [4, 'Others'] }, width: '210px' },
  {
    key: 'publicity_restriction',
    label: 'Publicity Restriction',
    type: 'select',
    options: ['Yes', 'No'],
    width: '160px',
  },
  {
    key: 'publicity_restriction_description',
    label: 'Publicity Restriction Description',
    type: 'textarea',
    enabledWhen: { field: 'publicity_restriction', values: ['Yes'] },
    width: '250px',
  },
  {
    key: 'potential_asset',
    label: 'Potential Asset',
    type: 'select',
    options: ['Yes', 'No'],
    width: '160px',
  },
  { key: 'potential_asset_description', label: 'Potential Asset Description', type: 'textarea', enabledWhen: { field: 'potential_asset', values: ['Yes'] }, width: '230px' },
  {
    key: 'requires_further_development',
    label: 'Requires Further Development',
    type: 'select',
    options: ['Yes', 'No'],
    width: '230px',
  },
  {
    key: 'requires_further_development_description',
    label: 'Further Development Description',
    type: 'textarea',
    enabledWhen: { field: 'requires_further_development', values: ['Yes'] },
    width: '260px',
  },
];
