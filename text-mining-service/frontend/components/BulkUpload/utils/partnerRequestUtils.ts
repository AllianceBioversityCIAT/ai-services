import { PARTNER_REQUEST_MIS_ACRONYM } from '../constants';
import type { PartnerRequestCreatePayload, PartnerRequestFormRow, UnmappedInstitution } from '../types';

export const PARTNER_REQUEST_AUTH_ERROR =
  'This user does not have the required permissions to submit a partner request.';

export const PARTNER_REQUEST_SERVICE_ERROR =
  'The service is not available at this moment. Please try again later or contact the person in charge to request the partner manually.';

export function isPartnerRequestAuthError(status: number, errorType?: string): boolean {
  return errorType === 'auth' || status === 401 || status === 403;
}

export function buildPartnerRequestRows(institutions: UnmappedInstitution[]): PartnerRequestFormRow[] {
  const seen = new Set<string>();
  const rows: PartnerRequestFormRow[] = [];

  for (const inst of institutions) {
    const name = inst.institution_name.trim();
    const key = name.toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    rows.push({
      rowKey: key,
      name,
      acronym: '',
      institutionTypeCode: null,
      hqCountryIso: '',
      website: '',
    });
  }

  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

export function isPartnerRequestRowValid(row: PartnerRequestFormRow): boolean {
  return (
    row.name.trim().length > 0
    && row.institutionTypeCode != null
    && row.hqCountryIso.trim().length > 0
  );
}

export function buildPartnerRequestPayload(
  row: PartnerRequestFormRow,
  externalUserMail: string,
  externalUserName: string,
): PartnerRequestCreatePayload {
  return {
    name: row.name.trim(),
    acronym: row.acronym.trim(),
    websiteLink: row.website.trim(),
    hqCountryIso: row.hqCountryIso,
    institutionTypeCode: row.institutionTypeCode as number,
    externalUserMail,
    externalUserName,
    externalUserComments: '',
    misAcronym: PARTNER_REQUEST_MIS_ACRONYM,
  };
}
