import * as THREE from "three";
import type { VizFrame } from "../schema/vizevent";

const ZONES = 3;
const RACKS = 16;
const COLS = 4;
const ROWS = 4;
const ZONE_PITCH = 3.2;
const PAD_W = 3.0;
const PAD_D = 6.6;
const CAB_W = 0.58;
const CAB_H = 1.72;
const CAB_D = 0.7;
const COL_PITCH = 0.68;
const ROW_PITCH = 1.45;
const FRUSTUM_PAD = 0.022;
const ZONE_NAMES = ["Z1 Air", "Z2 D2C", "Z3 Immersion"];
const ZONE_PAD = [0x2c4568, 0x1f5a50, 0x34386a];
const ZONE_ACCENT = [0x60a5fa, 0x22d3ee, 0x14b8a6];

function applyColor(hex: string | undefined, out: THREE.Color): THREE.Color {
  if (hex) {
    out.set(hex);
    return out;
  }
  out.setRGB(0.28, 0.3, 0.34);
  return out;
}

function labelSprite(title: string, subtitle: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 640;
  canvas.height = 192;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "rgba(5, 8, 22, 0.92)";
  ctx.fillRect(12, 14, 616, 164);
  ctx.strokeStyle = "rgba(148, 163, 184, 0.7)";
  ctx.lineWidth = 4;
  ctx.strokeRect(12, 14, 616, 164);
  ctx.fillStyle = "#f8fafc";
  ctx.font = "800 44px ui-sans-serif, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(title, 320, 78);
  ctx.fillStyle = "#94a3b8";
  ctx.font = "600 24px ui-sans-serif, system-ui, sans-serif";
  ctx.fillText(subtitle, 320, 132);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(2.45, 0.74, 1);
  sprite.renderOrder = 2;
  return sprite;
}

export class RackPanel {
  scene: THREE.Scene;
  camera: THREE.OrthographicCamera;
  mesh: THREE.InstancedMesh;
  frontMesh: THREE.InstancedMesh;
  pads: THREE.Mesh[] = [];
  labels: THREE.Sprite[] = [];
  padBase = ZONE_PAD.map((hex) => new THREE.Color(hex));
  dummy = new THREE.Object3D();
  color = new THREE.Color();
  work = new THREE.Color();
  contentMin = new THREE.Vector3();
  contentMax = new THREE.Vector3();
  private scratch = new THREE.Vector3();
  private pulseColor = new THREE.Color();

  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x050816);

    this.camera = new THREE.OrthographicCamera(-8, 8, 5, -5, 0.1, 80);
    this.camera.up.set(0, 1, 0);

    const slabW = ZONE_PITCH * 3 + 0.2;
    const slab = new THREE.Mesh(
      new THREE.BoxGeometry(slabW, 0.1, PAD_D + 1.35),
      new THREE.MeshLambertMaterial({ color: 0x101a2c }),
    );
    slab.position.set(0, -0.16, 0);
    this.scene.add(slab);

    const grid = new THREE.GridHelper(slabW, 24, 0x36516a, 0x1b2b3f);
    const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material];
    for (const material of gridMaterials) {
      material.transparent = true;
      material.opacity = 0.48;
    }
    grid.position.set(0, -0.095, 0);
    this.scene.add(grid);

    const hallSpine = new THREE.Mesh(
      new THREE.BoxGeometry(slabW - 0.4, 0.018, 0.12),
      new THREE.MeshBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.65 }),
    );
    hallSpine.position.set(0, 0.035, 0);
    this.scene.add(hallSpine);

    this.scene.add(new THREE.AmbientLight(0xb7c4dc, 0.95));
    const key = new THREE.DirectionalLight(0xffffff, 1.35);
    key.position.set(-3, 16, 5);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0x9eb6e0, 0.45);
    rim.position.set(5, 5, -4);
    this.scene.add(rim);

    for (let z = 0; z < ZONES; z++) {
      const originX = (z - 1) * ZONE_PITCH;
      const pad = new THREE.Mesh(
        new THREE.BoxGeometry(PAD_W, 0.1, PAD_D),
        new THREE.MeshLambertMaterial({ color: ZONE_PAD[z] }),
      );
      pad.position.set(originX, -0.02, 0);
      this.scene.add(pad);
      this.pads.push(pad);

      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(PAD_W, 0.1, PAD_D)),
        new THREE.LineBasicMaterial({ color: ZONE_ACCENT[z], transparent: true, opacity: 0.7 }),
      );
      edge.position.copy(pad.position);
      this.scene.add(edge);

      const label = labelSprite(
        ZONE_NAMES[z].toUpperCase(),
        z === 0 ? "AIR / DENSITY GATE" : z === 1 ? "D2C / LIQUID LOOP" : "IMMERSION / TANK ARRAY",
      );
      label.position.set(originX, 2.35, PAD_D * 0.48);
      this.scene.add(label);
      this.labels.push(label);

      this.addZoneIdentity(z, originX);
    }

    const geo = new THREE.BoxGeometry(CAB_W, CAB_H, CAB_D);
    const mat = new THREE.MeshLambertMaterial({ color: 0xffffff });
    this.mesh = new THREE.InstancedMesh(geo, mat, ZONES * RACKS);
    this.scene.add(this.mesh);
    const frontGeo = new THREE.BoxGeometry(CAB_W * 0.78, CAB_H * 0.82, 0.055);
    const frontMat = new THREE.MeshLambertMaterial({ color: 0x334155 });
    this.frontMesh = new THREE.InstancedMesh(frontGeo, frontMat, ZONES * RACKS);
    this.scene.add(this.frontMesh);
    this.layout();
    this.computeContentBounds();
    const cx = (this.contentMin.x + this.contentMax.x) * 0.5;
    const cy = (this.contentMin.y + this.contentMax.y) * 0.5;
    const cz = (this.contentMin.z + this.contentMax.z) * 0.5;
    this.camera.position.set(cx + 2.4, cy + 13.6, cz + 8.2);
    this.camera.lookAt(cx, cy, cz);
  }

  private addZoneIdentity(zone: number, originX: number): void {
    const accent = ZONE_ACCENT[zone];
    if (zone === 0) {
      for (const z of [-2.15, 2.15]) {
        const lane = new THREE.Mesh(
          new THREE.BoxGeometry(PAD_W - 0.24, 0.018, 0.09),
          new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.58 }),
        );
        lane.position.set(originX, 0.08, z);
        this.scene.add(lane);
      }
      const aisle = new THREE.Mesh(
        new THREE.BoxGeometry(PAD_W - 0.32, 0.02, 0.22),
        new THREE.MeshBasicMaterial({ color: 0x93c5fd, transparent: true, opacity: 0.26 }),
      );
      aisle.position.set(originX, 0.085, 0);
      this.scene.add(aisle);
      return;
    }

    if (zone === 1) {
      for (const z of [-2.4, 2.4]) {
        const manifold = new THREE.Mesh(
          new THREE.BoxGeometry(PAD_W - 0.2, 0.07, 0.07),
          new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.9 }),
        );
        manifold.position.set(originX, 0.14, z);
        this.scene.add(manifold);
      }
      for (const x of [-1.05, 1.05]) {
        const connector = new THREE.Mesh(
          new THREE.BoxGeometry(0.06, 0.09, PAD_D - 0.8),
          new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.7 }),
        );
        connector.position.set(originX + x, 0.15, 0);
        this.scene.add(connector);
      }
      return;
    }

    const liquid = new THREE.Mesh(
      new THREE.BoxGeometry(PAD_W - 0.24, 0.035, PAD_D - 0.26),
      new THREE.MeshLambertMaterial({ color: 0x0b5560, transparent: true, opacity: 0.5 }),
    );
    liquid.position.set(originX, 0.075, 0);
    this.scene.add(liquid);
    const tankEdge = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(PAD_W - 0.1, 0.12, PAD_D - 0.14)),
      new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.85 }),
    );
    tankEdge.position.set(originX, 0.12, 0);
    this.scene.add(tankEdge);
  }

  computeContentBounds(): void {
    this.contentMin.set(Infinity, Infinity, Infinity);
    this.contentMax.set(-Infinity, -Infinity, -Infinity);
    const expand = (x: number, y: number, z: number) => {
      this.contentMin.min(this.scratch.set(x, y, z));
      this.contentMax.max(this.scratch.set(x, y, z));
    };
    const slabHalfW = (ZONE_PITCH * 3 + 0.2) * 0.5;
    const slabHalfD = (PAD_D + 1.35) * 0.5;
    expand(-slabHalfW, -0.2, -slabHalfD);
    expand(slabHalfW, CAB_H + 0.15, slabHalfD);
    for (const label of this.labels) {
      expand(label.position.x - 1.15, label.position.y - 0.28, label.position.z);
      expand(label.position.x + 1.15, label.position.y + 0.32, label.position.z);
    }
  }

  fitAspect(aspect: number): void {
    this.camera.updateMatrixWorld(true);
    const inv = this.camera.matrixWorldInverse;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    const xs = [this.contentMin.x, this.contentMax.x];
    const ys = [this.contentMin.y, this.contentMax.y];
    const zs = [this.contentMin.z, this.contentMax.z];
    for (const x of xs) {
      for (const y of ys) {
        for (const z of zs) {
          this.scratch.set(x, y, z).applyMatrix4(inv);
          minX = Math.min(minX, this.scratch.x);
          maxX = Math.max(maxX, this.scratch.x);
          minY = Math.min(minY, this.scratch.y);
          maxY = Math.max(maxY, this.scratch.y);
        }
      }
    }
    const spanX = Math.max(maxX - minX, 0.01);
    const spanY = Math.max(maxY - minY, 0.01);
    let left = minX - spanX * FRUSTUM_PAD;
    let right = maxX + spanX * FRUSTUM_PAD;
    let bottom = minY - spanY * FRUSTUM_PAD;
    let top = maxY + spanY * FRUSTUM_PAD;
    const width = right - left;
    const height = top - bottom;
    if (width / height > aspect) {
      const extra = width / aspect - height;
      bottom -= extra * 0.45;
      top += extra * 0.55;
    } else {
      const extra = height * aspect - width;
      left -= extra * 0.5;
      right += extra * 0.5;
    }
    this.camera.left = left;
    this.camera.right = right;
    this.camera.top = top;
    this.camera.bottom = bottom;
    this.camera.updateProjectionMatrix();
  }

  layout(): void {
    const rowZ = [ROW_PITCH * 0.5, -ROW_PITCH * 0.5];
    for (let z = 0; z < ZONES; z++) {
      const originX = (z - 1) * ZONE_PITCH;
      for (let r = 0; r < RACKS; r++) {
        const i = z * RACKS + r;
        const col = r % COLS;
        const row = Math.floor(r / COLS);
        const x = originX - ((COLS - 1) * COL_PITCH) * 0.5 + col * COL_PITCH;
        this.dummy.position.set(x, CAB_H * 0.5, rowZ[row] ?? 0);
        this.dummy.rotation.set(0, 0, 0);
        this.dummy.scale.set(1, 1, 1);
        this.dummy.updateMatrix();
        this.mesh.setMatrixAt(i, this.dummy.matrix);
        this.mesh.setColorAt(i, this.color.setRGB(0.35, 0.38, 0.42));
        this.dummy.position.z += CAB_D * 0.5 + 0.035;
        this.dummy.position.y = CAB_H * 0.5;
        this.dummy.updateMatrix();
        this.frontMesh.setMatrixAt(i, this.dummy.matrix);
        this.frontMesh.setColorAt(i, this.color.setRGB(0.12, 0.15, 0.2));
      }
    }
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
    this.frontMesh.instanceMatrix.needsUpdate = true;
    if (this.frontMesh.instanceColor) this.frontMesh.instanceColor.needsUpdate = true;
  }

  apply(frame: VizFrame, _p10: number, _p90: number, nowMs = 0): void {
    const placement = frame.events.find((event) => event.type === "place");
    for (let z = 0; z < ZONES; z++) {
      const zoneRacks = frame.racks[z] ?? [];
      for (let r = 0; r < RACKS; r++) {
        const index = z * RACKS + r;
        const rackColor = applyColor(zoneRacks[r]?.color, this.color);
        this.mesh.setColorAt(index, rackColor);
        this.pulseColor.copy(rackColor).multiplyScalar(0.42);
        this.frontMesh.setColorAt(index, this.pulseColor);
        const pulseActive = placement?.zone === z && placement.rack === r;
        const pulse = pulseActive ? 1 + 0.09 * (0.5 + 0.5 * Math.sin(nowMs * 0.02)) : 1;
        const row = Math.floor(r / COLS);
        const col = r % COLS;
        const originX = (z - 1) * ZONE_PITCH;
        const x = originX - ((COLS - 1) * COL_PITCH) * 0.5 + col * COL_PITCH;
        const rowZ = [ROW_PITCH * 0.5, -ROW_PITCH * 0.5];
        this.dummy.position.set(x, CAB_H * 0.5 * pulse, rowZ[row] ?? 0);
        this.dummy.scale.set(1, pulse, 1);
        this.dummy.updateMatrix();
        this.mesh.setMatrixAt(index, this.dummy.matrix);
        this.dummy.position.z += CAB_D * 0.5 + 0.035;
        this.dummy.updateMatrix();
        this.frontMesh.setMatrixAt(index, this.dummy.matrix);
      }
      const pad = this.pads[z];
      const mat = pad.material as THREE.MeshLambertMaterial;
      const emergency = Boolean(frame.zones[z]?.emergency);
      if (emergency) {
        const pulse = 0.4 + 0.5 * Math.sin(nowMs * 0.008);
        this.work.copy(this.padBase[z]).lerp(new THREE.Color(0xcc2222), pulse);
        mat.color.copy(this.work);
        mat.emissive.setRGB(0.4 * pulse, 0.03, 0.03);
      } else {
        mat.color.copy(this.padBase[z]);
        mat.emissive.setRGB(0, 0, 0);
      }
    }
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
    this.mesh.instanceMatrix.needsUpdate = true;
    this.frontMesh.instanceMatrix.needsUpdate = true;
    if (this.frontMesh.instanceColor) this.frontMesh.instanceColor.needsUpdate = true;
    this.scene.background = frame.zones.some((zone) => zone.emergency)
      ? new THREE.Color(0x2a1214)
      : new THREE.Color(0x050816);
  }
}
