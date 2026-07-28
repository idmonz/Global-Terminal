import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDirectory, "..");
const repositoryRoot = path.resolve(appRoot, "../..");
const fixturePath = path.join(repositoryRoot, "static", "api-fixtures", "market-intelligence.json");
const symbolFixturePath = path.join(repositoryRoot, "static", "api-fixtures", "symbol-workstation.json");
const dailyBriefFixturePath = path.join(repositoryRoot, "static", "api-fixtures", "daily-brief.json");

const nextCli = path.join(appRoot, "node_modules", "next", "dist", "bin", "next");

async function main() {
  const fixture = await readFile(fixturePath, "utf8");
  const symbolFixture = await readFile(symbolFixturePath, "utf8");
  const dailyBriefFixture = await readFile(dailyBriefFixturePath, "utf8");
  const apiServer = createServer((request, response) => {
    if (request.url?.startsWith("/api/market-intelligence")) {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(fixture);
      return;
    }
    if (request.url?.startsWith("/api/symbol-workstation")) {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(symbolFixture);
      return;
    }
    if (request.url?.startsWith("/api/daily-brief")) {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(dailyBriefFixture);
      return;
    }
    response.writeHead(404, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: "not found" }));
  });

  await listen(apiServer, 0);
  const apiPort = addressPort(apiServer);
  const successPort = 3031;
  const fallbackPort = 3032;
  const apiBaseUrl = `http://127.0.0.1:${apiPort}`;

  try {
    const success = await runNextCheck({
      port: successPort,
      apiBaseUrl,
      route: "/?view=market-intelligence&mode=live-if-available",
      requiredMarkers: ["Market Intelligence", "Runtime Boundary", "runtime-api"],
    });
    const fallback = await runNextCheck({
      port: fallbackPort,
      apiBaseUrl: "http://127.0.0.1:9",
      route: "/?view=market-intelligence&mode=live-if-available",
      requiredMarkers: ["Market Intelligence", "Runtime Boundary", "runtime-fallback"],
    });
    const symbolSuccess = await runNextCheck({
      port: 3033,
      apiBaseUrl,
      route: "/?view=asset&symbol=MSFT&assetClass=equity&interval=1d&range=3mo&surface=overview&mode=live-if-available",
      requiredMarkers: ["MSFT", "Microsoft", "Universal Symbol Workstation", "runtime-api"],
    });
    const symbolFallback = await runNextCheck({
      port: 3034,
      apiBaseUrl: "http://127.0.0.1:9",
      route: "/?view=asset&symbol=MSFT&assetClass=equity&interval=1d&range=3mo&surface=overview&mode=live-if-available",
      requiredMarkers: ["MSFT", "Microsoft", "Universal Symbol Workstation", "runtime-fallback"],
    });
    const dailyBriefSuccess = await runNextCheck({
      port: 3035,
      apiBaseUrl,
      route: "/?view=daily-brief&mode=live-if-available&period=morning&section=overview",
      requiredMarkers: ["Daily Brief", "Claim ledger first", "runtime-api"],
    });

    console.log(
      `Runtime API smoke passed: success=${success.url} fallback=${fallback.url} ` +
      `symbolSuccess=${symbolSuccess.url} symbolFallback=${symbolFallback.url} dailyBriefSuccess=${dailyBriefSuccess.url}`,
    );
  } finally {
    await closeServer(apiServer);
  }
}

async function runNextCheck({ port, apiBaseUrl, route, requiredMarkers }) {
  const child = spawn(process.execPath, [nextCli, "start", "-p", String(port)], {
    cwd: appRoot,
    env: {
      ...process.env,
      GLOBAL_TERMINAL_API_BASE_URL: apiBaseUrl,
      NEXT_TELEMETRY_DISABLED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  const output = [];
  child.stdout.on("data", (chunk) => output.push(String(chunk)));
  child.stderr.on("data", (chunk) => output.push(String(chunk)));

  const url = `http://127.0.0.1:${port}${route}`;
  try {
    await waitForHttp(url);
    const response = await fetch(url);
    const body = await response.text();
    const missing = requiredMarkers.filter((marker) => !body.includes(marker));
    if (!response.ok || missing.length > 0) {
      throw new Error(`Runtime check failed for ${url}: HTTP ${response.status}, missing ${missing.join(", ")}`);
    }
    return { url };
  } finally {
    child.kill();
    await waitForExit(child);
    if (child.exitCode !== 0 && child.exitCode !== null && child.exitCode !== 1) {
      console.error(output.join(""));
    }
  }
}

async function waitForHttp(url) {
  const deadline = Date.now() + 30_000;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.status < 500) {
        return;
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(500);
  }
  throw lastError ?? new Error(`Timed out waiting for ${url}`);
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      server.off("error", reject);
      resolve();
    });
  });
}

function closeServer(server) {
  return new Promise((resolve) => server.close(resolve));
}

function waitForExit(child) {
  if (child.exitCode !== null) {
    return Promise.resolve();
  }
  return new Promise((resolve) => child.once("exit", resolve));
}

function addressPort(server) {
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Mock API server did not expose a TCP port");
  }
  return address.port;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
