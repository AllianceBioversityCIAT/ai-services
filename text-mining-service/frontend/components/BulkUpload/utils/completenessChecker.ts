import type { BulkUploadResult, RawInstitution, RawUser } from '../types';
import { RESEARCH_AREAS_MIN_YEAR, getPrimaryLeverOptions, parseResultYear } from '../constants';

export interface CompletenessResult {
  isComplete: boolean;
  reasons: string[];
  /** Actual field keys that are missing/invalid, e.g. ["title", "training_type"] */
  missing_fields: string[];
}

// =========================
// Helpers
// =========================

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

function isMappedInstitution(inst: RawInstitution): boolean {
  return inst.institution_id !== null &&
    inst.institution_id !== undefined &&
    inst.similarity_score >= 70;
}

function isMappedUser(user: RawUser): boolean {
  return user.code !== null &&
    user.code !== undefined &&
    user.similarity_score >= 70;
}

// =========================
// Main checker
// =========================

export function checkCompleteness(result: BulkUploadResult): CompletenessResult {
  const reasons: string[] = [];
  const fields = new Set<string>();
  const fail = (field: string, reason: string) => { reasons.push(reason); fields.add(field); };

  // ── Universal fields ──────────────────────────────────────────

  if (isEmpty(result.title)) fail('title', 'Title is required');
  if (isEmpty(result.year)) fail('year', 'Year is required');
  if (isEmpty(result.training_type)) fail('training_type', 'Training Type is required');

  // Primary Levers (year < 2026) / Research Areas (year >= 2026)
  const leverYear = parseResultYear(result.year);
  const leverLabel = leverYear === null
    ? 'Primary Levers / Research Areas'
    : leverYear >= RESEARCH_AREAS_MIN_YEAR ? 'Research Areas' : 'Primary Levers';

  if (isEmpty(result.primary_levers)) {
    fail('primary_levers', `${leverLabel} is required`);
  } else if (leverYear !== null) {
    const allowed = new Set(getPrimaryLeverOptions(result.year).map((o) => o.id));
    const invalid = (result.primary_levers as number[]).filter((id) => !allowed.has(Number(id)));
    if (invalid.length > 0) {
      fail('primary_levers', `${leverLabel}: ${invalid.length} selected option${invalid.length > 1 ? 's do' : ' does'} not belong to the ${leverYear} portfolio — please re-select`);
    }
  }

  // Main contact person
  if (!result.main_contact_person) {
    fail('main_contact_person', 'Main Contact Person is required');
  } else if (!isMappedUser(result.main_contact_person as RawUser)) {
    const name = (result.main_contact_person as RawUser).name;
    fail('main_contact_person', `Main Contact Person "${name}" could not be automatically matched — please add it manually`);
  }

  // Training supervisor (both types)
  if (!result.training_supervisor) {
    fail('training_supervisor', 'Training Supervisor is required');
  } else if (!isMappedUser(result.training_supervisor as RawUser)) {
    const name = (result.training_supervisor as RawUser).name;
    fail('training_supervisor', `Training Supervisor "${name}" could not be automatically matched — please add it manually`);
  }

  // Partners (required unless AI found none, in which case is_partner_not_applicable covers it)
  if (!result.is_partner_not_applicable) {
    if (!Array.isArray(result.partners) || result.partners.length === 0) {
      fail('partners', 'At least one Partner is required');
    } else {
      const unmapped = (result.partners as RawInstitution[]).filter((p) => !isMappedInstitution(p));
      if (unmapped.length > 0) {
        fail('partners',
          `${unmapped.length} partner${unmapped.length > 1 ? 's' : ''} could not be automatically matched — please add ${unmapped.length > 1 ? 'them' : 'it'} manually or submit a partner request`,
        );
      }
    }
  } else if (Array.isArray(result.partners) && result.partners.length > 0) {
    // User manually added partners after AI found none — validate mapping
    const unmapped = (result.partners as RawInstitution[]).filter((p) => !isMappedInstitution(p));
    if (unmapped.length > 0) {
      fail('partners',
        `${unmapped.length} partner${unmapped.length > 1 ? 's' : ''} could not be automatically matched — please add ${unmapped.length > 1 ? 'them' : 'it'} manually or submit a partner request`,
      );
    }
  }

  // Evidences
  if (!Array.isArray(result.evidences) || result.evidences.length === 0) {
    fail('evidences', 'At least one Evidence Link is required');
  } else {
    const emptyLinks = result.evidences.filter((e) => isEmpty(e.evidence_link));
    if (emptyLinks.length > 0) {
      fail('evidences', 'All evidence entries must have a URL');
    }
    const emptyDescs = result.evidences.filter((e) => isEmpty(e.evidence_description));
    if (emptyDescs.length > 0) {
      fail('evidences', 'All evidence entries must have a description');
    }
  }

  // IP Rights: asset_ip_owner_id
  if (isEmpty(result.asset_ip_owner_id)) {
    fail('asset_ip_owner_id', 'Asset IP Owner is required');
  } else if (result.asset_ip_owner_id === 4 || result.asset_ip_owner_id === 'Others') {
    if (isEmpty(result.asset_ip_owner_description)) {
      fail('asset_ip_owner_description', 'Asset IP Owner Description is required when "Others" is selected');
    }
  }

  // IP Rights: publicity_restriction
  if (isEmpty(result.publicity_restriction)) {
    fail('publicity_restriction', 'Publicity Restriction is required');
  } else if (result.publicity_restriction === 'Yes' && isEmpty(result.publicity_restriction_description)) {
    fail('publicity_restriction_description', 'Publicity Restriction Description is required when "Yes"');
  }

  // IP Rights: potential_asset
  if (isEmpty(result.potential_asset)) {
    fail('potential_asset', 'Potential Asset is required');
  } else if (result.potential_asset === 'Yes' && isEmpty(result.potential_asset_description)) {
    fail('potential_asset_description', 'Potential Asset Description is required when "Yes"');
  }

  // IP Rights: requires_further_development
  if (isEmpty(result.requires_further_development)) {
    fail('requires_further_development', 'Requires Further Development is required');
  } else if (result.requires_further_development === 'Yes' && isEmpty(result.requires_further_development_description)) {
    fail('requires_further_development_description', 'Further Development Description is required when "Yes"');
  }

  // Geoscope
  if (isEmpty(result.geoscope_level)) {
    fail('geoscope_level', 'Geoscope Level is required');
  } else {
    const level = result.geoscope_level as string;
    if (level === 'Regional') {
      if (!Array.isArray(result.regions) || result.regions.length === 0) {
        fail('regions', 'Regions is required for "Regional" geoscope');
      }
    } else if (level === 'National') {
      if (!Array.isArray(result.countries) || result.countries.length === 0) {
        fail('countries', 'Countries is required for "National" geoscope');
      }
    } else if (level === 'Sub-national') {
      if (!Array.isArray(result.countries) || result.countries.length === 0) {
        fail('countries', 'Countries is required for "Sub-national" geoscope');
      } else {
        const noAreas = result.countries.filter((c) => !c.areas || c.areas.length === 0);
        if (noAreas.length > 0) {
          fail('countries',
            `${noAreas.length} country${noAreas.length > 1 ? 'ies' : ''} must have at least one sub-national area`,
          );
        }
      }
    }
    // 'Global' and 'This is yet to be determined' → no geo requirement
  }

  // ── Branch: Group training ───────────────────────────

  if (result.training_type === 'Group training') {
    if (!result.total_participants || (result.total_participants as number) <= 0) {
      fail('total_participants', 'Total Participants is required for Group training');
    }
    if (isEmpty(result.training_purpose)) {
      fail('training_purpose', 'Training Purpose is required for Group training');
    }
    if (result.trainees === 'Yes') {
      if (!Array.isArray(result.trainees_description) || result.trainees_description.length === 0) {
        fail('trainees_description', 'Trainees Organizations are required when Trainees is "Yes"');
      } else {
        const unmapped = (result.trainees_description as RawInstitution[]).filter(
          (t) => !isMappedInstitution(t),
        );
        if (unmapped.length > 0) {
          fail('trainees_description',
            `${unmapped.length} trainee organization${unmapped.length > 1 ? 's' : ''} could not be automatically matched — please add ${unmapped.length > 1 ? 'them' : 'it'} manually or submit a partner request`,
          );
        }
      }
    }
  }

  // ── Degree: universal (applies whenever Long-term is set) ──
  if (result.length_of_training === 'Long-term' && isEmpty(result.degree)) {
    fail('degree', 'Degree is required when Length of Training is "Long-term"');
  }

  // ── Branch: Individual training ──────────────────────

  if (result.training_type === 'Individual training') {
    if (isEmpty(result.trainee_name)) fail('trainee_name', 'Trainee Name is required for Individual training');
    if (isEmpty(result.trainee_gender)) fail('trainee_gender', 'Trainee Gender is required for Individual training');
    if (isEmpty(result.trainee_nationality)) fail('trainee_nationality', 'Trainee Nationality is required for Individual training');

    if (isEmpty(result.length_of_training)) {
      fail('length_of_training', 'Length of Training is required for Individual training');
    }

    if (!result.trainee_affiliation) {
      fail('trainee_affiliation', 'Trainee Affiliation is required for Individual training');
    } else if (!isMappedInstitution(result.trainee_affiliation as RawInstitution)) {
      fail('trainee_affiliation', 'Trainee Affiliation could not be automatically matched — please add it manually or submit a partner request');
    }
  }

  return { isComplete: reasons.length === 0, reasons, missing_fields: Array.from(fields) };
}
