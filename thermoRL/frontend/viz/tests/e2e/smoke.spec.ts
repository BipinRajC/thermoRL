import { expect, test, type Page } from "@playwright/test";
import { scanText } from "../support/forbidden";

const FIXTURE = "/?data=replay-fixture";
const SHOTS = "test-artifacts";

interface FixtureCatalog {
  strings: { precision_note: string };
}

async function ready(page: Page, query = ""): Promise<void> {
  await page.goto(`${FIXTURE}${query}`);
  await expect(page.locator("#stage")).toHaveAttribute("data-state", "ready");
  await expect(page.locator("#status")).toBeHidden();
  await expect(page.locator("#legend-left .legend-max")).toBeVisible();
}

const clock = (page: Page) => page.locator("#clock");

test.describe("fixture bundle", () => {
  test("title, headline, canvas and WebGL", async ({ page }) => {
    await ready(page);
    await expect(page.locator("#app-title")).toHaveText("ThermoRL — closed-loop FMU replay");
    const headline = (await (await page.request.get("/replay-fixture/EFIX/frozen_outcome.json")).json()).headline as string;
    await expect(page.locator("#drawer .outcome-headline")).toHaveText(headline);
    await expect(page.locator("canvas#gl")).toBeVisible();
    const webgl = await page.evaluate(() => {
      const gl = document.createElement("canvas").getContext("webgl2") ?? document.createElement("canvas").getContext("webgl");
      return Boolean(gl);
    });
    expect(webgl).toBe(true);
    await expect(page.locator("#fallback")).toBeHidden();
    await page.screenshot({ path: `${SHOTS}/default.png` });
  });

  test("stepping controls and keyboard cross the evaluation boundary", async ({ page }) => {
    await ready(page);
    await expect(clock(page)).toContainText("tick 0/400");

    await page.getByRole("button", { name: "+10 min" }).click();
    await expect(clock(page)).toContainText("tick 60/400");
    await page.getByRole("button", { name: "−1 min" }).click();
    await expect(clock(page)).toContainText("tick 54/400");

    await page.getByRole("button", { name: "Jump to evaluation start" }).click();
    await expect(clock(page)).toContainText("tick 360/400");
    await expect(clock(page)).toContainText("01:00:10");
    await page.getByRole("button", { name: "−1 tick" }).click();
    await expect(clock(page)).toContainText("tick 359/400");
    await expect(clock(page)).toContainText("01:00:00");
    await expect(clock(page)).toContainText("before evaluation window");

    await page.locator("body").click({ position: { x: 2, y: 2 } });
    await page.keyboard.press("ArrowRight");
    await expect(clock(page)).toContainText("tick 360/400");
    await expect(clock(page)).toContainText("01:00:10");
    await expect(clock(page)).toContainText(/(?<!before )evaluation window/);
    await expect(clock(page)).not.toContainText("before evaluation window");

    await page.getByRole("button", { name: "+1 tick" }).click();
    await expect(clock(page)).toContainText("tick 361/400");
  });

  test("t=3600 deep link reads before evaluation window", async ({ page }) => {
    await ready(page, "&t=3600");
    await expect(clock(page)).toContainText("tick 359/400");
    await expect(clock(page)).toContainText("before evaluation window");
  });

  test("Why? drawer at the burst tick lists decisions with the precision note", async ({ page, request }) => {
    const cat = (await (await request.get("/replay-fixture/EFIX/catalog.json")).json()) as FixtureCatalog;
    await ready(page, "&t=3610");
    await expect(clock(page)).toContainText("tick 360/400");
    await page.getByRole("button", { name: "Why?" }).click();
    const why = page.locator('#drawer [data-pane="why"]');
    await expect(why.locator(".why-precision-plain")).toBeVisible();
    await expect(why.locator(".why-precision")).toBeHidden();
    await why.getByText("Technical detail").click();
    await expect(why.locator(".why-precision")).toBeVisible();
    await expect(why.locator(".why-precision")).toHaveText(cat.strings.precision_note);
    await expect(why.locator(".why-item").first()).toBeVisible();
    expect(await why.locator(".why-item").count()).toBeGreaterThanOrEqual(1);
    await expect(why.locator(".why-count")).toHaveText("120 decisions");
    await page.screenshot({ path: `${SHOTS}/burst-why.png` });
  });

  test("Why? drawer is empty where no job starts", async ({ page }) => {
    await ready(page, "&t=1200");
    await page.getByRole("button", { name: "Why?" }).click();
    await expect(page.locator('#drawer [data-pane="why"] .why-empty')).toBeVisible();
    await expect(page.locator('#drawer [data-pane="why"] .why-item')).toHaveCount(0);
  });

  test("switching to seed 2 changes the legend range", async ({ page }) => {
    await ready(page);
    const legend = page.locator("#legend-left .legend-ends");
    const before = await legend.innerText();
    await page.locator("#sel-seed").selectOption("2");
    await expect(page.locator("#stage")).toHaveAttribute("data-state", "ready");
    await expect.poll(() => legend.innerText()).not.toBe(before);
    await expect(page.locator("#sel-seed")).toHaveValue("2");
    await page.screenshot({ path: `${SHOTS}/seed2.png` });
  });

  test("hovering a tile shows the modelled coolant tooltip", async ({ page }) => {
    await ready(page);
    const box = await page.locator("#view-left").boundingBox();
    if (!box) throw new Error("view-left has no box");
    const tooltip = page.locator("#tooltip");
    let shown = false;
    for (let iy = 1; iy < 12 && !shown; iy++) {
      for (let ix = 1; ix < 12 && !shown; ix++) {
        await page.mouse.move(box.x + (box.width * ix) / 12, box.y + (box.height * iy) / 12);
        shown = await tooltip.isVisible();
      }
    }
    expect(shown).toBe(true);
    await expect(tooltip).toContainText("Modelled coolant");
    await expect(tooltip).toContainText("Rack power");
  });

  test("rendered text contains no forbidden wording", async ({ page }) => {
    await ready(page);
    for (const name of ["Why?", "About this data", "Outcome"]) {
      await page.getByRole("button", { name }).click();
      const text = await page.evaluate(() => document.body.innerText);
      expect(scanText(text), name).toEqual([]);
    }
    for (const name of ["Rack kW", "Occupied", "Coolant °C"]) {
      await page.getByRole("button", { name }).click();
      expect(scanText(await page.evaluate(() => document.body.innerText)), name).toEqual([]);
    }
  });

  test("a missing data directory shows the error panel naming the file", async ({ page }) => {
    await page.goto("/?data=does-not-exist");
    await expect(page.locator("#stage")).toHaveAttribute("data-state", "error");
    const status = page.locator("#status");
    await expect(status).toBeVisible();
    await expect(status).toHaveAttribute("role", "alert");
    await expect(status.locator(".status-kind")).toContainText("kind:");
    await expect(status.locator(".status-file")).toContainText("index.json");
    await expect(status.locator(".status-hint code")).toContainText("npm run sync-replay");
    await expect(page.locator("#panels")).toBeHidden();
  });

  test("a missing run file shows the error panel naming that file", async ({ page }) => {
    await page.route("**/replay-fixture/EFIX/runs/thermal_predictive_seed1/run.json", (route) => route.fulfill({ status: 404, body: "" }));
    await page.goto(FIXTURE);
    await expect(page.locator("#stage")).toHaveAttribute("data-state", "error");
    const status = page.locator("#status");
    await expect(status.locator(".status-kind")).toHaveText("kind: missing");
    await expect(status.locator(".status-file")).toContainText("thermal_predictive_seed1/run.json");
    await expect(status.locator(".status-hint code")).toContainText("npm run sync-replay");
    await expect(page.locator("#panels")).toBeHidden();
  });
});
