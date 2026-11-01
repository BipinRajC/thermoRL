import { expect, test } from "vitest";
import * as THREE from "three";
import { RackGrid, cellOf, pointerToNorm, rackAt } from "../../src/scene/rackGrid";
import type { Catalog } from "../../src/schema/replay";

const grid: Catalog["grid"] = {
  rows: 13,
  cols: 20,
  n_racks: 257,
  nodes_per_rack: 4,
  mapping: "row = r // 20, col = r % 20",
  schematic_not_floor_plan: true,
};

const centre = (row: number, col: number): [number, number] => [(col + 0.5) / grid.cols, (row + 0.5) / grid.rows];

test("cellOf is unique over 257 racks and cellOf(256) is row 12, col 16", () => {
  const seen = new Set<string>();
  for (let r = 0; r < grid.n_racks; r++) {
    const { row, col } = cellOf(r, grid.cols);
    seen.add(`${row},${col}`);
  }
  expect(seen.size).toBe(257);
  expect(cellOf(256, grid.cols)).toEqual({ row: 12, col: 16 });
});

test("tile mesh has 257 instances at 257 distinct (x, y) positions", () => {
  const g = new RackGrid(grid);
  expect(g.tiles.count).toBe(257);
  const m = new THREE.Matrix4();
  const p = new THREE.Vector3();
  const seen = new Set<string>();
  for (let i = 0; i < g.tiles.count; i++) {
    g.tiles.getMatrixAt(i, m);
    p.setFromMatrixPosition(m);
    seen.add(`${p.x},${p.y}`);
  }
  expect(seen.size).toBe(257);
  g.dispose();
});

test("empty cells are drawn as 3 outlines", () => {
  const g = new RackGrid(grid);
  expect(g.emptyOutlineCount).toBe(3);
  g.dispose();
});

test("rackAt hits tile centres and misses gaps, empty cells and outside", () => {
  expect(rackAt(...centre(0, 0), grid)).toBe(0);
  expect(rackAt(...centre(12, 16), grid)).toBe(256);
  expect(rackAt(...centre(12, 17), grid)).toBeNull();
  expect(rackAt(1 / grid.cols, 0.5 / grid.rows, grid)).toBeNull();
  expect(rackAt(-0.01, 0.5, grid)).toBeNull();
  expect(rackAt(0.5, 1.01, grid)).toBeNull();
});

test("setPulses sets the ring count", () => {
  const g = new RackGrid(grid);
  expect(g.rings.count).toBe(0);
  g.setPulses(new Set([1, 5]));
  expect(g.rings.count).toBe(2);
  g.dispose();
});

test("pointerToNorm maps the viewport centre and fitted extent back to rackAt coordinates", () => {
  const rect = { left: 10, top: 20, width: 1000, height: 500 };
  const mid = pointerToNorm(510, 270, rect, grid);
  expect(mid.x).toBeCloseTo(0.5, 6);
  expect(mid.y).toBeCloseTo(0.5, 6);
  const f = 1000 / 500;
  const halfH = (13 * 1.08) / 2;
  const halfW = halfH * f;
  const px = 10 + 500 + ((0 - 9.5 + 0.5 * 0) / halfW) * 500;
  const py = 20 + 250 - ((0 - 6) / halfH) * 250;
  expect(rackAt(pointerToNorm(px, py, rect, grid).x, pointerToNorm(px, py, rect, grid).y, grid)).toBe(0);
});
