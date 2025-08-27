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

// Product interface for DynamoDB
export interface Product {
  id: string;
  name: string;
  description: string;
  image_url?: string;
  status: "active" | "inactive";
  created_at: string;
}

// Create product
export async function createProduct(
  product: Omit<Product, "id" | "created_at">
): Promise<any> {
  try {
    const id = uuidv4();
    const item = {
      PK: `PRODUCT#${id}`,
      SK: "METADATA",
      entity_type: "PRODUCT",
      id,
      name: product.name,
      description: product.description,
      image_url: product.image_url || "",
      status: product.status || "active",
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
    console.error("Error creating product:", error);
    throw error;
  }
}

// Get product by ID
export async function getProduct(productId: string): Promise<any | null> {
  try {
    const command = new GetCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PRODUCT#${productId}`,
        SK: "METADATA",
      },
    });

    const result = await dynamoDb.send(command);
    return result.Item || null;
  } catch (error) {
    console.error("Error getting product:", error);
    return null;
  }
}

// Update product
export async function updateProduct(
  productId: string,
  updates: Partial<Product>
): Promise<boolean> {
  try {
    const updateExpr = Object.keys(updates)
      .map((k) => `#${k} = :${k}`)
      .join(", ");

    const exprAttrNames = Object.fromEntries(
      Object.keys(updates).map((k) => [`#${k}`, k])
    );

    const exprAttrValues = Object.fromEntries(
      Object.keys(updates).map((k) => [`:${k}`, updates[k as keyof Product]])
    );

    const command = new UpdateCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PRODUCT#${productId}`,
        SK: "METADATA",
      },
      UpdateExpression: `SET ${updateExpr}`,
      ExpressionAttributeNames: exprAttrNames,
      ExpressionAttributeValues: exprAttrValues,
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error updating product:", error);
    return false;
  }
}

// Delete product
export async function deleteProduct(productId: string): Promise<boolean> {
  try {
    const command = new DeleteCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      Key: {
        PK: `PRODUCT#${productId}`,
        SK: "METADATA",
      },
    });

    await dynamoDb.send(command);
    return true;
  } catch (error) {
    console.error("Error deleting product:", error);
    return false;
  }
}

// List all products
export async function listProducts(): Promise<any[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type",
      ExpressionAttributeValues: {
        ":type": "PRODUCT",
      },
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error listing products:", error);
    return [];
  }
}

// Get products for dropdown/select (id and name only)
export async function getProductsForSelect(): Promise<
  Array<{ id: string; name: string }>
> {
  try {
    const products = await listProducts();
    return products.map((product) => ({
      id: product.id,
      name: product.name,
    }));
  } catch (error) {
    console.error("Error getting products for select:", error);
    return [];
  }
}

// Check if product exists
export async function productExists(productId: string): Promise<boolean> {
  try {
    const product = await getProduct(productId);
    return product !== null;
  } catch (error) {
    console.error("Error checking if product exists:", error);
    return false;
  }
}

// Get active products only
export async function getActiveProducts(): Promise<any[]> {
  try {
    const command = new ScanCommand({
      TableName: env.DYNAMO_DB_CONFIG_TABLE!,
      FilterExpression: "entity_type = :type AND #status = :status",
      ExpressionAttributeNames: {
        "#status": "status",
      },
      ExpressionAttributeValues: {
        ":type": "PRODUCT",
        ":status": "active",
      },
    });

    const result = await dynamoDb.send(command);
    return result.Items || [];
  } catch (error) {
    console.error("Error getting active products:", error);
    return [];
  }
}
