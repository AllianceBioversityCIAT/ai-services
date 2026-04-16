import { GetObjectCommand, HeadObjectCommand, S3Client } from "@aws-sdk/client-s3";
import type { InternalEvent, InternalResult } from "@opennextjs/aws/types/open-next.js";
import type { AssetResolver } from "@opennextjs/aws/types/overrides.js";
import { Readable } from "node:stream";

/**
 * Sirve estáticos desde S3 cuando solo hay Function URL (sin CloudFront delante).
 * OpenNext 3 usa por defecto assetResolver "dummy" y asume CF→S3 para /_next/static.
 *
 * URL del navegador: /_next/static/media/foo.<hash>.png (Next no usa /static/bulk_upload para imports).
 * Clave S3 canónica: <BUCKET_KEY_PREFIX>/_next/static/media/foo.<hash>.png
 *   con BUCKET_KEY_PREFIX=_assets → _assets/_next/static/media/...
 * Jenkins debe hacer: aws s3 sync .open-next/assets/ s3://$BUCKET/_assets/
 *
 * @see https://opennext.js.org/aws/config/overrides/asset_resolver
 */
const client = new S3Client({
  region: process.env.AWS_REGION ?? process.env.BUCKET_REGION,
});

function trimmedPath(rawPath: string): string {
  const pathOnly = rawPath.split("?")[0];
  return pathOnly.startsWith("/") ? pathOnly.slice(1) : pathOnly;
}

/**
 * Orden: clave canónica primero; si el prefijo es _assets, reintenta bajo "assets/"
 * (syncs erróneos que omiten el guión bajo inicial).
 */
function candidateObjectKeys(rawPath: string): string[] {
  const trimmed = trimmedPath(rawPath);
  const prefix =
    process.env.BUCKET_KEY_PREFIX?.replace(/^\/|\/$/g, "").trim() ?? "_assets";
  const primary = prefix ? `${prefix}/${trimmed}` : trimmed;
  const keys = [primary];
  if (primary.startsWith("_assets/")) {
    keys.push(`assets/${trimmed}`);
  }
  return keys;
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

/** S3 a veces deja ContentType vacío o application/octet-stream tras sync; el <img> puede fallar en algunos navegadores. */
function effectiveContentType(key: string, s3ContentType: string | undefined): string {
  const generic =
    !s3ContentType ||
    s3ContentType === "binary/octet-stream" ||
    s3ContentType === "application/octet-stream";
  if (!generic) return s3ContentType;

  const k = key.toLowerCase();
  if (k.endsWith(".png")) return "image/png";
  if (k.endsWith(".jpg") || k.endsWith(".jpeg")) return "image/jpeg";
  if (k.endsWith(".gif")) return "image/gif";
  if (k.endsWith(".webp")) return "image/webp";
  if (k.endsWith(".svg")) return "image/svg+xml";
  if (k.endsWith(".ico")) return "image/x-icon";
  if (k.endsWith(".css")) return "text/css; charset=utf-8";
  if (k.endsWith(".js") || k.endsWith(".mjs")) return "application/javascript; charset=utf-8";
  if (k.endsWith(".woff2")) return "font/woff2";
  if (k.endsWith(".woff")) return "font/woff";
  return s3ContentType ?? "application/octet-stream";
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

    const keys = candidateObjectKeys(event.rawPath);

    for (const key of keys) {
      try {
        if (event.method === "HEAD") {
          const head = await client.send(
            new HeadObjectCommand({ Bucket: bucket, Key: key }),
          );
          return {
            type: "core",
            statusCode: 200,
            headers: {
              "content-type": effectiveContentType(key, head.ContentType),
              "cache-control": head.CacheControl ?? "public, max-age=31536000, immutable",
              ...(head.ContentLength != null
                ? { "content-length": String(head.ContentLength) }
                : {}),
            },
            body: emptyBody() as InternalResult["body"],
            isBase64Encoded: false,
          };
        }

        const out = await client.send(
          new GetObjectCommand({ Bucket: bucket, Key: key }),
        );
        const bodyNode = out.Body as Readable | undefined;
        if (!bodyNode) return undefined;

        const body = Readable.toWeb(bodyNode) as InternalResult["body"];
        const contentType = effectiveContentType(key, out.ContentType);

        return {
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
      } catch (e: unknown) {
        if (isS3NotFound(e)) continue;
        throw e;
      }
    }

    return undefined;
  },
};

export default resolver;
