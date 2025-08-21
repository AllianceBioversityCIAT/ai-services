import { NextRequest, NextResponse } from "next/server";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DeleteCommand } from "@aws-sdk/lib-dynamodb";
import { env } from "process";
import { getSessionFromRequest } from "@/lib/auth";

const client = new DynamoDBClient({
  region: env.AWS_REGION,
  credentials: {
    accessKeyId: env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY || '',
  },
});

export async function POST(req: NextRequest) {
  const sessionUser = await getSessionFromRequest(req);
  if (!sessionUser || sessionUser.role !== "admin") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 403 });
  }

  const { email } = await req.json();
  if (!email || email === sessionUser.email) {
    return NextResponse.json({ error: "Invalid operation" }, { status: 400 });
  }

  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE,
      Key: { email },
    });
    await client.send(command);
    return NextResponse.json({ message: "User deleted" });
  } catch (error) {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
