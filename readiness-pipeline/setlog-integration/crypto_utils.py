"""
Encrypts the readiness payload before it ever touches a git repo.

Format (all fields base64, JSON):
  { "salt": "...", "iv": "...", "ciphertext": "...", "iterations": 250000 }

Uses PBKDF2-HMAC-SHA256 for key derivation and AES-256-GCM for encryption,
the exact same primitives the browser's Web Crypto API (SubtleCrypto) uses,
so js/readiness-crypto.js can decrypt this directly with no server involved.
"""

import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITERATIONS = 250_000
KEY_LEN = 32   # AES-256
SALT_LEN = 16
IV_LEN = 12    # standard GCM nonce size


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_json(obj, passphrase: str) -> dict:
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)
    key = _derive_key(passphrase, salt)

    plaintext = json.dumps(obj).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(iv, plaintext, None)  # tag appended, Web Crypto compatible

    return {
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "iterations": ITERATIONS,
    }


def decrypt_json(payload: dict, passphrase: str):
    """Round-trip check helper; the real decryption happens in the browser."""
    salt = base64.b64decode(payload["salt"])
    iv = base64.b64decode(payload["iv"])
    ciphertext = base64.b64decode(payload["ciphertext"])
    key = _derive_key(passphrase, salt)
    plaintext = AESGCM(key).decrypt(iv, ciphertext, None)
    return json.loads(plaintext)


if __name__ == "__main__":
    demo = {"hello": "from python", "score": 74}
    enc = encrypt_json(demo, "correct horse battery staple")
    print(json.dumps(enc, indent=2))
    assert decrypt_json(enc, "correct horse battery staple") == demo
    print("round-trip OK")
