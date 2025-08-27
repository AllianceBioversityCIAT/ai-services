import {
  GetCommand,
  PutCommand,
  ScanCommand,
  DeleteCommand,
  UpdateCommand,
} from "@aws-sdk/lib-dynamodb";
import { dynamoDb } from "./client";
import { env } from "process";

// User interface for DynamoDB
export interface User {
  email: string;
  passwordHash: string;
  role: "admin" | "user";
  createdAt: string;
}

// Normalize user data from DynamoDB response
function normalizeUser(item: any): User {
  return {
    email: item.email,
    passwordHash: item.passwordHash,
    role: item.role,
    createdAt: item.createdAt,
  };
}

// Get user by email
export async function getUserByEmail(email: string): Promise<User | null> {
  try {
    const command = new GetCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE!,
      Key: { email },
    });

    const result = await dynamoDb.send(command);
    return result.Item as User | null;
  } catch (error) {
    console.error("Error getting user by email:", error);
    return null;
  }
}

// Create user
export async function createUser(user: User): Promise<boolean> {
  try {
    const command = new PutCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE!,
      Item: user,
      ConditionExpression: "attribute_not_exists(email)",
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    if ((error as any).name === "ConditionalCheckFailedException") {
      return false; // User already exists
    }
    console.error("Error creating user:", error);
    throw error;
  }
}

// List all users
export async function listUsers(): Promise<User[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE!,
    });
    const result = await dynamoDb.send(command);
    return (result.Items || []).map(normalizeUser);
  } catch (error) {
    console.error("Error listing users:", error);
    return [];
  }
}

// Delete user by email
export async function deleteUser(email: string): Promise<boolean> {
  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE!,
      Key: { email },
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error deleting user:", error);
    return false;
  }
}

// Update user (optional, if needed later)
export async function updateUser(
  email: string,
  updates: Partial<Omit<User, "email">>
): Promise<boolean> {
  try {
    const updateExpr = Object.keys(updates)
      .map((k) => `#${k} = :${k}`)
      .join(", ");

    const exprAttrNames = Object.fromEntries(
      Object.keys(updates).map((k) => [`#${k}`, k])
    );

    const exprAttrValues = Object.fromEntries(
      Object.keys(updates).map((k) => [
        `:${k}`,
        updates[k as keyof Omit<User, "email">],
      ])
    );

    const command = new UpdateCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE!,
      Key: { email },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error updating user:", error);
    return false;
  }
}
