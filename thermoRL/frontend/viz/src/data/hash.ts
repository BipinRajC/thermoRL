import { ReplayError } from "./loader";

export async function sha256Hex(bytes: ArrayBuffer | Uint8Array): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new ReplayError("hash", "Hash verification needs a secure context (localhost or https)");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}
