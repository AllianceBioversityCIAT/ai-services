import {
  GetCommand,
  PutCommand,
  ScanCommand,
  DeleteCommand,
  UpdateCommand,
} from "@aws-sdk/lib-dynamodb";
import { dynamoDb } from "./client";
import { env } from "process";
import { v4 as uuidv4 } from "uuid";

// Project interface for DynamoDB
export interface Project {
  id: string;
  name: string;
  description: string;
  product_id: string;
  status: "active" | "inactive";
  created_at: string;
}

// Create project
export async function createProject(
  project: Omit<Project, "id" | "created_at">
): Promise<any> {
  try {
    const id = uuidv4();
    const item = {
      PK: `PROJECT#${id}`,
      SK: "METADATA",
      entity_type: "PROJECT",
      id,
      name: project.name,
      description: project.description,
      product_id: project.product_id,
      status: project.status || "active",
      created_at: new Date().toISOString(),
    };

    const command = new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    });

    await dynamoDb.send(command);
    return item;
  } catch (error) {
    console.error("Error creating project:", error);
    throw error;
  }
}

// Get project by ID
export async function getProject(projectId: string): Promise<any | null> {
  try {
    const command = new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROJECT#${projectId}`,
        SK: "METADATA",
      },
    });

    const result = await dynamoDb.send(command);
    return result.Item || null;
  } catch (error) {
    console.error("Error getting project:", error);
    return null;
  }
}

// Update project
export async function updateProject(
  projectId: string,
  updates: Partial<Project>
): Promise<boolean> {
  try {
    const updateExpr = Object.keys(updates)
      .map((k) => `#${k} = :${k}`)
      .join(", ");

    const exprAttrNames = Object.fromEntries(
      Object.keys(updates).map((k) => [`#${k}`, k])
    );

    const exprAttrValues = Object.fromEntries(
      Object.keys(updates).map((k) => [`:${k}`, updates[k as keyof Project]])
    );

    const command = new UpdateCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROJECT#${projectId}`,
        SK: "METADATA",
      },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error updating project:", error);
    return false;
  }
}

// Delete project
export async function deleteProject(projectId: string): Promise<boolean> {
  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PROJECT#${projectId}`,
        SK: "METADATA",
      },
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error deleting project:", error);
    return false;
  }
}

// List all projects with product names
export async function listProjects(): Promise<any[]> {
  try {
    // Get both projects and products in parallel
    const [projectsResult, productsResult] = await Promise.all([
      dynamoDb.send(
        new ScanCommand({
          TableName: env.DYNAMO_DB_CONFIG_TABLE!,
          FilterExpression: "entity_type = :type",
          ExpressionAttributeValues: {
            ":type": "PROJECT",
          },
        })
      ),
      dynamoDb.send(
        new ScanCommand({
          TableName: env.DYNAMO_DB_CONFIG_TABLE!,
          FilterExpression: "entity_type = :type",
          ExpressionAttributeValues: {
            ":type": "PRODUCT",
          },
        })
      ),
    ]);

    const projects = projectsResult.Items || [];
    const products = productsResult.Items || [];

    // Map projects with product names
    return projects.map((project) => {
      const product = products.find((p) => p.id === project.product_id);
      return {
        ...project,
        product_name: product ? product.name : "Unknown Product",
      };
    });
  } catch (error) {
    console.error("Error listing projects:", error);
    return [];
  }
}

// Get projects by product ID
export async function getProjectsByProduct(productId: string): Promise<any[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type AND product_id = :productId",
      ExpressionAttributeValues: {
        ":type": "PROJECT",
        ":productId": productId,
      },
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error getting projects by product:", error);
    return [];
  }
}

// Get active projects only
export async function getActiveProjects(): Promise<any[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type AND #status = :status",
      ExpressionAttributeNames: {
        "#status": "status",
      },
      ExpressionAttributeValues: {
        ":type": "PROJECT",
        ":status": "active",
      },
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error getting active projects:", error);
    return [];
  }
}

// Check if project exists
export async function projectExists(projectId: string): Promise<boolean> {
  try {
    const project = await getProject(projectId);
    return project !== null;
  } catch (error) {
    console.error("Error checking if project exists:", error);
    return false;
  }
}

// Get projects for dropdown/select (id and name only)
export async function getProjectsForSelect(): Promise<
  Array<{ id: string; name: string }>
> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type",
      ExpressionAttributeValues: {
        ":type": "PROJECT",
      },
    });

    const result = await dynamoDb.send(command);
    const projects = result.Items || [];

    return projects.map((project) => ({
      id: project.id,
      name: project.name,
    }));
  } catch (error) {
    console.error("Error getting projects for select:", error);
    return [];
  }
}

// Count projects by status
export async function getProjectStats(): Promise<{
  total: number;
  active: number;
  inactive: number;
}> {
  try {
    const projects = await listProjects();

    return {
      total: projects.length,
      active: projects.filter((p) => p.status === "active").length,
      inactive: projects.filter((p) => p.status === "inactive").length,
    };
  } catch (error) {
    console.error("Error getting project stats:", error);
    return { total: 0, active: 0, inactive: 0 };
  }
}
