import { NextRequest, NextResponse } from "next/server";
import { createUser } from "@/lib/dynamo";
import { getSessionFromRequest } from "@/lib/auth";
import { User } from "@/lib/dynamo";

export async function POST(req: NextRequest) {
  const sessionUser = await getSessionFromRequest(req);
  if (!sessionUser || sessionUser.role !== "admin") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 403 });
  }

  const { email, passwordHash, role } = await req.json();
  if (!email || !passwordHash || !["admin", "user"].includes(role)) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }

  const newUser: User = {
    email,
    passwordHash,
    role,
    createdAt: new Date().toISOString(),
  };

  try {
    const success = await createUser(newUser);
    if (!success) {
      return NextResponse.json(
        { error: "User already exists" },
        { status: 409 }
      );
    }
    return NextResponse.json({ message: "User created" }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
