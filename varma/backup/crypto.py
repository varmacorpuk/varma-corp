"""Authenticated encryption for backup artefacts at rest.

Not a live broker credential. The key never belongs in GitHub. Employees
including the CEO cannot download it.

Construction: SHAKE256 keystream + HMAC-SHA256 (encrypt-then-MAC). Stdlib only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from pathlib import Path

from varma.config import DATA_DIR, get_settings

_VERSION = b"varma-backup-v1"
_KEY_BYTES = 32
_NONCE_BYTES = 16
_MAC_BYTES = 32
DEV_KEY_PATH = DATA_DIR / "backup.key"


def generate_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(_KEY_BYTES)).decode("ascii")


def _decode_key(key: str) -> bytes:
    raw = base64.urlsafe_b64decode(key.encode("ascii"))
    if len(raw) != _KEY_BYTES:
        raise ValueError("BACKUP_KEY_INVALID")
    return raw


def key_fingerprint(key: str) -> str:
    return hashlib.sha256(_decode_key(key)).hexdigest()[:16]


def encrypt_bytes(plaintext: bytes, key: str) -> str:
    k = _decode_key(key)
    nonce = secrets.token_bytes(_NONCE_BYTES)
    stream = hashlib.shake_256(_VERSION + k + nonce).digest(len(plaintext))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
    mac = hmac.new(k, _VERSION + nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + ciphertext).decode("ascii")


def decrypt_bytes(token: str, key: str) -> bytes:
    k = _decode_key(key)
    blob = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(blob) < _NONCE_BYTES + _MAC_BYTES:
        raise ValueError("BACKUP_CIPHERTEXT_INVALID")
    nonce = blob[:_NONCE_BYTES]
    mac = blob[_NONCE_BYTES : _NONCE_BYTES + _MAC_BYTES]
    ciphertext = blob[_NONCE_BYTES + _MAC_BYTES :]
    expected = hmac.new(k, _VERSION + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("BACKUP_MAC_INVALID")
    stream = hashlib.shake_256(_VERSION + k + nonce).digest(len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, stream))


def load_or_create_backup_key() -> str:
    """Env first. Else a TEMPORARY DEVELOPMENT key under data/ (gitignored)."""
    settings = get_settings()
    configured = (settings.backup_encryption_key or "").strip()
    if configured:
        _decode_key(configured)
        return configured
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DEV_KEY_PATH.exists():
        stored = DEV_KEY_PATH.read_text(encoding="ascii").strip()
        _decode_key(stored)
        return stored
    key = generate_key()
    DEV_KEY_PATH.write_text(key + "\n", encoding="ascii")
    DEV_KEY_PATH.chmod(0o600)
    return key
