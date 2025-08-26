import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  UpdateCommand,
  DeleteCommand,
  ScanCommand,
  QueryCommand,
} from "@aws-sdk/lib-dynamodb";
import { v4 as uuidv4 } from "uuid";
import { env } from "process";
import { dynamoDb } from "./dynamo";

// PRODUCT CRUD
export async function createProduct(product: any) {
  const id = uuidv4();
  const PK = `PRODUCT#${id}`;
  const SK = "METADATA";
  const item = {
    PK,
    SK,
    entity_type: "PRODUCT",
    id,
    name: product.name,
    description: product.description,
    image_url: product.image_url,
    status: product.status || "active",
    created_at: new Date().toISOString(),
  };
  const newProduct = await dynamoDb.send(
    new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    })
  );
  return item;
}

export async function getProduct(productId: string) {
  const PK = `PRODUCT#${productId}`;
  const SK = "METADATA";
  const result = await dynamoDb.send(
    new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
    })
  );
  return result.Item;
}

export async function updateProduct(productId: string, updates: any) {
  const PK = `PRODUCT#${productId}`;
  const SK = "METADATA";
  const updateExpr = Object.keys(updates)
    .map((k, i) => `#${k}=:${k}`)
    .join(", ");
  const exprAttrNames = Object.fromEntries(
    Object.keys(updates).map((k) => [`#${k}`, k])
  );
  const exprAttrValues = Object.fromEntries(
    Object.keys(updates).map((k) => [`:${k}`, updates[k]])
  );
  await dynamoDb.send(
    new UpdateCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    })
  );
}

export async function deleteProduct(productId: string) {
  const PK = `PRODUCT#${productId}`;
  const SK = "METADATA";
  await dynamoDb.send(
    new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
    })
  );
}

export async function listProducts() {
  const result = await dynamoDb.send(
    new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      FilterExpression: "entity_type = :type",
      ExpressionAttributeValues: { ":type": "PRODUCT" },
    })
  );
  return result.Items || [];
}

// PROJECT CRUD
export async function createProject(project: any) {
  const id = uuidv4();
  const PK = `PROJECT#${id}`;
  const SK = "METADATA";
  const item = {
    PK,
    SK,
    entity_type: "PROJECT",
    name: project.name,
    description: project.description,
    product_id: project.product_id,
    status: project.status || "active",
    created_at: new Date().toISOString(),
  };
  await dynamoDb.send(
    new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    })
  );
  return item;
}

export async function getProject(projectId: string) {
  const PK = `PROJECT#${projectId}`;
  const SK = "METADATA";
  const result = await dynamoDb.send(
    new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
    })
  );
  return result.Item;
}

export async function updateProject(projectId: string, updates: any) {
  const PK = `PROJECT#${projectId}`;
  const SK = "METADATA";
  const updateExpr = Object.keys(updates)
    .map((k, i) => `#${k}=:${k}`)
    .join(", ");
  const exprAttrNames = Object.fromEntries(
    Object.keys(updates).map((k) => [`#${k}`, k])
  );
  const exprAttrValues = Object.fromEntries(
    Object.keys(updates).map((k) => [`:${k}`, updates[k]])
  );
  await dynamoDb.send(
    new UpdateCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    })
  );
}

export async function deleteProject(projectId: string) {
  const PK = `PROJECT#${projectId}`;
  const SK = "METADATA";
  await dynamoDb.send(
    new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
    })
  );
}

export async function listProjects() {
  const result = await dynamoDb.send(
    new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      FilterExpression: "entity_type = :type",
      ExpressionAttributeValues: { ":type": "PROJECT" },
    })
  );
  const projects = result.Items || [];

  const productsResult = await dynamoDb.send(
    new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      FilterExpression: "entity_type = :type",
      ExpressionAttributeValues: { ":type": "PRODUCT" },
    })
  );
  const products = productsResult.Items || [];

  const projectsWithProductName = projects.map((project) => {
    const product = products.find((p) => p.id === project.product_id);
    return {
      ...project,
      product_name: product ? product.name : "",
    };
  });

  return projectsWithProductName;
}

// PROMPT VERSIONING CRUD
export async function createPromptVersion(prompt: any) {
  const PK = `PROMPT#${prompt.project_id}`;
  const SK = `VERSION#${prompt.created_at}`;
  const item = {
    PK,
    SK,
    entity_type: "PROMPT",
    ...prompt,
  };
  await dynamoDb.send(
    new PutCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Item: item,
    })
  );
  return item;
}

export async function getPromptVersions(projectId: string) {
  const PK = `PROMPT#${projectId}`;
  const result = await dynamoDb.send(
    new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      KeyConditionExpression: "PK = :pk",
      ExpressionAttributeValues: { ":pk": PK },
    })
  );
  return result.Items || [];
}

export async function getPromptLTS(projectId: string) {
  const PK = `PROMPT#${projectId}`;
  const result = await dynamoDb.send(
    new QueryCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      KeyConditionExpression: "PK = :pk",
      FilterExpression: "is_stable = :stable",
      ExpressionAttributeValues: { ":pk": PK, ":stable": true },
    })
  );
  return result.Items?.[0] || null;
}

export async function deletePromptVersion(
  projectId: string,
  created_at: string
) {
  const PK = `PROMPT#${projectId}`;
  const SK = `VERSION#${created_at}`;
  await dynamoDb.send(
    new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE,
      Key: { PK, SK },
    })
  );
}
