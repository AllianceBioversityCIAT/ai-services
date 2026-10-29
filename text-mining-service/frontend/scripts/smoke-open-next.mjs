import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

// Invoke the generated Lambda handler with local upstreams only. No AWS access,
// paid model calls, real credentials, or application data are needed.
const projectDir = process.cwd();
const upstreamCalls = [];
const imageBytes = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0, 255]);
let upstreamFailure = false;
const upstream = createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const body = Buffer.concat(chunks).toString();
  upstreamCalls.push({ url: request.url, method: request.method, headers: request.headers, body });
  if (request.url.startsWith("/smoke-assets/_assets/_next/static/media/smoke.png")) {
    response.setHeader("content-type", "application/octet-stream");
    response.setHeader("content-length", imageBytes.length);
    response.end(request.method === "HEAD" ? undefined : imageBytes);
    return;
  }
  response.setHeader("content-type", "application/json");
  if (request.url === "/authorization/validate-token") {
    response.end(JSON.stringify({ data: { isValid: true, user: { roles: [1], first_name: "Test", sec_user_id: 1 } } }));
  } else if (request.url === "/auth/validate-api-key") {
    response.end(JSON.stringify({ valid: true, mis: "TEST" }));
  } else if (request.url === "/partner-requests/create") {
    response.end(JSON.stringify({ id: 1 }));
  } else if (request.url === "/star/mining-bulk-upload/capdev") {
    response.statusCode = upstreamFailure ? 422 : 200;
    response.end(JSON.stringify(upstreamFailure ? { detail: "Test rejection" } : { records: [] }));
  } else {
    response.statusCode = 404;
    response.end("{}");
  }
});
await new Promise((resolve) => upstream.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${upstream.address().port}`;
Object.assign(process.env, {
  NODE_ENV: "production",
  AWS_EC2_METADATA_DISABLED: "true",
  AWS_REGION: "us-east-1",
  AWS_ACCESS_KEY_ID: "smoke-only-access",
  AWS_SECRET_ACCESS_KEY: "smoke-only-secret",
  AWS_SESSION_TOKEN: "smoke-only-session",
  AWS_ENDPOINT_URL_S3: base,
  AWS_IGNORE_CONFIGURED_ENDPOINT_URLS: "false",
  BUCKET_NAME: "smoke-assets",
  BUCKET_KEY_PREFIX: "_assets",
  MINING_API_BASE_URL: base,
  MANAGEMENT_API_BASE_URL: base,
  CLARISA_API_BASE_URL: base,
  CLARISA_VALIDATE_URL: `${base}/auth/validate-api-key`,
  CLARISA_PARTNER_REQUEST_CREATE_URL: `${base}/partner-requests/create`,
  BULK_UPLOAD_API_KEY: "smoke-only-key",
  CLARISA_API_KEY: "smoke-only-key",
});

try {
  const bundleDir = path.join(projectDir, ".open-next/server-functions/default");
  process.chdir(bundleDir);
  const { handler } = await import(pathToFileURL(path.join(bundleDir, "index.mjs")));
  async function invoke(rawPath, body, contentType = "application/json", method = body === undefined ? "GET" : "POST") {
    return handler({
      version: "2.0", routeKey: "$default", rawPath, rawQueryString: "",
      headers: { host: "localhost", "content-type": contentType },
      requestContext: {
        accountId: "test", apiId: "test", domainName: "localhost", domainPrefix: "test",
        http: { method, path: rawPath, protocol: "HTTP/1.1", sourceIp: "127.0.0.1", userAgent: "smoke" },
        requestId: "smoke", routeKey: "$default", stage: "$default", timeEpoch: Date.now(),
      },
      body, isBase64Encoded: false,
    }, { awsRequestId: "smoke", getRemainingTimeInMillis: () => 30000 });
  }
  const home = await invoke("/");
  assert.equal(home.statusCode, 200);
  const html = Buffer.from(home.body, home.isBase64Encoded ? "base64" : "utf8").toString();
  const asset = html.match(/src="(\/_next\/static\/[^"?]+\.js)/)?.[1];
  assert.ok(asset, "Home page must reference a static JS bundle");
  assert.ok((await readFile(path.join(projectDir, ".open-next/assets", asset))).length > 0);
  const image = await invoke("/_next/static/media/smoke.png");
  assert.equal(image.statusCode, 200);
  assert.equal(image.headers["content-type"], "image/png");
  assert.deepEqual(Buffer.from(image.body, image.isBase64Encoded ? "base64" : "utf8"), imageBytes);
  assert.equal((await invoke("/_next/static/media/smoke.png", undefined, "application/json", "HEAD")).statusCode, 200);
  assert.equal((await invoke("/preview")).statusCode, 200);
  assert.equal((await invoke("/api/validate-token", "{}")).statusCode, 400);
  const auth = await invoke("/api/validate-token", JSON.stringify({ token: "smoke-token" }));
  assert.equal(auth.statusCode, 200);
  assert.equal(JSON.parse(auth.body).valid, true);
  const authCall = upstreamCalls.find((call) => call.url === "/authorization/validate-token");
  assert.equal(authCall.method, "PATCH");
  assert.equal(authCall.headers["access-token"], "smoke-token");

  const form = new FormData();
  form.set("key", "fictional/test.xlsx");
  form.set("file", new Blob(["fictional spreadsheet"], { type: "application/octet-stream" }), "test.xlsx");
  const encodedForm = new Request(`${base}/unused`, { method: "POST", body: form });
  const formBody = await encodedForm.text();
  const formType = encodedForm.headers.get("content-type");
  assert.equal((await invoke("/api/bulk-upload", formBody, formType)).statusCode, 200);
  const miningCall = upstreamCalls.find((call) => call.url === "/star/mining-bulk-upload/capdev");
  assert.equal(miningCall.headers["x-api-key"], "smoke-only-key");
  assert.match(miningCall.headers["content-type"], /^multipart\/form-data; boundary=/);
  assert.ok(miningCall.body.includes("fictional/test.xlsx") && miningCall.body.includes("fictional spreadsheet"));
  upstreamFailure = true;
  assert.equal((await invoke("/api/bulk-upload", formBody, formType)).statusCode, 422);

  const payload = { name: "Fictional Test Partner", hqCountryIso: "CO", institutionTypeCode: 1, userId: 1 };
  assert.equal((await invoke("/api/partner-request", JSON.stringify({ payload }))).statusCode, 200);
  const validationCall = upstreamCalls.find((call) => call.url === "/auth/validate-api-key");
  assert.equal(JSON.parse(validationCall.body).endpoint_accessed, "/api/partner-request");
  const partnerCall = upstreamCalls.find((call) => call.url === "/partner-requests/create");
  assert.equal(partnerCall.headers["x-api-key"], "smoke-only-key");
  assert.deepEqual(JSON.parse(partnerCall.body), payload);
  console.log("OpenNext Lambda smoke passed: pages, static bundle, auth, multipart proxy, upstream errors, partner request.");
} finally {
  process.chdir(projectDir);
  upstream.closeAllConnections();
  await new Promise((resolve) => upstream.close(resolve));
}
