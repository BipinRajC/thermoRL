import { defineConfig, devices } from "@playwright/test";

const viewer = {
  ...devices["Desktop Chrome"],
  viewport: { width: 1440, height: 900 },
  launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] },
};

export default defineConfig({
  testDir: "tests/e2e",
  outputDir: "test-artifacts/pw-results",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:4173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "fixture",
      testMatch: /smoke\.spec\.ts/,
      use: viewer,
    },
    {
      name: "real",
      testMatch: /real\.spec\.ts/,
      use: viewer,
    },
  ],
  webServer: {
    command: "npx vite build && npx vite preview --port 4173 --strictPort",
    port: 4173,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
