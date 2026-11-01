import * as THREE from "three";
import { fitFrustum, type RackGrid } from "./rackGrid";

export class DualView {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly canvas: HTMLCanvasElement;
  private readonly scenes = new WeakMap<RackGrid, THREE.Scene>();
  private readonly camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x0b0d12, 1);
    this.renderer.autoClear = false;
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.camera.position.set(0, 0, 10);
    this.resize();
  }

  static webglAvailable(): boolean {
    try {
      const c = document.createElement("canvas");
      if (typeof c.getContext !== "function") return false;
      return Boolean(c.getContext("webgl2") ?? c.getContext("webgl"));
    } catch {
      return false;
    }
  }

  resize(): void {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
  }

  render(left: RackGrid, right: RackGrid, leftEl: HTMLElement, rightEl: HTMLElement): void {
    const r = this.renderer;
    r.setScissorTest(false);
    r.clear(true, true, true);
    r.setScissorTest(true);
    for (const [grid, el] of [
      [left, leftEl],
      [right, rightEl],
    ] as const) {
      const canvasRect = this.canvas.getBoundingClientRect();
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) continue;
      const x = rect.left - canvasRect.left;
      const y = canvasRect.bottom - rect.bottom;
      r.setViewport(x, y, rect.width, rect.height);
      r.setScissor(x, y, rect.width, rect.height);
      this.fit(grid.grid, rect.width / rect.height);
      r.clearDepth();
      r.render(this.sceneFor(grid), this.camera);
    }
  }

  private fit(grid: RackGrid["grid"], aspect: number): void {
    const f = fitFrustum(grid, aspect);
    const c = this.camera;
    c.left = f.cx - f.halfW;
    c.right = f.cx + f.halfW;
    c.top = f.cy + f.halfH;
    c.bottom = f.cy - f.halfH;
    c.position.set(0, 0, 10);
    c.updateProjectionMatrix();
  }

  private sceneFor(grid: RackGrid): THREE.Scene {
    let s = this.scenes.get(grid);
    if (!s) {
      s = new THREE.Scene();
      s.add(grid.group);
      this.scenes.set(grid, s);
    }
    return s;
  }
}
