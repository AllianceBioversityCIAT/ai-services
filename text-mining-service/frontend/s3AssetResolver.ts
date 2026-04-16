import { GetObjectCommand, HeadObjectCommand, S3Client } from "@aws-sdk/client-s3";
import type { InternalEvent, InternalResult } from "@opennextjs/aws/types/open-next.js";
import type { AssetResolver } from "@opennextjs/aws/types/overrides.js";
import { Readable } from "node:stream";

/**
 * Sirve estáticos desde S3 cuando solo hay Function URL (sin CloudFront delante).
 * OpenNext 3 usa por defecto assetResolver "dummy" y asume CF→S3 para /_next/static.
 * @see https://opennext.js.org/aws/config/overrides/asset_resolver
 */
const client = new S3Client({
  region: process.env.AWS_REGION ?? process.env.BUCKET_REGION,
});

function buildObjectKey(rawPath: string): string {
  const pathOnly = rawPath.split("?")[0];
  const trimmed = pathOnly.startsWith("/") ? pathOnly.slice(1) : pathOnly;
  const prefix = process.env.BUCKET_KEY_PREFIX?.replace(/^\/|\/$/g, "") ?? "";
  return prefix ? `${prefix}/${trimmed}` : trimmed;
}

function shouldResolveFromS3(pathOnly: string): boolean {
  if (pathOnly === "/BUILD_ID") return true;
  if (pathOnly === "/favicon.ico") return true;
  if (pathOnly.startsWith("/_next/static/")) return true;
  if (pathOnly.startsWith("/static/")) return true;
  if (pathOnly.startsWith("/_next/image")) return false;
  if (pathOnly.startsWith("/_next/data/")) return false;
  return /\.(svg|ico|png|jpg|jpeg|gif|webp|txt|woff2?|ttf|eot|css|js|map)$/i.test(
    pathOnly,
  );
}

function isS3NotFound(e: unknown): boolean {
  if (typeof e !== "object" || e === null || !("name" in e)) return false;
  const name = (e as { name: string }).name;
  return name === "NoSuchKey" || name === "NotFound";
}

function emptyBody(): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      controller.close();
    },
  });
}

const resolver: AssetResolver = {
  name: "s3-function-url",
  maybeGetAssetResult: async (
    event: InternalEvent,
  ): Promise<InternalResult | undefined> => {
    if (event.method !== "GET" && event.method !== "HEAD") return;

    const pathOnly = event.rawPath.split("?")[0];
    if (!shouldResolveFromS3(pathOnly)) return;

    const bucket = process.env.BUCKET_NAME;
    if (!bucket) return;

    const key = buildObjectKey(event.rawPath);

    try {
      if (event.method === "HEAD") {
        const head = await client.send(
          new HeadObjectCommand({ Bucket: bucket, Key: key }),
        );
        const headResult: InternalResult = {
          type: "core",
          statusCode: 200,
          headers: {
            "content-type": head.ContentType ?? "application/octet-stream",
            "cache-control": head.CacheControl ?? "public, max-age=31536000, immutable",
            ...(head.ContentLength != null
              ? { "content-length": String(head.ContentLength) }
              : {}),
          },
          body: emptyBody() as InternalResult["body"],
          isBase64Encoded: false,
        };
        return headResult;
      }

      const out = await client.send(
        new GetObjectCommand({ Bucket: bucket, Key: key }),
      );
      const bodyNode = out.Body as Readable | undefined;
      if (!bodyNode) return undefined;

      const body = Readable.toWeb(bodyNode) as InternalResult["body"];
      const contentType = out.ContentType ?? "application/octet-stream";

      const ok: InternalResult = {
        type: "core",
        statusCode: 200,
        headers: {
          "content-type": contentType,
          "cache-control":
            out.CacheControl ?? "public, max-age=31536000, immutable",
        },
        body,
        isBase64Encoded: false,
      };
      return ok;
    } catch (e: unknown) {
      if (isS3NotFound(e)) return undefined;
      throw e;
    }
  },
};

export default resolver;
