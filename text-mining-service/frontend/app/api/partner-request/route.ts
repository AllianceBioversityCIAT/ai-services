import { NextRequest, NextResponse } from 'next/server';
import type { PartnerRequestCreatePayload } from '../../../components/BulkUpload/types';
import {
  PARTNER_REQUEST_BFF_PATH,
  resolveClarisaValidateUrl,
  resolvePartnerRequestMicroserviceName,
  validateClarisaApiKey,
} from '../../../lib/clarisaApiKeyAuth';

const CLARISA_API_KEY = process.env.CLARISA_API_KEY ?? '';

const PARTNER_REQUEST_MICROSERVICE_NAME = resolvePartnerRequestMicroserviceName();

function resolveCreateUrl(): string | null {
  const explicit = process.env.CLARISA_PARTNER_REQUEST_CREATE_URL;
  if (explicit) return explicit;

  const base = process.env.CLARISA_API_BASE_URL ?? process.env.NEXT_PUBLIC_CLARISA_API_BASE_URL;
  if (!base) return null;
  return `${base.replace(/\/$/, '')}/partner-requests/create`;
}

function errorTypeForStatus(status: number): 'auth' | 'service' {
  return status === 401 || status === 403 ? 'auth' : 'service';
}

async function readClarisaErrorBody(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => '');
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function POST(request: NextRequest) {
  const createUrl = resolveCreateUrl();
  const validateUrl = resolveClarisaValidateUrl();

  if (!createUrl || !CLARISA_API_KEY || !validateUrl) {
    console.error('[partner-request] misconfigured', {
      hasCreateUrl: Boolean(createUrl),
      hasApiKey: Boolean(CLARISA_API_KEY),
      hasValidateUrl: Boolean(validateUrl),
    });
    return NextResponse.json(
      { error: 'service', detail: 'Partner request API is not configured on the server' },
      { status: 503 },
    );
  }

  let payload: PartnerRequestCreatePayload;
  try {
    const body = (await request.json()) as { payload?: PartnerRequestCreatePayload };
    payload = body.payload as PartnerRequestCreatePayload;
  } catch {
    return NextResponse.json({ error: 'service', detail: 'Invalid request body' }, { status: 400 });
  }

  if (!payload?.name?.trim() || !payload.hqCountryIso || payload.institutionTypeCode == null || payload.userId == null) {
    return NextResponse.json({ error: 'service', detail: 'Missing required partner fields' }, { status: 400 });
  }

  const clientIp = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    ?? request.headers.get('x-real-ip')
    ?? '0.0.0.0';

  const keyValidation = await validateClarisaApiKey({
    apiKey: CLARISA_API_KEY,
    microserviceName: PARTNER_REQUEST_MICROSERVICE_NAME,
    validateUrl,
    endpointAccessed: PARTNER_REQUEST_BFF_PATH,
    ipAddress: clientIp,
  });

  if (!keyValidation.valid) {
    console.error('[partner-request] CLARISA API key validation failed', {
      microserviceName: PARTNER_REQUEST_MICROSERVICE_NAME,
      endpointAccessed: PARTNER_REQUEST_BFF_PATH,
      validateUrl,
      clarisaError: keyValidation.error,
    });

    return NextResponse.json(
      {
        error: 'auth',
        httpStatus: 401,
        clarisaError: keyValidation.error,
        detail: 'CLARISA API key validation failed',
      },
      { status: 401 },
    );
  }

  try {
    console.log('[partner-request] CLARISA create request', {
      createUrl,
      partnerName: payload.name,
      auth: 'X-API-Key',
      microserviceName: PARTNER_REQUEST_MICROSERVICE_NAME,
      endpointAccessed: PARTNER_REQUEST_BFF_PATH,
      mis: keyValidation.mis ?? null,
    });

    const response = await fetch(createUrl, {
      method: 'POST',
      headers: {
        'X-API-Key': CLARISA_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const clarisaError = await readClarisaErrorBody(response);
      const errorType = errorTypeForStatus(response.status);

      console.error('[partner-request] CLARISA create failed', {
        errorType,
        httpStatus: response.status,
        createUrl,
        partnerName: payload.name,
        microserviceName: PARTNER_REQUEST_MICROSERVICE_NAME,
        clarisaError,
      });

      return NextResponse.json(
        {
          error: errorType,
          httpStatus: response.status,
          clarisaError,
          detail: `CLARISA create returned HTTP ${response.status}`,
        },
        { status: response.status },
      );
    }

    const data: unknown = await response.json().catch(() => null);
    return NextResponse.json({ ok: true, data }, { status: 200 });
  } catch (error) {
    console.error('[partner-request] CLARISA create network error', error);
    return NextResponse.json(
      { error: 'service', detail: 'Could not reach CLARISA partner request API' },
      { status: 502 },
    );
  }
}
