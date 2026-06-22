import { NextRequest, NextResponse } from 'next/server';

const MINING_API_BASE_URL =
  process.env.MINING_API_BASE_URL ?? process.env.NEXT_PUBLIC_MINING_API_BASE_URL;
const BULK_UPLOAD_API_KEY = process.env.BULK_UPLOAD_API_KEY ?? '';

export async function POST(request: NextRequest) {
  if (!MINING_API_BASE_URL) {
    return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
  }

  const formData = await request.formData();

  const response = await fetch(`${MINING_API_BASE_URL}/star/mining-bulk-upload/capdev`, {
    method: 'POST',
    headers: { 'X-API-Key': BULK_UPLOAD_API_KEY },
    body: formData,
  });

  const data: unknown = await response.json().catch(() => ({ error: 'Invalid response from upstream' }));
  return NextResponse.json(data, { status: response.status });
}
