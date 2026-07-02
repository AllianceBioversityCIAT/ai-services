import type { BulkUploadResult, RawInstitution, UnmappedInstitution } from '../types';
import {
  ASSET_IP_OWNER_NAME_TO_ID,
  JSON_FIELDS,
  NON_CAPDEV_FIELDS,
  NUMERIC_FIELDS,
  OPTIONAL_NESTED_OBJECTS,
  OPTIONAL_STRING_FIELDS,
  IP_RIGHTS_DESCRIPTION_FIELDS,
  IP_RIGHTS_YES_NO_FIELDS,
} from '../constants';

// =========================
// Result Extraction
// =========================

/** Unwraps the API response to a normalised { results: [...] } payload. */
export function extractInnerResults(rawResult: unknown): { results: BulkUploadResult[] } {
  if (rawResult && typeof rawResult === 'object') {
    const raw = rawResult as Record<string, unknown>;
    if (raw.results) return raw as { results: BulkUploadResult[] };

    if (raw.content && Array.isArray(raw.content)) {
      for (const item of raw.content as Array<{ text?: string }>) {
        if (item.text) {
          try {
            const parsed = JSON.parse(item.text) as Record<string, unknown>;
            if (parsed && parsed.results) return parsed as { results: BulkUploadResult[] };
          } catch {
            continue;
          }
        }
      }
    }
  }
  return { results: [] };
}

/** Extracts unmapped institutions (similarity < 70) from all results. */
export function extractUnmappedInstitutions(results: BulkUploadResult[]): UnmappedInstitution[] {
  const unmapped: UnmappedInstitution[] = [];
  const seen = new Set<string>();

  const addIfUnmapped = (
    recordId: string,
    title: string,
    sourceField: string,
    institution: RawInstitution,
  ) => {
    const { institution_name, institution_id, similarity_score } = institution;
    if ((institution_id === null && similarity_score === 0) || similarity_score < 70) {
      const key = institution_name.toLowerCase().trim();
      if (!seen.has(key)) {
        seen.add(key);
        unmapped.push({ record_id: recordId, record_title: title, source_field: sourceField, institution_name, institution_id, similarity_score });
      }
    }
  };

  results.forEach((result, idx) => {
    const recordId = `Result ${idx + 1}`;
    const title = result.title ?? 'Unknown Title';

    if (Array.isArray(result.partners)) {
      result.partners.forEach((p) => addIfUnmapped(recordId, title, 'partners', { institution_name: p.institution_name ?? 'Unknown Institution', institution_id: p.institution_id ?? null, similarity_score: p.similarity_score ?? 0 }));
    }

    if (result.trainee_affiliation && typeof result.trainee_affiliation === 'object') {
      const aff = result.trainee_affiliation;
      addIfUnmapped(recordId, title, 'trainee_affiliation', { institution_name: aff.institution_name ?? 'Unknown Affiliation', institution_id: aff.institution_id ?? null, similarity_score: aff.similarity_score ?? 0 });
    }

    if (Array.isArray(result.trainees_description)) {
      result.trainees_description.forEach((t) => addIfUnmapped(recordId, title, 'trainees_description', { institution_name: t.institution_name ?? 'Unknown Institution', institution_id: t.institution_id ?? null, similarity_score: t.similarity_score ?? 0 }));
    }
  });

  return unmapped;
}

// =========================
// STAR Submission Formatter
// =========================

/** Formats a single result according to the STAR CapDev DTO requirements. */
export function formatResultForSTAR(result: BulkUploadResult): Record<string, unknown> {
  const formatted: Record<string, unknown> = { ...result };

  // Step 1: Remove non-CapDev fields
  NON_CAPDEV_FIELDS.forEach((f) => delete formatted[f]);
  delete formatted.batch_number;
  delete formatted.id;

  // Step 2: year → string
  if (formatted.year !== undefined && formatted.year !== null) {
    formatted.year = String(formatted.year);
  }

  // Step 3: numeric fields → numbers
  NUMERIC_FIELDS.forEach((field) => {
    if (formatted[field] !== undefined && formatted[field] !== null && formatted[field] !== '') {
      formatted[field] = Number(formatted[field]);
    }
  });

  // Step 4: regions → array of numbers
  if (formatted.regions) {
    if (typeof formatted.regions === 'string') {
      try {
        formatted.regions = JSON.parse(formatted.regions as string);
      } catch {
        formatted.regions = [];
      }
    }
    if (Array.isArray(formatted.regions)) {
      formatted.regions = (formatted.regions as unknown[]).map((r) => {
        if (typeof r === 'object' && r !== null && 'id' in r) return Number((r as { id: unknown }).id);
        return Number(r);
      }).filter((r) => !isNaN(r as number));
    }
  }

  // Step 5: trainee_affiliation
  if (formatted.trainee_affiliation && typeof formatted.trainee_affiliation === 'object') {
    const aff = formatted.trainee_affiliation as Record<string, unknown>;
    if (aff.similarity_score !== undefined && aff.similarity_score !== null) aff.similarity_score = Number(aff.similarity_score);
    if (aff.institution_id !== undefined && aff.institution_id !== null) aff.institution_id = String(aff.institution_id);
    delete aff.mapped_institution_name;
    delete aff.mapped_institution_acronym;
    if (!aff.institution_name || !aff.similarity_score) delete formatted.trainee_affiliation;
  }

  // Step 6: training_supervisor
  if (formatted.training_supervisor && typeof formatted.training_supervisor === 'object') {
    const sup = formatted.training_supervisor as Record<string, unknown>;
    if (sup.similarity_score !== undefined && sup.similarity_score !== null) sup.similarity_score = Number(sup.similarity_score);
    if (sup.code !== undefined && sup.code !== null) sup.code = String(sup.code);
    delete sup.mapped_name;
    if (!sup.name || !sup.similarity_score) delete formatted.training_supervisor;
  }

  // Step 7: main_contact_person
  if (formatted.main_contact_person && typeof formatted.main_contact_person === 'object') {
    const mcp = formatted.main_contact_person as Record<string, unknown>;
    if (mcp.similarity_score !== undefined && mcp.similarity_score !== null) mcp.similarity_score = Number(mcp.similarity_score);
    if (mcp.code !== undefined && mcp.code !== null) mcp.code = String(mcp.code);
    delete mcp.mapped_name;
    if (!mcp.name || !mcp.similarity_score) delete formatted.main_contact_person;
  }

  // Step 8: language
  if (formatted.language && typeof formatted.language === 'object') {
    const lang = formatted.language as Record<string, unknown>;
    if (lang.name) lang.name = String(lang.name);
    if (lang.code) lang.code = String(lang.code);
    if (!lang.name || !lang.code) delete formatted.language;
  }

  // Step 9: trainee_nationality
  if (formatted.trainee_nationality && typeof formatted.trainee_nationality === 'object') {
    const nat = formatted.trainee_nationality as Record<string, unknown>;
    if (nat.code) nat.code = String(nat.code);
    if (nat.areas) {
      if (Array.isArray(nat.areas)) {
        nat.areas = (nat.areas as unknown[]).map((a) => String(a));
        if ((nat.areas as string[]).length === 0) delete nat.areas;
      } else {
        delete nat.areas;
      }
    }
    if (!nat.code) delete formatted.trainee_nationality;
  }

  // Step 10: parse JSON strings for array/object fields
  JSON_FIELDS.forEach((field) => {
    if (formatted[field] && typeof formatted[field] === 'string') {
      try {
        formatted[field] = JSON.parse(formatted[field] as string);
      } catch {
        formatted[field] = [];
      }
    }
  });

  // Step 11: partners
  if (formatted.partners !== undefined) {
    if (!Array.isArray(formatted.partners) || (formatted.partners as unknown[]).length === 0) {
      delete formatted.partners;
    } else {
      const cleaned = (formatted.partners as Record<string, unknown>[])
        .map((p) => {
          if (typeof p === 'object' && p !== null) {
            const partner = { ...p };
            if (partner.similarity_score !== undefined && partner.similarity_score !== null) partner.similarity_score = Number(partner.similarity_score);
            if (partner.institution_id !== undefined && partner.institution_id !== null) partner.institution_id = String(partner.institution_id);
            delete partner.mapped_institution_name;
            delete partner.mapped_institution_acronym;
            return partner;
          }
          return p;
        })
        .filter((p) => p && typeof p === 'object' && p.institution_name && p.similarity_score !== undefined);
      if (cleaned.length === 0) delete formatted.partners;
      else formatted.partners = cleaned;
    }
  }

  // Step 11.5: trainees_description
  if (formatted.trainees_description !== undefined) {
    if (!Array.isArray(formatted.trainees_description) || (formatted.trainees_description as unknown[]).length === 0) {
      delete formatted.trainees_description;
    } else {
      const cleaned = (formatted.trainees_description as Record<string, unknown>[])
        .map((t) => {
          if (typeof t === 'object' && t !== null) {
            const trainee = { ...t };
            if (trainee.similarity_score !== undefined && trainee.similarity_score !== null) trainee.similarity_score = Number(trainee.similarity_score);
            if (trainee.institution_id !== undefined && trainee.institution_id !== null) trainee.institution_id = String(trainee.institution_id);
            delete trainee.mapped_institution_name;
            delete trainee.mapped_institution_acronym;
            return trainee;
          }
          return t;
        })
        .filter((t) => t && typeof t === 'object' && t.institution_name && t.similarity_score !== undefined);
      if (cleaned.length === 0) delete formatted.trainees_description;
      else formatted.trainees_description = cleaned;
    }
  }

  // Step 12: countries
  if (formatted.countries !== undefined) {
    if (!Array.isArray(formatted.countries) || (formatted.countries as unknown[]).length === 0) {
      delete formatted.countries;
    } else {
      const cleaned = (formatted.countries as Record<string, unknown>[])
        .map((c) => {
          if (typeof c === 'object' && c !== null) {
            const country = { ...c };
            if (country.code) country.code = String(country.code);
            if (country.areas) {
              if (Array.isArray(country.areas)) {
                country.areas = (country.areas as unknown[]).map((a) => String(a));
                if ((country.areas as string[]).length === 0) delete country.areas;
              } else {
                delete country.areas;
              }
            }
            return country;
          }
          return c;
        })
        .filter((c) => c && typeof c === 'object' && c.code);
      if (cleaned.length === 0) delete formatted.countries;
      else formatted.countries = cleaned;
    }
  }

  // Step 13: evidences
  if (formatted.evidences !== undefined) {
    if (!Array.isArray(formatted.evidences) || (formatted.evidences as unknown[]).length === 0) {
      delete formatted.evidences;
    } else {
      const cleaned = (formatted.evidences as Record<string, unknown>[])
        .map((e) => {
          if (typeof e === 'object' && e !== null) {
            const ev = { ...e };
            if (ev.evidence_link) ev.evidence_link = String(ev.evidence_link);
            if (ev.evidence_description) ev.evidence_description = String(ev.evidence_description);
            return ev;
          }
          return e;
        })
        .filter((e) => e && typeof e === 'object' && e.evidence_link && e.evidence_description);
      if (cleaned.length === 0) delete formatted.evidences;
      else formatted.evidences = cleaned;
    }
  }

  // Step 14: keywords
  ['keywords'].forEach((field) => {
    if (formatted[field] !== undefined) {
      if (!Array.isArray(formatted[field]) || (formatted[field] as unknown[]).length === 0) {
        delete formatted[field];
      } else {
        formatted[field] = (formatted[field] as unknown[]).map((item) => String(item));
      }
    }
  });

  // Step 15: regions
  if (formatted.regions !== undefined) {
    if (!Array.isArray(formatted.regions) || (formatted.regions as unknown[]).length === 0) {
      delete formatted.regions;
    }
  }

  // Step 16: IP rights
  if (formatted.asset_ip_owner_id !== undefined && formatted.asset_ip_owner_id !== null && formatted.asset_ip_owner_id !== '') {
    if (typeof formatted.asset_ip_owner_id === 'string') {
      formatted.asset_ip_owner_id = ASSET_IP_OWNER_NAME_TO_ID[formatted.asset_ip_owner_id] ?? Number(formatted.asset_ip_owner_id);
    } else {
      formatted.asset_ip_owner_id = Number(formatted.asset_ip_owner_id);
    }
  } else {
    delete formatted.asset_ip_owner_id;
  }

  IP_RIGHTS_DESCRIPTION_FIELDS.forEach((field) => {
    if (formatted[field] === null || formatted[field] === undefined || formatted[field] === '') {
      delete formatted[field];
    } else if (formatted[field] !== undefined) {
      formatted[field] = String(formatted[field]);
    }
  });

  IP_RIGHTS_YES_NO_FIELDS.forEach((field) => {
    if (formatted[field] === null || formatted[field] === undefined || formatted[field] === '') {
      delete formatted[field];
    } else if (formatted[field] !== undefined) {
      formatted[field] = String(formatted[field]);
    }
  });

  // Step 17: optional string fields
  OPTIONAL_STRING_FIELDS.forEach((field) => {
    const val = formatted[field];
    if (val === null || val === undefined || val === '' || String(val) === 'undefined' || String(val) === 'null') {
      delete formatted[field];
    } else if (val !== undefined) {
      formatted[field] = String(val);
    }
  });

  // Step 17.5: strip "Other: " prefix from training_purpose before sending
  if (typeof formatted.training_purpose === 'string' && formatted.training_purpose.startsWith('Other: ')) {
    formatted.training_purpose = formatted.training_purpose.slice(7);
  }

  // Step 18: optional numeric fields
  NUMERIC_FIELDS.forEach((field) => {
    if (formatted[field] === null || formatted[field] === undefined) {
      delete formatted[field];
    }
  });

  // Step 19: optional nested objects when empty
  OPTIONAL_NESTED_OBJECTS.forEach((field) => {
    const val = formatted[field];
    if (val === null || val === undefined || (typeof val === 'object' && Object.keys(val as object).length === 0)) {
      delete formatted[field];
    }
  });

  return formatted;
}
