import { NextRequest, NextResponse } from 'next/server';
import type { PartnerRequestCreatePayload } from '../../../components/BulkUpload/types';

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

export async function POST(request: NextRequest) {
  const createUrl = resolveCreateUrl();
  if (!createUrl) {
    return NextResponse.json({ error: 'service' }, { status: 503 });
  }

  let token = '';
  let payload: PartnerRequestCreatePayload;
  try {
    const body = (await request.json()) as { token?: string; payload?: PartnerRequestCreatePayload };
    token = body.token ?? '';
    payload = body.payload as PartnerRequestCreatePayload;
  } catch {
    return NextResponse.json({ error: 'service' }, { status: 400 });
  }

  if (!token) {
    return NextResponse.json({ error: 'auth' }, { status: 401 });
  }

  if (!payload?.name?.trim() || !payload.hqCountryIso || payload.institutionTypeCode == null) {
    return NextResponse.json({ error: 'service' }, { status: 400 });
  }

  try {
    const response = await fetch(createUrl, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      return NextResponse.json({ error: errorTypeForStatus(response.status) }, { status: response.status });
    }

    const data: unknown = await response.json().catch(() => null);
    return NextResponse.json({ ok: true, data }, { status: 200 });
  } catch {
    return NextResponse.json({ error: 'service' }, { status: 502 });
  }
}
