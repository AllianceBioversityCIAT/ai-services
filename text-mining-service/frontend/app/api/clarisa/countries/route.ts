import { NextResponse } from 'next/server';
import { resolveClarisaApiBase } from '../../../../lib/clarisaApiBase';

export async function GET() {
  const base = resolveClarisaApiBase();
  if (!base) {
    return NextResponse.json({ error: 'CLARISA API base URL is not configured' }, { status: 503 });
  }

  try {
    const response = await fetch(`${base}/countries`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 3600 },
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to load countries catalog' }, { status: response.status });
    }

    const data: unknown = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json({ error: 'Failed to load countries catalog' }, { status: 502 });
  }
}
