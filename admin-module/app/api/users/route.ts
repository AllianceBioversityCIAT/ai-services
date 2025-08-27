import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listUsers, createUser } from "@/lib/database/users";
import { hashPassword } from "@/lib/auth";

export async function GET() {
  try {
    const session = await getSession();
    console.log("🚀 ~ GET ~ session:", session)
    if (!session || session.role !== "admin") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const users = await listUsers();

    const safeUsers = users.map((user) => {
      const { passwordHash, ...safeUser } = user;
      return safeUser;
    });

    return NextResponse.json({ users: safeUsers });
  } catch (error) {
    console.error("Error listing users:", error);
    return NextResponse.json(
      { error: "Failed to list users" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSession();
    if (!session || session.role !== "admin") {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const { email, passwordHash, role } = body;

    if (!email || !passwordHash || !role) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    if (!["admin", "user"].includes(role)) {
      return NextResponse.json({ error: "Invalid role" }, { status: 400 });
    }

    const hashedPassword = await hashPassword(passwordHash);

    const user = {
      email,
      passwordHash: hashedPassword,
      role,
      createdAt: new Date().toISOString(),
    };

    const success = await createUser(user);
    if (!success) {
      return NextResponse.json(
        { error: "User already exists" },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { message: "User created successfully" },
      { status: 201 }
    );
  } catch (error) {
    console.error("Error creating user:", error);
    return NextResponse.json(
      { error: "Failed to create user" },
      { status: 500 }
    );
  }
}
