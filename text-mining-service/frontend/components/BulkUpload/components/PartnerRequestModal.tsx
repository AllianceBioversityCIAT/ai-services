'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { PartnerRequestFormRow, UnmappedInstitution } from '../types';
import { useClarisaCatalogs } from '../hooks/useClarisaCatalogs';
import {
  buildPartnerRequestPayload,
  buildPartnerRequestRows,
  isPartnerRequestAuthError,
  isPartnerRequestRowValid,
  PARTNER_REQUEST_AUTH_ERROR,
  PARTNER_REQUEST_SERVICE_ERROR,
} from '../utils/partnerRequestUtils';

interface PartnerRequestModalProps {
  open: boolean;
  institutions: UnmappedInstitution[];
  authToken: string | null;
  userEmail: string | null;
  starUserId: string | null;
  userFullName: string | null;
  onClose: () => void;
}

export function PartnerRequestModal({
  open,
  institutions,
  authToken,
  userEmail,
  starUserId,
  userFullName,
  onClose,
}: PartnerRequestModalProps) {
  const { countries, institutionTypes, loading, error: catalogError, reload } = useClarisaCatalogs(open);
  const [rows, setRows] = useState<PartnerRequestFormRow[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showValidation, setShowValidation] = useState(false);

  useEffect(() => {
    if (!open) return;
    setRows(buildPartnerRequestRows(institutions));
    setGlobalError(null);
    setSuccessMessage(null);
    setShowValidation(false);
    setSubmitting(false);
  }, [open, institutions]);

  const invalidCount = useMemo(
    () => rows.filter((row) => !isPartnerRequestRowValid(row)).length,
    [rows],
  );

  const updateRow = useCallback((rowKey: string, patch: Partial<PartnerRequestFormRow>) => {
    setRows((prev) => prev.map((row) => (row.rowKey === rowKey ? { ...row, ...patch } : row)));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!authToken) {
      setGlobalError(PARTNER_REQUEST_AUTH_ERROR);
      return;
    }
    if (!userEmail || !userFullName || !starUserId) {
      setGlobalError(PARTNER_REQUEST_AUTH_ERROR);
      return;
    }
    if (rows.length === 0) {
      setGlobalError(PARTNER_REQUEST_SERVICE_ERROR);
      return;
    }

    setShowValidation(true);
    if (invalidCount > 0) {
      setGlobalError('Complete all required fields (Partner name, Type, Headquarter country) for each row.');
      return;
    }

    setGlobalError(null);
    setSuccessMessage(null);
    setSubmitting(true);

    let submittedCount = 0;
    for (const row of rows) {
      try {
        const response = await fetch('/api/partner-request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            payload: buildPartnerRequestPayload(row, userEmail, userFullName, starUserId),
          }),
        });

        const responseText = await response.text();
        let data: {
          error?: string;
          httpStatus?: number;
          clarisaError?: unknown;
          detail?: string;
        } = {};
        try {
          data = responseText ? JSON.parse(responseText) as typeof data : {};
        } catch {
          data = { detail: responseText.slice(0, 500) };
        }

        if (!response.ok) {
          const logPayload = {
            partnerName: row.name,
            responseStatus: response.status,
            errorType: data.error ?? 'unknown',
            httpStatus: data.httpStatus ?? response.status,
            detail: data.detail ?? null,
            clarisaError: data.clarisaError ?? null,
            rawBody: responseText.slice(0, 500),
          };
          console.error(
            `[partner-request] submit failed (HTTP ${response.status}): ${JSON.stringify(logPayload)}`,
          );

          setGlobalError(
            isPartnerRequestAuthError(response.status, data.error)
              ? PARTNER_REQUEST_AUTH_ERROR
              : PARTNER_REQUEST_SERVICE_ERROR,
          );
          setSubmitting(false);
          return;
        }

        submittedCount += 1;
      } catch (err) {
        console.error('[partner-request] submit failed (network or parse error)', {
          partnerName: row.name,
          error: err,
        });
        setGlobalError(PARTNER_REQUEST_SERVICE_ERROR);
        setSubmitting(false);
        return;
      }
    }

    setSuccessMessage(
      `${submittedCount} partner request${submittedCount !== 1 ? 's' : ''} submitted successfully.`,
    );
    setSubmitting(false);
  }, [authToken, invalidCount, rows, starUserId, userEmail, userFullName]);

  if (!open) return null;

  return (
    <div className="bulk-confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="partner-request-title">
      <div className="bulk-partner-request-modal">
        <div className="bulk-partner-request-header">
          <h3 id="partner-request-title" className="bulk-partner-request-title">Partners Request</h3>
          <button className="bulk-partner-request-close" type="button" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="bulk-info-banner bulk-partner-request-info-banner">
          <div className="bulk-info-icon">i</div>
          <div className="bulk-info-text">
            Please note that once your partner request is approved (the partner review process may take up to 2 business days), it could take up to an hour to be available in the CLARISA institutions list. Make sure that you are requesting to add a legal entity.
          </div>
        </div>

        {catalogError && (
          <div className="bulk-partner-request-alert bulk-partner-request-alert-error">
            <span>{PARTNER_REQUEST_SERVICE_ERROR}</span>
            <button type="button" className="bulk-partner-request-link-btn" onClick={reload}>
              Retry
            </button>
          </div>
        )}

        {globalError && (
          <div className="bulk-partner-request-alert bulk-partner-request-alert-error">
            {globalError}
          </div>
        )}

        {successMessage && (
          <div className="bulk-partner-request-alert bulk-partner-request-alert-success">
            {successMessage}
          </div>
        )}

        {loading ? (
          <div className="bulk-partner-request-loading">Loading CLARISA catalogs…</div>
        ) : rows.length === 0 ? (
          <div className="bulk-partner-request-empty">No unmapped partners found for this file.</div>
        ) : (
          <div className="bulk-partner-request-table-wrap">
            <table className="bulk-partner-request-table">
              <thead>
                <tr>
                  <th>Partner name <span className="bulk-required-asterisk">*</span></th>
                  <th>Acronym</th>
                  <th>Type <span className="bulk-required-asterisk">*</span></th>
                  <th>Headquarter country <span className="bulk-required-asterisk">*</span></th>
                  <th>Website</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const invalid = showValidation && !isPartnerRequestRowValid(row);
                  return (
                    <tr key={row.rowKey} className={invalid ? 'bulk-partner-request-row-invalid' : undefined}>
                      <td>
                        <input
                          type="text"
                          className="bulk-partner-request-input"
                          value={row.name}
                          onChange={(e) => updateRow(row.rowKey, { name: e.target.value })}
                          disabled={submitting}
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          className="bulk-partner-request-input"
                          value={row.acronym}
                          onChange={(e) => updateRow(row.rowKey, { acronym: e.target.value })}
                          disabled={submitting}
                        />
                      </td>
                      <td>
                        <select
                          className="bulk-partner-request-select"
                          value={row.institutionTypeCode ?? ''}
                          onChange={(e) => updateRow(row.rowKey, {
                            institutionTypeCode: e.target.value ? Number(e.target.value) : null,
                          })}
                          disabled={submitting || !!catalogError}
                        >
                          <option value="">Select type</option>
                          {institutionTypes.map((type) => (
                            <option key={type.code} value={type.code}>
                              {type.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select
                          className="bulk-partner-request-select"
                          value={row.hqCountryIso}
                          onChange={(e) => updateRow(row.rowKey, { hqCountryIso: e.target.value })}
                          disabled={submitting || !!catalogError}
                        >
                          <option value="">Select country</option>
                          {countries.map((country) => (
                            <option key={country.isoAlpha2} value={country.isoAlpha2}>
                              {country.name}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          type="text"
                          className="bulk-partner-request-input"
                          value={row.website}
                          placeholder="https://"
                          onChange={(e) => updateRow(row.rowKey, { website: e.target.value })}
                          disabled={submitting}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="bulk-partner-request-actions">
          <button className="bulk-confirm-btn-cancel" type="button" onClick={onClose} disabled={submitting}>
            Close
          </button>
          <button
            className="bulk-confirm-btn-submit"
            type="button"
            onClick={handleSubmit}
            disabled={submitting || loading || !!catalogError || rows.length === 0}
          >
            {submitting ? 'Submitting…' : 'Submit partner requests'}
          </button>
        </div>
      </div>
    </div>
  );
}
