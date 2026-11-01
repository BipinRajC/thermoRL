import * as THREE from "three";
import type { Catalog } from "../schema/replay";

type Grid = Catalog["grid"];

const TILE = 0.88;
const HALF_TILE = TILE / 2;
const PAD = 0.04;
const PULSE_COLOUR = [0x22 / 255, 0xd3 / 255, 0xee / 255] as const;
const EMPTY_COLOUR = 0x475569;
const OUTLINE_HALF = 0.47;

export function cellOf(r: number, cols: number): { row: number; col: number } {
  return { row: Math.floor(r / cols), col: r % cols };
}

export function rackAt(xNorm: number, yNorm: number, grid: Grid): number | null {
  if (!(xNorm >= 0 && xNorm < 1 && yNorm >= 0 && yNorm < 1)) return null;
  const cx = xNorm * grid.cols;
  const cy = yNorm * grid.rows;
  const col = Math.floor(cx);
  const row = Math.floor(cy);
  if (Math.abs(cx - col - 0.5) > HALF_TILE || Math.abs(cy - row - 0.5) > HALF_TILE) return null;
  const r = row * grid.cols + col;
  return r < grid.n_racks ? r : null;
}

export function fitFrustum(grid: Grid, aspect: number): { cx: number; cy: number; halfW: number; halfH: number } {
  const w = grid.cols * (1 + 2 * PAD);
  const h = grid.rows * (1 + 2 * PAD);
  const [halfW, halfH] = w / h > aspect ? [w / 2, w / aspect / 2] : [(h * aspect) / 2, h / 2];
  return { cx: (grid.cols - 1) / 2, cy: (grid.rows - 1) / 2, halfW, halfH };
}

export function pointerToNorm(
  clientX: number,
  clientY: number,
  rect: { left: number; top: number; width: number; height: number },
  grid: Grid,
): { x: number; y: number } {
  const f = fitFrustum(grid, rect.width / rect.height);
  const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
  const ny = 1 - ((clientY - rect.top) / rect.height) * 2;
  return {
    x: (f.cx + nx * f.halfW + 0.5) / grid.cols,
    y: (f.cy + ny * f.halfH + 0.5) / grid.rows,
  };
}

function squareSegments(cells: Array<[number, number]>, half: number): Float32Array {
  const out = new Float32Array(cells.length * 8 * 3);
  let o = 0;
  const put = (x: number, y: number) => {
    out[o++] = x;
    out[o++] = y;
    out[o++] = 0;
  };
  for (const [x, y] of cells) {
    const c: Array<[number, number]> = [
      [x - half, y - half],
      [x + half, y - half],
      [x + half, y + half],
      [x - half, y + half],
    ];
    for (let i = 0; i < 4; i++) {
      put(...c[i]);
      put(...c[(i + 1) % 4]);
    }
  }
  return out;
}

export class RackGrid {
  readonly group = new THREE.Group();
  readonly tiles: THREE.InstancedMesh;
  readonly rings: THREE.InstancedMesh;
  readonly emptyOutlineCount: number;
  private readonly nRacks: number;
  private readonly cols: number;
  private readonly pinned: THREE.LineSegments;
  private readonly hover: THREE.LineSegments;
  private readonly emptyLines: THREE.LineSegments;
  private readonly colours: Float32Array;
  private readonly dummy = new THREE.Object3D();

  constructor(readonly grid: Grid) {
    this.nRacks = grid.n_racks;
    this.cols = grid.cols;
    this.colours = new Float32Array(grid.n_racks * 3).fill(0.28);

    this.tiles = new THREE.InstancedMesh(
      new THREE.PlaneGeometry(TILE, TILE),
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
      grid.n_racks,
    );
    this.tiles.instanceColor = new THREE.InstancedBufferAttribute(this.colours, 3);
    for (let r = 0; r < grid.n_racks; r++) {
      const { row, col } = cellOf(r, grid.cols);
      this.dummy.position.set(col, row, 0);
      this.dummy.updateMatrix();
      this.tiles.setMatrixAt(r, this.dummy.matrix);
    }
    this.tiles.instanceMatrix.needsUpdate = true;
    this.tiles.instanceColor.needsUpdate = true;
    this.tiles.frustumCulled = false;

    const empty: Array<[number, number]> = [];
    for (let r = grid.n_racks; r < grid.rows * grid.cols; r++) {
      const { row, col } = cellOf(r, grid.cols);
      empty.push([col, row]);
    }
    this.emptyOutlineCount = empty.length;
    const emptyGeo = new THREE.BufferGeometry();
    emptyGeo.setAttribute("position", new THREE.BufferAttribute(squareSegments(empty, HALF_TILE), 3));
    this.emptyLines = new THREE.LineSegments(emptyGeo, new THREE.LineBasicMaterial({ color: EMPTY_COLOUR }));
    this.emptyLines.frustumCulled = false;

    const ringMat = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
    ringMat.color.setRGB(...PULSE_COLOUR, THREE.LinearSRGBColorSpace);
    this.rings = new THREE.InstancedMesh(new THREE.RingGeometry(0.3, 0.4, 32), ringMat, grid.n_racks);
    this.rings.count = 0;
    this.rings.position.z = 0.01;
    this.rings.frustumCulled = false;

    this.pinned = this.makeOutline();
    this.hover = this.makeOutline();

    this.group.add(this.tiles, this.emptyLines, this.rings, this.hover, this.pinned);
  }

  private makeOutline(): THREE.LineSegments {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(squareSegments([[0, 0]], OUTLINE_HALF), 3));
    const mat = new THREE.LineBasicMaterial({ depthTest: false });
    mat.color.setRGB(1, 1, 1, THREE.LinearSRGBColorSpace);
    const line = new THREE.LineSegments(geo, mat);
    line.visible = false;
    line.position.z = 0.02;
    line.renderOrder = 1;
    line.frustumCulled = false;
    return line;
  }

  setColours(rgb: Float32Array): void {
    if (rgb.length !== this.nRacks * 3) {
      throw new Error(`setColours expects ${this.nRacks * 3} floats, got ${rgb.length}`);
    }
    this.colours.set(rgb);
    this.tiles.instanceColor!.needsUpdate = true;
  }

  setPulses(racks: Set<number>): void {
    let n = 0;
    for (const r of racks) {
      if (r < 0 || r >= this.nRacks) continue;
      const { row, col } = cellOf(r, this.cols);
      this.dummy.position.set(col, row, 0);
      this.dummy.updateMatrix();
      this.rings.setMatrixAt(n++, this.dummy.matrix);
    }
    this.rings.count = n;
    this.rings.instanceMatrix.needsUpdate = true;
  }

  setPinned(r: number | null): void {
    this.place(this.pinned, r);
  }

  setHover(r: number | null): void {
    this.place(this.hover, r);
  }

  private place(line: THREE.LineSegments, r: number | null): void {
    if (r === null || r < 0 || r >= this.nRacks) {
      line.visible = false;
      return;
    }
    const { row, col } = cellOf(r, this.cols);
    line.position.set(col, row, line.position.z);
    line.visible = true;
  }

  dispose(): void {
    this.group.traverse((o) => {
      const m = o as THREE.Mesh;
      m.geometry?.dispose();
      (m.material as THREE.Material | undefined)?.dispose();
    });
    this.tiles.dispose();
    this.rings.dispose();
  }
}
