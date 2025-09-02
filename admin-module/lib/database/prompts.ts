import {
  GetCommand,
  PutCommand,
  QueryCommand,
  DeleteCommand,
  UpdateCommand,
  ScanCommand,
} from "@aws-sdk/lib-dynamodb";
import { dynamoDb } from "./client";
import { env } from "process";

// Prompt interface for DynamoDB
export interface Prompt {
  project_id: string;
  version: string;
  prompt_text: string;
  is_stable: boolean;
  created_at: string;
  created_by?: string;
  description?: string;
  parameters?: Record<string, any>;
}

// Access control for prompts per project
export type PromptAccessRole = "editor" | "viewer";
export interface PromptAccess {
  project_id: string;
  user_email: string;
  role: PromptAccessRole;
  created_at: string;
}

// Create prompt version
export async function createPromptVersion(
  prompt: Omit<Prompt, "created_at">
): Promise<any> {
  try {
    const created_at = new Date().toISOString();
    const item = {
      PK: `PROMPT#${prompt.project_id}`,
      SK: `VERSION#${created_at}`,
      entity_type: "PROMPT",
      project_id: prompt.project_id,
      version: prompt.version,
      prompt_text: prompt.prompt_text,
      is_stable: prompt.is_stable || false,
      created_at,
      created_by: prompt.created_by || "system",
      description: prompt.description || "",
      parameters: prompt.parameters || {},
    };

    const command = new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Item: item,
    });

    await dynamoDb.send(command);
    return item;
  } catch (error) {
    console.error("Error creating prompt version:", error);
    throw error;
  }
}

// Get all prompt versions for a project
export async function getPromptVersions(projectId: string): Promise<any[]> {
  try {
    const command = new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      KeyConditionExpression: "PK = :pk",
      ExpressionAttributeValues: {
        ":pk": `PROMPT#${projectId}`,
      },
      ScanIndexForward: false, // Most recent first
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error getting prompt versions:", error);
    return [];
  }
}

// Get latest stable prompt (LTS)
export async function getPromptLTS(projectId: string): Promise<any | null> {
  try {
    const command = new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      KeyConditionExpression: "PK = :pk",
      FilterExpression: "is_stable = :stable",
      ExpressionAttributeValues: {
        ":pk": `PROMPT#${projectId}`,
        ":stable": true,
      },
      ScanIndexForward: false, // Most recent first
      Limit: 1,
    });

    const result = await dynamoDb.send(command);
    return result.Items?.[0] || null;
  } catch (error) {
    console.error("Error getting prompt LTS:", error);
    return null;
  }
}

// Get latest prompt version (stable or not)
export async function getLatestPrompt(projectId: string): Promise<any | null> {
  try {
    const command = new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      KeyConditionExpression: "PK = :pk",
      ExpressionAttributeValues: {
        ":pk": `PROMPT#${projectId}`,
      },
      ScanIndexForward: false, // Most recent first
      Limit: 1,
    });

    const result = await dynamoDb.send(command);
    return result.Items?.[0] || null;
  } catch (error) {
    console.error("Error getting latest prompt:", error);
    return null;
  }
}

// Get specific prompt version
export async function getPromptVersion(
  projectId: string,
  createdAt: string
): Promise<any | null> {
  try {
    const command = new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROMPT#${projectId}`,
        SK: `VERSION#${createdAt}`,
      },
    });

    const result = await dynamoDb.send(command);
    return result.Item || null;
  } catch (error) {
    console.error("Error getting prompt version:", error);
    return null;
  }
}

// Update prompt version (mark as stable, update description, etc.)
export async function updatePromptVersion(
  projectId: string,
  createdAt: string,
  updates: Partial<Prompt>
): Promise<boolean> {
  try {
    const updateExpr = Object.keys(updates)
      .map((k) => `#${k} = :${k}`)
      .join(", ");

    const exprAttrNames = Object.fromEntries(
      Object.keys(updates).map((k) => [`#${k}`, k])
    );

    const exprAttrValues = Object.fromEntries(
      Object.keys(updates).map((k) => [`:${k}`, updates[k as keyof Prompt]])
    );

    const command = new UpdateCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROMPT#${projectId}`,
        SK: `VERSION#${createdAt}`,
      },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error updating prompt version:", error);
    return false;
  }
}

// Delete prompt version
export async function deletePromptVersion(
  projectId: string,
  createdAt: string
): Promise<boolean> {
  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROMPT#${projectId}`,
        SK: `VERSION#${createdAt}`,
      },
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error deleting prompt version:", error);
    return false;
  }
}

// --- Prompt Access Control helpers ---

// Grant access to a user for a project's prompts
export async function grantPromptAccess(
  projectId: string,
  userEmail: string,
  role: PromptAccessRole = "editor"
): Promise<boolean> {
  try {
    const item = {
      PK: `PROMPT#${projectId}`,
      SK: `ACCESS#${userEmail}`,
      entity_type: "PROMPT_ACCESS",
      project_id: projectId,
      user_email: userEmail,
      role,
      created_at: new Date().toISOString(),
    };

    const command = new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Item: item,
    });
    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error granting prompt access:", error);
    return false;
  }
}

// Revoke access for a user
export async function revokePromptAccess(
  projectId: string,
  userEmail: string
): Promise<boolean> {
  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: { PK: `PROMPT#${projectId}`, SK: `ACCESS#${userEmail}` },
    });
    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error revoking prompt access:", error);
    return false;
  }
}

// Get access entry for a user on a project (if any)
export async function getPromptAccessForUser(
  projectId: string,
  userEmail: string
): Promise<PromptAccess | null> {
  try {
    const command = new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: { PK: `PROMPT#${projectId}`, SK: `ACCESS#${userEmail}` },
    });
    const result = await dynamoDb.send(command);
    const item = result.Item;
    if (!item) return null;
    return {
      project_id: item.project_id,
      user_email: item.user_email,
      role: item.role,
      created_at: item.created_at,
    } as PromptAccess;
  } catch (error) {
    console.error("Error getting prompt access for user:", error);
    return null;
  }
}

// List users with access to a project
export async function listPromptAccessUsers(
  projectId: string
): Promise<PromptAccess[]> {
  try {
    const command = new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :sk)",
      ExpressionAttributeValues: {
        ":pk": `PROMPT#${projectId}`,
        ":sk": "ACCESS#",
      },
    });
    const result = await dynamoDb.send(command);
    return (result.Items || []).map((item: any) => ({
      project_id: item.project_id,
      user_email: item.user_email,
      role: item.role,
      created_at: item.created_at,
    }));
  } catch (error) {
    console.error("Error listing prompt access users:", error);
    return [];
  }
}

// List project IDs a user has any access to
export async function listProjectIdsForUserAccess(
  userEmail: string
): Promise<string[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type AND user_email = :email",
      ExpressionAttributeValues: {
        ":type": "PROMPT_ACCESS",
        ":email": userEmail,
      },
    });
    const result = await dynamoDb.send(command);
    const items = result.Items || [];
    const ids = Array.from(new Set(items.map((i: any) => i.project_id)));
    return ids;
  } catch (error) {
    console.error("Error listing projects for user access:", error);
    return [];
  }
}

// Mark prompt as stable (and optionally unmark others)
export async function markPromptAsStable(
  projectId: string,
  createdAt: string,
  unmarkOthers: boolean = true
): Promise<boolean> {
  try {
    // If unmarkOthers is true, first unmark all other stable prompts
    if (unmarkOthers) {
      const stablePrompts = await getStablePrompts(projectId);
      for (const prompt of stablePrompts) {
        if (prompt.SK !== `VERSION#${createdAt}`) {
          await updatePromptVersion(projectId, prompt.created_at, {
            is_stable: false,
          });
        }
      }
    }

    // Mark the specified prompt as stable
    return await updatePromptVersion(projectId, createdAt, { is_stable: true });
  } catch (error) {
    console.error("Error marking prompt as stable:", error);
    return false;
  }
}

// Get all stable prompts for a project
export async function getStablePrompts(projectId: string): Promise<any[]> {
  try {
    const command = new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      KeyConditionExpression: "PK = :pk",
      FilterExpression: "is_stable = :stable",
      ExpressionAttributeValues: {
        ":pk": `PROMPT#${projectId}`,
        ":stable": true,
      },
      ScanIndexForward: false, // Most recent first
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error getting stable prompts:", error);
    return [];
  }
}

// Get prompt statistics for a project
export async function getPromptStats(projectId: string): Promise<{
  total: number;
  stable: number;
  unstable: number;
  latest_version: string | null;
  latest_stable_version: string | null;
}> {
  try {
    const [allPrompts, latestPrompt, latestStable] = await Promise.all([
      getPromptVersions(projectId),
      getLatestPrompt(projectId),
      getPromptLTS(projectId),
    ]);

    const stableCount = allPrompts.filter((p) => p.is_stable).length;

    return {
      total: allPrompts.length,
      stable: stableCount,
      unstable: allPrompts.length - stableCount,
      latest_version: latestPrompt?.version || null,
      latest_stable_version: latestStable?.version || null,
    };
  } catch (error) {
    console.error("Error getting prompt stats:", error);
    return {
      total: 0,
      stable: 0,
      unstable: 0,
      latest_version: null,
      latest_stable_version: null,
    };
  }
}

// Clone prompt version (create new version based on existing one)
export async function clonePromptVersion(
  projectId: string,
  sourceCreatedAt: string,
  newVersion: string,
  updates?: Partial<Prompt>
): Promise<any> {
  try {
    const sourcePrompt = await getPromptVersion(projectId, sourceCreatedAt);
    if (!sourcePrompt) {
      throw new Error("Source prompt not found");
    }

    const newPrompt: Omit<Prompt, "created_at"> = {
      project_id: projectId,
      version: newVersion,
      prompt_text: sourcePrompt.prompt_text,
      is_stable: false, // New clones are never stable by default
      created_by: updates?.created_by || "system",
      description:
        updates?.description || `Cloned from version ${sourcePrompt.version}`,
      parameters: { ...sourcePrompt.parameters, ...updates?.parameters },
      ...updates,
    };

    return await createPromptVersion(newPrompt);
  } catch (error) {
    console.error("Error cloning prompt version:", error);
    throw error;
  }
}
