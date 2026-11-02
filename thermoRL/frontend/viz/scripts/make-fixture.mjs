import { mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildFixture } from "../tests/fixture/buildFixture.ts";

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "replay-fixture");
await rm(out, { recursive: true, force: true });
const files = await buildFixture();
for (const [rel, bytes] of files) {
  const dest = join(out, rel);
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, bytes);
}
console.log(`wrote ${files.size} files to ${out}`);
