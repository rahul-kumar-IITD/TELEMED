import { spawnSync } from "node:child_process";
import { request } from "@playwright/test";
import { ADMIN, API } from "./fixtures/api";

async function adminCanLogin(): Promise<boolean> {
  const ctx = await request.newContext({ baseURL: API });
  try {
    const res = await ctx.post("/api/auth/login", { data: ADMIN });
    return res.ok();
  } finally {
    await ctx.dispose();
  }
}

/** The suite needs the seeded admin. When it reuses an already-running backend lacking one, seed it. */
export default async function globalSetup(): Promise<void> {
  if (await adminCanLogin()) return;
  const seed = spawnSync("uv", ["run", "python", "scripts/seed.py"], {
    cwd: "backend",
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (seed.status !== 0 || !(await adminCanLogin())) {
    throw new Error("e2e: admin account unavailable and seeding failed; check DATABASE_PATH/JWT_SECRET");
  }
}
