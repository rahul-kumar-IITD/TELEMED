// Starts an isolated backend on :8000 for the Playwright suite: fresh throwaway SQLite DB,
// migrated and seeded (the seed creates the admin), provider timezone Asia/Kolkata.
import { spawnSync, spawn } from "node:child_process";
import { rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cwd = resolve(root, "backend");
const dbFile = "./e2e.db";
for (const suffix of ["", "-wal", "-shm"]) rmSync(resolve(cwd, dbFile + suffix), { force: true });

const env = {
  ...process.env,
  DATABASE_PATH: dbFile,
  JWT_SECRET: "e2e-secret-at-least-32-bytes-long-0123456789",
  PROVIDER_TIMEZONE: "Asia/Kolkata",
  APP_ENV: "dev",
};
const opts = { cwd, env, stdio: "inherit", shell: process.platform === "win32" };

for (const args of [
  ["run", "alembic", "upgrade", "head"],
  ["run", "python", "scripts/seed.py"],
]) {
  const step = spawnSync("uv", args, opts);
  if (step.status !== 0) process.exit(step.status ?? 1);
}

const server = spawn(
  "uv",
  ["run", "uvicorn", "telemed.api.app:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000"],
  opts,
);
server.on("exit", (code) => process.exit(code ?? 0));
