import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
} from "@aws-sdk/lib-dynamodb";
import { env } from "process";

// Initialize DynamoDB client
const client = new DynamoDBClient({
  region: env.AWS_REGION,
  credentials: {
    accessKeyId: env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY || '',
  },
});

export const dynamoDb = DynamoDBDocumentClient.from(client);

// User interface for DynamoDB
export interface User {
  email: string;
  passwordHash: string;
  role: "admin" | "user";
  createdAt: string;
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
    console.error("Error getting user:", error);
    return null;
  }
}

// Create user
export async function createUser(user: User): Promise<boolean> {
  try {
    const command = new PutCommand({
      TableName: env.DYNAMO_DB_USERS_TABLE,
      Item: user,
      ConditionExpression: "attribute_not_exists(email)",
    });
    console.log("🚀 ~ createUser ~ command:", command);

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
