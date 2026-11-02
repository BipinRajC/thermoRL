import { expect, test, type Page } from "@playwright/test";
import { scanText } from "../support/forbidden";

const DATA = "/replay/E12_g4_alibaba";
const URL = "/?data=replay&exp=E12_g4_alibaba&seed=1";
const SHOTS = "test-artifacts";

interface Catalog {
  strings: { precision_note: string };
}

async function frames(page: Page, n = 2): Promise<void> {
  await page.evaluate(
    (count) =>
      new Promise<void>((resolve) => {
        const step = (left: number) => (left ? requestAnimationFrame(() => step(left - 1)) : resolve());
        step(count);
      }),
    n,
  );
}

async function ready(page: Page, query = ""): Promise<void> {
  await page.goto(`${URL}${query}`);
  await expect(page.locator("#stage")).toHaveAttribute("data-state", "ready");
  await expect(page.locator("#status")).toBeHidden();
  await expect(page.locator("#legend-left .legend-max")).toBeVisible();
  await frames(page);
}

async function seek(page: Page, tick: number): Promise<void> {
  await page.locator("#scrubber").fill(String(tick));
  await expect(page.locator("#clock")).toContainText(`tick ${tick}/2160`);
  await frames(page);
}

const clock = (page: Page) => page.locator("#clock");

test.describe("real hash-verified E12 export", () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.get("/replay/index.json");
    const body = res.ok() ? await res.text() : "";
    let ok = false;
    try {
      ok = (JSON.parse(body) as { schema?: string }).schema === "thermorl.replay.v1";
    } catch {
      ok = false;
    }
    if (!ok) throw new Error(`Real replay data is missing: /replay/index.json (HTTP ${res.status()}) is not a thermorl.replay.v1 index. Run \`npm run sync-replay\` first.`);
  });

  test("title, verbatim headline and legend on seed 1", async ({ page }) => {
    await ready(page, "&cmp=pb_vs_tp");
    await expect(page.locator("#app-title")).toHaveText("ThermoRL — closed-loop FMU replay");
    const outcome = (await (await page.request.get(`${DATA}/frozen_outcome.json`)).json()) as { headline: string; rule: string; experiment_statement: string };
    await expect(page.locator("#drawer .outcome-headline")).toHaveText(outcome.headline);
    await expect(page.locator("#drawer .outcome-rule")).toHaveText(outcome.rule);
    await expect(page.locator("#drawer .outcome-statement")).toHaveText(outcome.experiment_statement);
    for (const side of ["left", "right"]) {
      await expect(page.locator(`#legend-${side} .legend-max`)).toHaveText("42.41 °C");
      await expect(page.locator(`#legend-${side} .legend-min`)).toHaveText("38.70 °C");
    }
    await expect(page.locator("#identity")).toContainText("seed 1 of 3");
    await expect(page.locator("canvas#gl")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/real-default.png` });
  });

  test("outcome card lists all five policies and the per-seed gaps", async ({ page }) => {
    await ready(page, "&cmp=pb_vs_tp");
    const gaps = await page.locator("#drawer .outcome-gaps tbody tr").evaluateAll((rows) => rows.map((r) => Array.from(r.children).map((c) => c.textContent?.trim())));
    expect(gaps).toEqual([
      ["1", "0.178", "0.353"],
      ["2", "0.077", "0.441"],
      ["3", "0.109", "0.423"],
    ]);
    const policies = await page.locator("#drawer .outcome-metrics tbody th").allInnerTexts();
    expect(policies).toEqual(["packing", "node_balance", "power_balance", "coolest_rack", "thermal_predictive"]);
    await expect(page.locator("#drawer .outcome-metrics tbody td")).toHaveCount(15);
  });

  test("the C′ badge appears only on thermal_predictive seed 1", async ({ page }) => {
    for (const seed of [1, 2, 3]) {
      for (const cmp of ["pb_vs_tp", "packing_vs_tp"]) {
        await page.goto(`/?data=replay&exp=E12_g4_alibaba&seed=${seed}&cmp=${cmp}`);
        await expect(page.locator("#stage")).toHaveAttribute("data-state", "ready");
        await expect(page.locator("#title-right")).toHaveText("thermal_predictive");
        const verifiedExpected = seed === 1;
        await expect(page.locator("#badge-left")).toHaveText(/not directly repeated/);
        await expect(page.locator("#badge-left")).not.toHaveClass(/verified/);
        await expect(page.locator("#badge-right")).toHaveText(verifiedExpected ? /C′ verified/ : /not directly repeated/);
        if (verifiedExpected) await expect(page.locator("#badge-right")).toHaveClass(/verified/);
        else await expect(page.locator("#badge-right")).not.toHaveClass(/verified/);
      }
    }
  });

  test("evaluation window label flips between 3600 s and 3610 s", async ({ page }) => {
    await ready(page, "&cmp=pb_vs_tp&t=3600");
    await expect(clock(page)).toContainText("01:00:00");
    await expect(clock(page)).toContainText("tick 359/2160");
    await expect(clock(page)).toContainText("before evaluation window");
    await page.getByRole("button", { name: "+1 tick" }).click();
    await expect(clock(page)).toContainText("01:00:10");
    await expect(clock(page)).toContainText("tick 360/2160");
    await expect(clock(page)).toContainText(/(?<!before )evaluation window/);
    await expect(clock(page)).not.toContainText("before evaluation window");
  });

  test("no racks fall outside the scale at the hottest packing sample", async ({ page }) => {
    const tick = Buffer.from(await (await page.request.get(`${DATA}/runs/packing_seed1/tick.f64`)).body());
    const values = new Float64Array(tick.buffer.slice(tick.byteOffset, tick.byteOffset + tick.byteLength));
    let hot = 0;
    for (let k = 1; k < 2160; k++) if (values[k * 8 + 4] > values[hot * 8 + 4]) hot = k;
    await ready(page, "&cmp=packing_vs_tp");
    await seek(page, hot);
    await expect(page.locator("#legend-left .legend-out")).toHaveCount(0);
    await expect(page.locator("#legend-right .legend-out")).toHaveCount(0);
  });

  test("Why? drawer at a job-start burst pages 50 and shows at most six candidates", async ({ page, request }) => {
    const cat = (await (await request.get(`${DATA}/catalog.json`)).json()) as Catalog;
    const decisions = (await (await request.get(`${DATA}/runs/power_balance_seed1/decisions.json`)).json()) as { raps_t_s: number[] };
    const inWindow = decisions.raps_t_s.filter((t) => t > 6920 && t <= 6950).length;
    expect(inWindow).toBeGreaterThan(100);

    await ready(page, "&cmp=pb_vs_tp&t=6950");
    await expect(clock(page)).toContainText("tick 694/2160");
    await page.getByRole("button", { name: "Why?" }).click();
    const why = page.locator('#drawer [data-pane="why"]');
    await expect(why.locator(".why-precision-plain")).toBeVisible();
    await expect(why.locator(".why-precision")).toBeHidden();
    await why.getByText("Technical detail").click();
    await expect(why.locator(".why-precision")).toBeVisible();
    await expect(why.locator(".why-precision")).toHaveText(cat.strings.precision_note);
    await expect(why.locator(".why-count")).toHaveText(`${inWindow} decisions`);
    await expect(why.locator(".why-item")).toHaveCount(50);
    const pages = Math.ceil(inWindow / 50);
    await expect(why.locator(".why-page")).toHaveText(`Page 1 of ${pages} · 1–50 of ${inWindow}`);
    await why.getByRole("button", { name: /next/i }).click();
    await expect(why.locator(".why-page")).toHaveText(`Page 2 of ${pages} · 51–100 of ${inWindow}`);
    await expect(why.locator(".why-item")).toHaveCount(50);
    await why.locator(".why-item-head").first().click();
    const rows = await why.locator(".why-item").first().locator("tbody tr").count();
    expect(rows).toBeGreaterThanOrEqual(1);
    expect(rows).toBeLessThanOrEqual(6);
    await expect(why.locator(".why-precision")).toHaveText(cat.strings.precision_note);
    await page.screenshot({ path: `${SHOTS}/real-burst-why.png` });
  });

  test("the first tick opens the Why? drawer without errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await ready(page, "&cmp=pb_vs_tp&t=10");
    await expect(clock(page)).toContainText("00:00:10 · tick 0/2160");
    await page.getByRole("button", { name: "Why?" }).click();
    await expect(page.locator('#drawer [data-pane="why"] .why-header')).toContainText("00:00:10");
    await frames(page, 3);
    expect(errors).toEqual([]);
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
      expect(scanText(await page.evaluate(() => document.body.innerText)), name).toEqual([]);
    }
    for (const name of ["Rack kW", "Occupied", "Coolant °C"]) {
      await page.getByRole("button", { name }).click();
      expect(scanText(await page.evaluate(() => document.body.innerText)), name).toEqual([]);
    }
  });
});
