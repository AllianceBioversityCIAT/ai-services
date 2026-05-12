import type { ColumnDef } from './types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_MINING_API_BASE_URL;
export const S3_BUCKET = 'ai-services-ibd';
export const FOLDER_PATH = 'star/text-mining/files/test/bulk_upload/';
export const STAR_BASE_URL = process.env.NEXT_PUBLIC_STAR_API_BASE_URL;
export const MANAGEMENT_BASE_URL = process.env.NEXT_PUBLIC_MANAGEMENT_API_BASE_URL;
export const CLARISA_BASE_URL = process.env.NEXT_PUBLIC_CLARISA_API_BASE_URL;
export const ENVIRONMENT_URL = `${MANAGEMENT_BASE_URL}/`;
export const STAR_API_URL = `${STAR_BASE_URL}/results/ai/formalize/bulk`;
// TODO: replace with the real submit+approve endpoint when available from STAR team
export const STAR_SUBMIT_APPROVE_API_URL: string | undefined = process.env.NEXT_PUBLIC_STAR_SUBMIT_APPROVE_API_URL;

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
  { key: 'completeness', label: 'Completeness', type: 'completeness', readonly: true, width: '130px', showInSubmitted: true },
  { key: 'star_link', label: 'STAR Link', type: 'link', readonly: true, width: '150px', showInSubmitted: true },
  { key: 'title', label: 'Title', type: 'textarea', required: true, width: '350px', showInSubmitted: true },
  { key: 'description', label: 'Description', type: 'textarea', width: '485px' },
  { key: 'year', label: 'Year', type: 'text', width: '90px', showInSubmitted: true },
  { key: 'main_contact_person', label: 'Main Contact Name', type: 'staff', riskFlag: true, width: '200px' },
  { key: 'keywords', label: 'Keywords', type: 'chips', width: '400px' },
  { key: 'contract_code', label: 'Contract Code', type: 'text', width: '155px', showInSubmitted: true },
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
