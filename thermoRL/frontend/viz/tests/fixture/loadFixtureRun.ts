import type { Catalog } from "../../src/schema/replay";
import { loadRun, type Fetcher, type LoadedRun } from "../../src/data/loader";
import { buildFixture } from "./buildFixture";

const BASE = "replay-fixture";

export const fixtureFetcher =
  (files: Map<string, Uint8Array>): Fetcher =>
  async (url) => {
    const bytes = files.get(url.startsWith(`${BASE}/`) ? url.slice(BASE.length + 1) : url);
    return bytes ? new Response(bytes as BodyInit) : new Response(null, { status: 404 });
  };

export async function loadFixtureRun(policy = "packing", seed = 1): Promise<{ run: LoadedRun; cat: Catalog }> {
  const files = await buildFixture();
  const f = fixtureFetcher(files);
  const run = await loadRun(BASE, "EFIX", `runs/${policy}_seed${seed}/run.json`, f);
  const cat = JSON.parse(new TextDecoder().decode(files.get("EFIX/catalog.json")!)) as Catalog;
  return { run, cat };
}
