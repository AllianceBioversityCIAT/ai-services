import type { BulkUploadResult, RawInstitution, RawUser } from '../types';

export interface CompletenessResult {
  isComplete: boolean;
  reasons: string[];
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
    inst.similarity_score > 70;
}

function isMappedUser(user: RawUser): boolean {
  return user.code !== null &&
    user.code !== undefined &&
    user.similarity_score > 70;
}

// =========================
// Main checker
// =========================

export function checkCompleteness(result: BulkUploadResult): CompletenessResult {
  const reasons: string[] = [];

  // ── Universal fields ─────────────────────────────────

  if (isEmpty(result.title)) reasons.push('Title is required');
  if (isEmpty(result.year)) reasons.push('Year is required');
  if (isEmpty(result.training_type)) reasons.push('Training Type is required');

  // Main contact person
  if (!result.main_contact_person) {
    reasons.push('Main Contact Person is required');
  } else if (!isMappedUser(result.main_contact_person as RawUser)) {
    reasons.push('Main Contact Person is not mapped (similarity ≤ 70 or missing staff ID)');
  }

  // Training supervisor (both types)
  if (!result.training_supervisor) {
    reasons.push('Training Supervisor is required');
  } else if (!isMappedUser(result.training_supervisor as RawUser)) {
    reasons.push('Training Supervisor is not mapped (similarity ≤ 70 or missing staff ID)');
  }

  // Partners (required, at least one, all mapped)
  if (!Array.isArray(result.partners) || result.partners.length === 0) {
    reasons.push('At least one Partner is required');
  } else {
    const unmapped = (result.partners as RawInstitution[]).filter((p) => !isMappedInstitution(p));
    if (unmapped.length > 0) {
      reasons.push(
        `${unmapped.length} partner${unmapped.length > 1 ? 's' : ''} not mapped (similarity ≤ 70 or missing institution ID)`,
      );
    }
  }

  // Evidences
  if (!Array.isArray(result.evidences) || result.evidences.length === 0) {
    reasons.push('At least one Evidence Link is required');
  } else {
    const emptyLinks = result.evidences.filter((e) => isEmpty(e.evidence_link));
    if (emptyLinks.length > 0) {
      reasons.push('All evidence entries must have a URL');
    }
  }

  // IP Rights: asset_ip_owner_id
  if (isEmpty(result.asset_ip_owner_id)) {
    reasons.push('Asset IP Owner is required');
  } else if (result.asset_ip_owner_id === 4 || result.asset_ip_owner_id === 'Others') {
    if (isEmpty(result.asset_ip_owner_description)) {
      reasons.push('Asset IP Owner Description is required when "Others" is selected');
    }
  }

  // IP Rights: publicity_restriction
  if (isEmpty(result.publicity_restriction)) {
    reasons.push('Publicity Restriction is required');
  } else if (result.publicity_restriction === 'Yes' && isEmpty(result.publicity_restriction_description)) {
    reasons.push('Publicity Restriction Description is required when "Yes"');
  }

  // IP Rights: potential_asset
  if (isEmpty(result.potential_asset)) {
    reasons.push('Potential Asset is required');
  } else if (result.potential_asset === 'Yes' && isEmpty(result.potential_asset_description)) {
    reasons.push('Potential Asset Description is required when "Yes"');
  }

  // IP Rights: requires_further_development
  if (isEmpty(result.requires_further_development)) {
    reasons.push('Requires Further Development is required');
  } else if (result.requires_further_development === 'Yes' && isEmpty(result.requires_further_development_description)) {
    reasons.push('Further Development Description is required when "Yes"');
  }

  // Geoscope
  if (isEmpty(result.geoscope_level)) {
    reasons.push('Geoscope Level is required');
  } else {
    const level = result.geoscope_level as string;
    if (level === 'Regional') {
      if (!Array.isArray(result.regions) || result.regions.length === 0) {
        reasons.push('Regions is required for "Regional" geoscope');
      }
    } else if (level === 'National') {
      if (!Array.isArray(result.countries) || result.countries.length === 0) {
        reasons.push('Countries is required for "National" geoscope');
      }
    } else if (level === 'Sub-national') {
      if (!Array.isArray(result.countries) || result.countries.length === 0) {
        reasons.push('Countries is required for "Sub-national" geoscope');
      } else {
        const noAreas = result.countries.filter((c) => !c.areas || c.areas.length === 0);
        if (noAreas.length > 0) {
          reasons.push(
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
      reasons.push('Total Participants is required for Group training');
    }
    if (isEmpty(result.training_purpose)) {
      reasons.push('Training Purpose is required for Group training');
    }
    if (result.trainees === 'Yes') {
      if (!Array.isArray(result.trainees_description) || result.trainees_description.length === 0) {
        reasons.push('Trainees Organizations are required when Trainees is "Yes"');
      } else {
        const unmapped = (result.trainees_description as RawInstitution[]).filter(
          (t) => !isMappedInstitution(t),
        );
        if (unmapped.length > 0) {
          reasons.push(
            `${unmapped.length} trainee organization${unmapped.length > 1 ? 's' : ''} not mapped`,
          );
        }
      }
    }
  }

  // ── Degree: universal (applies whenever Long-term is set) ──
  if (result.length_of_training === 'Long-term' && isEmpty(result.degree)) {
    reasons.push('Degree is required when Length of Training is "Long-term"');
  }

  // ── Branch: Individual training ──────────────────────

  if (result.training_type === 'Individual training') {
    if (isEmpty(result.trainee_name)) reasons.push('Trainee Name is required for Individual training');
    if (isEmpty(result.trainee_gender)) reasons.push('Trainee Gender is required for Individual training');
    if (isEmpty(result.trainee_nationality)) reasons.push('Trainee Nationality is required for Individual training');

    if (isEmpty(result.length_of_training)) {
      reasons.push('Length of Training is required for Individual training');
    }

    if (!result.trainee_affiliation) {
      reasons.push('Trainee Affiliation is required for Individual training');
    } else if (!isMappedInstitution(result.trainee_affiliation as RawInstitution)) {
      reasons.push('Trainee Affiliation is not mapped (similarity ≤ 70 or missing institution ID)');
    }
  }

  return { isComplete: reasons.length === 0, reasons };
}
