import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import os from "node:os";
import { dirname } from "node:path";

const args = process.argv.slice(2);
const flag = (name) => args.includes(`--${name}`);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const BASE = opt("base", "http://localhost:4173");
const SECONDS = Number(opt("seconds", "30"));
const LOADS = Number(opt("loads", "5"));
const OUT = opt("out", "test-artifacts/perf-check.json");
const HEADED = flag("headed");
const ENTRY = `${BASE}/?data=replay&exp=E12_g4_alibaba&seed=1&cmp=pb_vs_tp`;

const launch = async () => {
  const launchArgs = ["--ignore-gpu-blocklist", "--enable-precise-memory-info"];
  try {
    return { browser: await chromium.launch({ channel: "chrome", headless: !HEADED, args: launchArgs }), channel: "Google Chrome (channel: chrome)" };
  } catch (e) {
    return { browser: await chromium.launch({ headless: !HEADED, args: launchArgs }), channel: `Playwright Chromium (Google Chrome unavailable: ${String(e.message).split("\n")[0]})` };
  }
};

const FIRST_RENDER_PROBE = () => {
  window.__firstRender = null;
  let armed = false;
  const tick = () => {
    if (window.__firstRender === null) {
      const stage = document.getElementById("stage");
      const status = document.getElementById("status");
      const legend = document.querySelector("#legend-left .legend-max");
      if (armed) window.__firstRender = performance.now();
      else if (stage?.dataset.state === "ready" && status?.hidden && legend) armed = true;
      requestAnimationFrame(tick);
    }
  };
  requestAnimationFrame(tick);
};

const waitReady = (page) =>
  page.waitForFunction(() => document.getElementById("stage")?.dataset.state === "ready" && document.getElementById("status")?.hidden === true);

const rendererRssMb = (marker) => {
  try {
    const rows = execFileSync("ps", ["-axo", "rss=,command="], { encoding: "utf8" }).split("\n");
    const kb = rows.filter((r) => r.includes("--type=renderer") && r.includes(marker)).reduce((s, r) => s + Number(r.trim().split(/\s+/)[0]), 0);
    return kb ? Math.round(kb / 1024) : null;
  } catch {
    return null;
  }
};

const result = { base: BASE, headed: HEADED, seconds: SECONDS, started_utc: new Date().toISOString() };
const { browser, channel } = await launch();
result.browser = channel;
const sysctl = (key) => {
  try {
    return execFileSync("sysctl", ["-n", key], { encoding: "utf8" }).trim();
  } catch {
    return null;
  }
};
result.host = { model: sysctl("hw.model"), cpu: os.cpus()[0]?.model ?? null, arch: os.arch(), platform: os.platform(), release: os.release(), node: process.version };
result.browser_version = browser.version();

result.first_render_ms = [];
for (let i = 0; i < LOADS; i++) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.addInitScript(FIRST_RENDER_PROBE);
  await page.goto(ENTRY);
  await page.waitForFunction(() => window.__firstRender !== null);
  result.first_render_ms.push(Math.round(await page.evaluate(() => window.__firstRender)));
  await context.close();
}

const fps = async (speed) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.goto(ENTRY);
  await waitReady(page);
  await page.locator("#scrubber").fill("0");
  await page.locator("#sel-speed").selectOption(String(speed));
  await page.evaluate(() => {
    window.__inputs = [];
    for (const t of ["keydown", "pointerdown", "click", "input", "wheel"]) window.addEventListener(t, (e) => window.__inputs.push(`${t}:${e.target?.id || e.target?.tagName}@${Math.round(performance.now())}`), true);
  });
  await page.getByRole("button", { name: "Play" }).click();
  const stats = await page.evaluate(
    (ms) =>
      new Promise((resolve) => {
        const stamps = [];
        const heap = [];
        const start = performance.now();
        const startTick = Number(/tick (\d+)\//.exec(document.getElementById("clock").textContent)[1]);
        const ticks = [];
        const heapTimer = setInterval(() => {
          heap.push(performance.memory.usedJSHeapSize);
          ticks.push(Number(/tick (\d+)\//.exec(document.getElementById("clock").textContent)[1]));
        }, 1000);
        const step = (now) => {
          stamps.push(now);
          if (now - start < ms) requestAnimationFrame(step);
          else {
            clearInterval(heapTimer);
            const gaps = stamps.slice(1).map((t, i) => t - stamps[i]).sort((a, b) => a - b);
            const elapsed = (stamps[stamps.length - 1] - stamps[0]) / 1000;
            resolve({
              frames: stamps.length,
              elapsed_s: elapsed,
              fps_mean: (stamps.length - 1) / elapsed,
              frame_ms_p50: gaps[Math.floor(gaps.length * 0.5)],
              frame_ms_p99: gaps[Math.floor(gaps.length * 0.99)],
              frame_ms_max: gaps[gaps.length - 1],
              frames_over_33ms: gaps.filter((g) => g > 33.4).length,
              start_tick: startTick,
              end_tick: Number(/tick (\d+)\//.exec(document.getElementById("clock").textContent)[1]),
              heap_max_mb_during: Math.max(...heap) / 1048576,
              tick_each_second: ticks,
              visibility: document.visibilityState,
              inputs_seen_after_play: window.__inputs.slice(1),
            });
          }
        };
        requestAnimationFrame(step);
      }),
    SECONDS * 1000,
  );
  await context.close();
  stats.expected_end_tick = Math.round(speed * SECONDS);
  stats.playback_rate_ok = Math.abs(stats.end_tick - stats.expected_end_tick) <= 0.05 * stats.expected_end_tick + 1;
  stats.tick_each_second = stats.tick_each_second.join(",");
  for (const k of Object.keys(stats)) if (typeof stats[k] === "number") stats[k] = Math.round(stats[k] * 100) / 100;
  return stats;
};
result.fps = { speed_10: await fps(10), speed_60: await fps(60) };

const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
const heap = async (label) => {
  const used = (await cdp.send("Runtime.getHeapUsage")).usedSize;
  await cdp.send("HeapProfiler.collectGarbage");
  const afterGc = (await cdp.send("Runtime.getHeapUsage")).usedSize;
  return { label, used_js_heap_mb: Math.round((used / 1048576) * 10) / 10, after_gc_mb: Math.round((afterGc / 1048576) * 10) / 10, renderer_rss_mb: rendererRssMb("playwright") };
};
result.heap = [];
await page.goto("about:blank");
result.webgl = await page.evaluate(() => {
  const gl = document.createElement("canvas").getContext("webgl2") ?? document.createElement("canvas").getContext("webgl");
  const info = gl?.getExtension("WEBGL_debug_renderer_info");
  return {
    context: gl ? (typeof WebGL2RenderingContext !== "undefined" && gl instanceof WebGL2RenderingContext ? "webgl2" : "webgl") : null,
    renderer: gl && info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : null,
    vendor: gl && info ? gl.getParameter(info.UNMASKED_VENDOR_WEBGL) : null,
  };
});
result.heap.push(await heap("about:blank baseline"));
await page.goto(ENTRY);
await waitReady(page);
result.heap.push(await heap("E12 seed 1 pb_vs_tp"));
await page.locator("#sel-cmp").selectOption("packing_vs_tp");
await page.waitForFunction(() => document.getElementById("title-left")?.textContent === "packing" && document.getElementById("stage")?.dataset.state === "ready");
result.heap.push(await heap("E12 seed 1 packing_vs_tp"));
await page.locator("#sel-exp").selectOption("E11_g4_synthetic");
await page.waitForFunction(() => document.getElementById("identity")?.textContent?.includes("Synthetic") && document.getElementById("stage")?.dataset.state === "ready" && document.getElementById("status")?.hidden === true);
result.heap.push(await heap("E11 seed 1 pb_vs_tp"));
await context.close();
await browser.close();

result.targets = {
  first_render_max_ms: 5000,
  fps_min: 50,
  heap_max_mb: 400,
};
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];
result.summary = {
  first_render_median_ms: median(result.first_render_ms),
  first_render_max_ms: Math.max(...result.first_render_ms),
  fps_speed_10: result.fps.speed_10.fps_mean,
  fps_speed_60: result.fps.speed_60.fps_mean,
  heap_final_mb: result.heap[result.heap.length - 1].used_js_heap_mb,
  heap_final_after_gc_mb: result.heap[result.heap.length - 1].after_gc_mb,
};
result.met = {
  first_render: result.summary.first_render_max_ms <= result.targets.first_render_max_ms,
  fps: Math.min(result.summary.fps_speed_10, result.summary.fps_speed_60) >= result.targets.fps_min && result.fps.speed_10.playback_rate_ok && result.fps.speed_60.playback_rate_ok,
  heap: result.summary.heap_final_mb <= result.targets.heap_max_mb,
};
result.met_notes = {
  heap: "met on the JS-heap definition (Runtime.getHeapUsage); renderer RSS growth is reported separately in heap[].renderer_rss_mb and is not the target quantity",
};
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result, null, 2));
