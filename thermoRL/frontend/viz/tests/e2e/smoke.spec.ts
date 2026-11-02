import { expect, test, type Page } from "@playwright/test";
import { scanText } from "../support/forbidden";

const FIXTURE = "/?data=replay-fixture";
const SHOTS = "test-artifacts";

interface FixtureCatalog {
  strings: { s2: string; precision_note: string };
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

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

const boxOf = async (page: Page, selector: string): Promise<Box> => {
  const box = await page.locator(selector).boundingBox();
  if (!box) throw new Error(`${selector} has no bounding box`);
  return box;
};

const widthOf = async (page: Page, selector: string): Promise<number> => (await boxOf(page, selector)).width;

async function drag(page: Page, selector: string, dx: number, dy: number): Promise<void> {
  const b = await boxOf(page, selector);
  const x = b.x + b.width / 2;
  const y = b.y + b.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx / 2, y + dy / 2, { steps: 4 });
  await page.mouse.move(x + dx, y + dy, { steps: 4 });
  await page.mouse.up();
}

async function tooltipOnLeftGrid(page: Page): Promise<boolean> {
  const box = await boxOf(page, "#view-left");
  const tooltip = page.locator("#tooltip");
  for (let iy = 1; iy < 12; iy++) {
    for (let ix = 1; ix < 12; ix++) {
      await page.mouse.move(box.x + (box.width * ix) / 12, box.y + (box.height * iy) / 12);
      if (await tooltip.isVisible()) return true;
    }
  }
  return false;
}

async function stageUsable(page: Page): Promise<void> {
  for (const sel of ["#view-left", "#view-right", "canvas#gl"]) {
    await expect(page.locator(sel)).toBeVisible();
    const b = await boxOf(page, sel);
    expect(b.width, `${sel} width`).toBeGreaterThan(0);
    expect(b.height, `${sel} height`).toBeGreaterThan(0);
  }
}

test.describe("fixture layout splitters", () => {
  test("dragging the drawer edge left widens the drawer; grids, canvas and tooltip still work", async ({ page }) => {
    await ready(page);
    const before = await widthOf(page, "#drawer");
    const leftBefore = await widthOf(page, "#view-left");
    await drag(page, "#split-drawer", -150, 0);
    await expect.poll(() => widthOf(page, "#drawer")).toBeGreaterThanOrEqual(before + 100);
    expect(await widthOf(page, "#drawer")).toBeLessThanOrEqual(800 + 1);
    await expect.poll(() => widthOf(page, "#view-left")).toBeLessThan(leftBefore);
    await stageUsable(page);
    expect(await tooltipOnLeftGrid(page)).toBe(true);
    await expect(page.locator("#tooltip")).toContainText("Modelled coolant");
    await page.screenshot({ path: `${SHOTS}/split-drawer-wide.png` });
  });

  test("dragging the drawer edge right narrows it but never below 300 px", async ({ page }) => {
    await ready(page);
    await drag(page, "#split-drawer", 600, 0);
    await expect.poll(() => widthOf(page, "#drawer")).toBeLessThan(461);
    expect(await widthOf(page, "#drawer")).toBeGreaterThanOrEqual(299);
    await stageUsable(page);
  });

  test("dragging the panels splitter moves the left/right panel widths in opposite directions", async ({ page }) => {
    await ready(page);
    const l0 = await widthOf(page, "#panel-left");
    const r0 = await widthOf(page, "#panel-right");
    await drag(page, "#split-panels", 100, 0);
    await expect.poll(() => widthOf(page, "#panel-left")).toBeGreaterThan(l0 + 60);
    expect(await widthOf(page, "#panel-right")).toBeLessThan(r0 - 60);
    const l1 = await widthOf(page, "#panel-left");
    await drag(page, "#split-panels", -300, 0);
    await expect.poll(() => widthOf(page, "#panel-left")).toBeLessThan(l1 - 200);
    expect(await widthOf(page, "#panel-left")).toBeGreaterThanOrEqual(239);
    await stageUsable(page);
    expect(await tooltipOnLeftGrid(page)).toBe(true);
  });

  test("dragging the timeline splitter changes its height within 80..400 px", async ({ page }) => {
    await ready(page);
    const h0 = (await boxOf(page, "#timeline")).height;
    expect(h0).toBeGreaterThan(160);
    expect(h0).toBeLessThan(176);
    await drag(page, "#split-timeline", 0, -100);
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeGreaterThan(h0 + 80);
    await drag(page, "#split-timeline", 0, -800);
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeGreaterThan(398);
    expect((await boxOf(page, "#timeline")).height).toBeLessThanOrEqual(401);
    await drag(page, "#split-timeline", 0, 1000);
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeLessThan(82);
    expect((await boxOf(page, "#timeline")).height).toBeGreaterThanOrEqual(79);
    await stageUsable(page);
  });

  test("double-click resets each splitter to its default", async ({ page }) => {
    await ready(page);
    const drawer0 = await widthOf(page, "#drawer");
    const panelL0 = await widthOf(page, "#panel-left");
    const panelR0 = await widthOf(page, "#panel-right");
    const timeline0 = (await boxOf(page, "#timeline")).height;
    expect(drawer0).toBeCloseTo(460, 0);

    await drag(page, "#split-drawer", -150, 0);
    await expect.poll(() => widthOf(page, "#drawer")).toBeGreaterThan(drawer0 + 100);
    await page.locator("#split-drawer").dblclick();
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(drawer0, 0);

    await drag(page, "#split-panels", 100, 0);
    await expect.poll(() => widthOf(page, "#panel-left")).toBeGreaterThan(panelL0 + 60);
    await page.locator("#split-panels").dblclick();
    await expect.poll(() => widthOf(page, "#panel-left")).toBeCloseTo(panelL0, 0);
    await expect.poll(() => widthOf(page, "#panel-right")).toBeCloseTo(panelR0, 0);

    await drag(page, "#split-timeline", 0, -100);
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeGreaterThan(timeline0 + 80);
    await page.locator("#split-timeline").dblclick();
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeCloseTo(timeline0, 0);
    await stageUsable(page);
  });

  test("arrow keys on a focused splitter resize it and do not step playback", async ({ page }) => {
    await ready(page, "&t=3610");
    await expect(clock(page)).toContainText("tick 360/400");
    const clockBefore = await clock(page).innerText();

    await page.locator("#split-drawer").focus();
    const d0 = await widthOf(page, "#drawer");
    await page.keyboard.press("ArrowLeft");
    await expect.poll(() => widthOf(page, "#drawer")).toBeGreaterThan(d0 + 8);
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => widthOf(page, "#drawer")).toBeLessThan(d0 - 8);

    await page.locator("#split-panels").focus();
    const l0 = await widthOf(page, "#panel-left");
    await page.keyboard.press("ArrowRight");
    await expect.poll(() => widthOf(page, "#panel-left")).toBeGreaterThan(l0 + 8);
    await page.keyboard.press("ArrowLeft");
    await page.keyboard.press("ArrowLeft");
    await expect.poll(() => widthOf(page, "#panel-left")).toBeLessThan(l0 - 8);

    await page.locator("#split-timeline").focus();
    const t0 = (await boxOf(page, "#timeline")).height;
    await page.keyboard.press("ArrowUp");
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeGreaterThan(t0 + 8);
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await expect.poll(async () => (await boxOf(page, "#timeline")).height).toBeLessThan(t0 - 8);

    await expect(clock(page)).toContainText("tick 360/400");
    expect(await clock(page).innerText()).toBe(clockBefore);
  });

  test("the drawer at its maximum leaves the grids usable at 1440 px", async ({ page }) => {
    await ready(page);
    await page.locator("#split-drawer").focus();
    await page.keyboard.press("End");
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(800, 0);
    await expect.poll(() => widthOf(page, "#stage")).toBeGreaterThanOrEqual(630);
    await stageUsable(page);
    expect(await widthOf(page, "#view-left")).toBeGreaterThanOrEqual(120);
    expect(await widthOf(page, "#view-right")).toBeGreaterThanOrEqual(120);
    await drag(page, "#split-drawer", -400, 0);
    await expect.poll(() => widthOf(page, "#drawer")).toBeLessThanOrEqual(801);
    await drag(page, "#split-panels", -1000, 0);
    await expect.poll(() => widthOf(page, "#view-left")).toBeGreaterThanOrEqual(120);
    await drag(page, "#split-panels", 2000, 0);
    await expect.poll(() => widthOf(page, "#view-right")).toBeGreaterThanOrEqual(120);
    expect(await tooltipOnLeftGrid(page)).toBe(true);
    await page.screenshot({ path: `${SHOTS}/drawer-max-1440.png` });
  });

  test("shrinking the window re-clamps a wide drawer so the grids stay usable", async ({ page }) => {
    await ready(page);
    await page.locator("#split-drawer").focus();
    await page.keyboard.press("End");
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(800, 0);

    await page.setViewportSize({ width: 1100, height: 700 });
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(460, 0);
    await expect.poll(() => widthOf(page, "#stage")).toBeGreaterThanOrEqual(630);
    await stageUsable(page);
    const handle = await boxOf(page, "#split-drawer");
    expect(handle.x).toBeGreaterThan(0);
    expect(handle.x + handle.width).toBeLessThanOrEqual(1100);
    await page.locator("#split-drawer").dblclick();
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(460, 0);
    expect(await widthOf(page, "#view-left")).toBeGreaterThanOrEqual(120);

    await page.locator("#split-drawer").focus();
    await page.keyboard.press("Home");
    await page.keyboard.press("End");
    await page.setViewportSize({ width: 900, height: 700 });
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(300, 0);
    await page.locator("#split-drawer").focus();
    await page.keyboard.press("End");
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(300, 0);
    await expect.poll(() => widthOf(page, "#stage")).toBeGreaterThanOrEqual(580);
    await stageUsable(page);
    expect(await widthOf(page, "#view-left")).toBeGreaterThanOrEqual(100);
    expect(await widthOf(page, "#view-right")).toBeGreaterThanOrEqual(100);
    await page.locator("#split-drawer").dblclick();
    await expect.poll(() => widthOf(page, "#drawer")).toBeCloseTo(300, 0);
    expect(await widthOf(page, "#view-left")).toBeGreaterThanOrEqual(100);
    await page.screenshot({ path: `${SHOTS}/drawer-max-900.png` });
  });
});

test.describe("fixture plain words and collapsible technical detail", () => {
  test("About shows plain lines, every details closed, and the verbatim S2 one click away", async ({ page, request }) => {
    const cat = (await (await request.get("/replay-fixture/EFIX/catalog.json")).json()) as FixtureCatalog;
    await ready(page);
    await page.getByRole("button", { name: "About this data" }).click();
    const about = page.locator('#drawer [data-pane="info"]');
    await expect(about.locator(".about-plain")).toHaveCount(5);
    for (const plain of await about.locator(".about-plain").all()) await expect(plain).toBeVisible();
    const details = about.locator("details");
    expect(await details.count()).toBe(5);
    expect(await details.evaluateAll((all) => all.map((d) => (d as HTMLDetailsElement).open))).toEqual([false, false, false, false, false]);
    await expect(about.locator(".about-s2")).toBeHidden();

    await about.locator("details").first().locator("summary").click();
    await expect(about.locator("details").first()).toHaveAttribute("open", "");
    await expect(about.locator(".about-s2")).toBeVisible();
    await expect(about.locator(".about-s2")).toHaveText(cat.strings.s2);
    expect(await details.evaluateAll((all) => all.filter((d) => (d as HTMLDetailsElement).open).length)).toBe(1);
    await page.screenshot({ path: `${SHOTS}/about-expanded.png` });
  });

  test("Why? at the burst tick shows the callout plain line with a collapsed technical detail", async ({ page, request }) => {
    const cat = (await (await request.get("/replay-fixture/EFIX/catalog.json")).json()) as FixtureCatalog;
    await ready(page, "&t=3610");
    await page.getByRole("button", { name: "Why?" }).click();
    const callout = page.locator('#drawer [data-pane="why"] .why-precision-callout');
    await expect(callout).toBeVisible();
    await expect(callout.locator(".why-precision-plain")).toBeVisible();
    await expect(callout.locator("details")).not.toHaveAttribute("open", "");
    await expect(callout.locator(".why-precision")).toBeHidden();
    await callout.locator("summary").click();
    await expect(callout.locator(".why-precision")).toHaveText(cat.strings.precision_note);
  });
});
