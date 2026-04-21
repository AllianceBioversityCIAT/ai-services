import { NextRequest, NextResponse } from 'next/server';

const ALLOWED_ROLES = [1, 9, 10];

export async function POST(request: NextRequest) {
  let token: string;
  try {
    const body = (await request.json()) as { token?: string };
    token = body.token ?? '';
  } catch {
    return NextResponse.json({ valid: false, error: 'Invalid request body' }, { status: 400 });
  }

  if (!token) {
    return NextResponse.json({ valid: false, error: 'No token provided' }, { status: 400 });
  }

  const managementApiBaseUrl =
    process.env.MANAGEMENT_API_BASE_URL ?? process.env.NEXT_PUBLIC_MANAGEMENT_API_BASE_URL;
  if (!managementApiBaseUrl) {
    return NextResponse.json({ valid: false, error: 'Server configuration error' }, { status: 500 });
  }

  try {
    const response = await fetch(`${managementApiBaseUrl}/authorization/validate-token`, {
      method: 'PATCH',
      headers: {
        'access-token': token,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json({ valid: false, error: 'Token validation failed' }, { status: 401 });
    }

    const data = (await response.json()) as {
      data?: { isValid?: boolean; user?: { roles?: number[] } };
    };

    const isValid = data?.data?.isValid === true;
    const roles: number[] = data?.data?.user?.roles ?? [];
    const hasAllowedRole = roles.some((r) => ALLOWED_ROLES.includes(r));

    if (!isValid || !hasAllowedRole) {
      return NextResponse.json(
        { valid: false, error: 'Unauthorized: invalid token or insufficient permissions' },
        { status: 401 },
      );
    }

    return NextResponse.json({ valid: true });
  } catch {
    return NextResponse.json({ valid: false, error: 'Token validation error' }, { status: 500 });
  }
}
