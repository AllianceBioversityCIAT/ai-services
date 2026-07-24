interface ValidateClarisaApiKeyOptions {
  apiKey: string;
  microserviceName: string;
  validateUrl: string;
  endpointAccessed: string;
  ipAddress?: string;
}

export interface ValidateClarisaApiKeyResult {
  valid: boolean;
  mis?: string;
  error?: unknown;
}

/** Same contract as validate_with_clarisa() in app/mcp/client.py */
export async function validateClarisaApiKey(
  options: ValidateClarisaApiKeyOptions,
): Promise<ValidateClarisaApiKeyResult> {
  const {
    apiKey,
    microserviceName,
    validateUrl,
    endpointAccessed,
    ipAddress = '0.0.0.0',
  } = options;

  const payload = {
    api_key: apiKey,
    microservice_name: microserviceName,
    endpoint_accessed: endpointAccessed,
    ip_address: ipAddress,
  };

  try {
    const response = await fetch(validateUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.status.toString().startsWith('2')) {
      const error = await response.text().catch(() => null);
      return {
        valid: false,
        error: error ?? `validate-api-key HTTP ${response.status}`,
      };
    }

    const data = (await response.json()) as { valid?: boolean; error?: string; mis?: string };
    if (!data.valid) {
      return { valid: false, error: data.error ?? 'Invalid API Key' };
    }

    return { valid: true, mis: data.mis };
  } catch (error) {
    return { valid: false, error };
  }
}

export function resolveClarisaValidateUrl(): string | null {
  const explicit = process.env.CLARISA_VALIDATE_URL?.trim();
  if (explicit) return explicit;

  const base = process.env.CLARISA_API_BASE_URL ?? process.env.NEXT_PUBLIC_CLARISA_API_BASE_URL;
  if (!base) return null;
  return `${base.replace(/\/$/, '')}/auth/validate-api-key`;
}

/** Registered in CLARISA for partner request API key validation. */
export const PARTNER_REQUEST_MICROSERVICE_NAME = 'AI STAR Bulk Upload - Partner Request';

export function resolvePartnerRequestMicroserviceName(): string {
  return PARTNER_REQUEST_MICROSERVICE_NAME;
}

/** BFF route path — analogous to request.url.path in mining (e.g. /star/mining-bulk-upload/capdev). */
export const PARTNER_REQUEST_BFF_PATH = '/api/partner-request';
