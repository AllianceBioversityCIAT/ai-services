import type { ColumnDef } from './types';

export const API_BASE_URL = 'http://localhost:8000';
export const S3_BUCKET = 'ai-services-ibd';
export const FOLDER_PATH = 'star/text-mining/files/test/bulk_upload/';
export const ENVIRONMENT_URL = 'https://management-allianceindicatorstest.ciat.cgiar.org/api/';
export const STAR_API_URL =
  'https://main-allianceindicatorstest.ciat.cgiar.org/api/results/ai/formalize/bulk';

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
  'sdg_targets',
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
  { key: 'select', label: 'Select', type: 'checkbox' },
  { key: 'id', label: 'ID', type: 'text', readonly: true },
  { key: 'status', label: 'Status', type: 'status', readonly: true },
  { key: 'star_link', label: 'STAR Link', type: 'link', readonly: true },
  { key: 'title', label: 'Title', type: 'textarea', required: true },
  { key: 'description', label: 'Description', type: 'textarea' },
  { key: 'year', label: 'Year', type: 'text' },
  { key: 'contract_code', label: 'Contract Code', type: 'text' },
  { key: 'sdg_targets', label: 'SDG Targets', type: 'sdg' },
  {
    key: 'training_category',
    label: 'Training Category',
    type: 'select',
    options: ['Training', 'Engagement'],
  },
  {
    key: 'training_type',
    label: 'Training Type',
    type: 'select',
    options: ['Individual training', 'Group training'],
  },
  { key: 'training_purpose', label: 'Training Purpose', type: 'training_purpose' },
  { key: 'start_date', label: 'Start Date', type: 'text' },
  { key: 'end_date', label: 'End Date', type: 'text' },
  {
    key: 'delivery_modality',
    label: 'Delivery Modality',
    type: 'select',
    options: ['in-person', 'virtual', 'hybrid'],
  },
  {
    key: 'length_of_training',
    label: 'Length of Training',
    type: 'select',
    options: ['Short-term', 'Long-term'],
  },
  { key: 'total_participants', label: 'Total Participants', type: 'number' },
  { key: 'male_participants', label: 'Male Participants', type: 'number' },
  { key: 'female_participants', label: 'Female Participants', type: 'number' },
  { key: 'non_binary_participants', label: 'Non-binary Participants', type: 'number' },
  { key: 'degree', label: 'Degree', type: 'select', options: ['PhD', 'MSc', 'BSc', 'Other'] },
  { key: 'trainee_name', label: 'Trainee Name', type: 'text' },
  {
    key: 'trainee_gender',
    label: 'Trainee Gender',
    type: 'select',
    options: ['male', 'female', 'non-binary'],
  },
  {
    key: 'geoscope_level',
    label: 'Geoscope Level',
    type: 'select',
    options: [
      'Global',
      'Regional',
      'National',
      'Sub-national',
      'This is yet to be determined',
    ],
  },
  { key: 'keywords', label: 'Keywords', type: 'chips' },
  { key: 'main_contact_person.name', label: 'Main Contact Name', type: 'text' },
  { key: 'training_supervisor.name', label: 'Training Supervisor', type: 'text' },
  { key: 'trainee_affiliation.institution_name', label: 'Trainee Affiliation', type: 'text' },
  { key: 'language.name', label: 'Language', type: 'text' },
  { key: 'partners', label: 'Partners', type: 'partners' },
  { key: 'trainees', label: 'Trainees', type: 'select', options: ['Yes', 'No'] },
  { key: 'trainees_description', label: 'Trainees Organizations', type: 'textarea' },
  { key: 'countries', label: 'Countries', type: 'textarea' },
  { key: 'regions', label: 'Regions', type: 'textarea' },
  { key: 'evidences', label: 'Evidence Description', type: 'evidence_desc' },
  { key: 'evidences', label: 'Evidence Link', type: 'evidence_link' },
  { key: 'trainee_nationality.code', label: 'Trainee Nationality Code', type: 'text' },
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
  },
  { key: 'asset_ip_owner_description', label: 'Asset IP Owner Description', type: 'text' },
  {
    key: 'publicity_restriction',
    label: 'Publicity Restriction',
    type: 'select',
    options: ['Yes', 'No'],
  },
  {
    key: 'publicity_restriction_description',
    label: 'Publicity Restriction Description',
    type: 'textarea',
  },
  {
    key: 'potential_asset',
    label: 'Potential Asset',
    type: 'select',
    options: ['Yes', 'No'],
  },
  { key: 'potential_asset_description', label: 'Potential Asset Description', type: 'textarea' },
  {
    key: 'requires_further_development',
    label: 'Requires Further Development',
    type: 'select',
    options: ['Yes', 'No'],
  },
  {
    key: 'requires_further_development_description',
    label: 'Further Development Description',
    type: 'textarea',
  },
];
