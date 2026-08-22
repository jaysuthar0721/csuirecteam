/**
 * Decrypts a payload produced by crypto_utils.py, using the browser's
 * native Web Crypto API. No dependencies, works offline.
 *
 * Payload shape: { salt, iv, ciphertext, iterations } — all base64.
 */

function b64ToBytes(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

async function deriveKey(passphrase, saltBytes, iterations) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(passphrase),
    { name: "PBKDF2" },
    false,
    ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: saltBytes, iterations, hash: "SHA-256" },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"]
  );
}

/**
 * Returns the decrypted object, or throws if the passphrase is wrong
 * (Web Crypto surfaces this as an OperationError from the GCM auth tag
 * check, which is the correct behavior — wrong passphrase should fail
 * loudly, not silently return garbage).
 */
async function decryptPayload(payload, passphrase) {
  const salt = b64ToBytes(payload.salt);
  const iv = b64ToBytes(payload.iv);
  const ciphertext = b64ToBytes(payload.ciphertext);
  const key = await deriveKey(passphrase, salt, payload.iterations);
  const plaintextBuf = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    key,
    ciphertext
  );
  const json = new TextDecoder().decode(plaintextBuf);
  return JSON.parse(json);
}

// Export for both browser <script> use and Node testing.
if (typeof module !== "undefined") {
  module.exports = { decryptPayload, deriveKey, b64ToBytes };
}
