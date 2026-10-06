// Launches the FastAPI backend on :8000 for local dev (used by root `npm start`).
import { spawnSync, spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cwd = resolve(root, "backend");
const env = {
  DATABASE_PATH: "./dev.db",
  JWT_SECRET: "dev-secret-at-least-32-bytes-long-0123456789",
  PROVIDER_TIMEZONE: "UTC",
  APP_ENV: "dev",
  ...process.env,
};
const opts = { cwd, env, stdio: "inherit", shell: process.platform === "win32" };

const migrate = spawnSync("uv", ["run", "alembic", "upgrade", "head"], opts);
if (migrate.status !== 0) process.exit(migrate.status ?? 1);

const server = spawn(
  "uv",
  ["run", "uvicorn", "telemed.api.app:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000"],
  opts,
);
server.on("exit", (code) => process.exit(code ?? 0));
