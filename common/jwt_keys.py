"""
JWT key rotation helpers: derive a signing key per 30-minute window from a base secret.

Design:
- kid = integer window id = floor(utc_epoch_seconds / (30 * 60))
- key = HMAC-SHA256(base_secret, f"jwt:{algorithm}:{kid}")
- Encode tokens with header { kid } and verify using the derived key for that kid.
- Back-compat: If no kid header, try current and previous window keys, and finally the legacy static key.
"""
from __future__ import annotations
import hmac
import hashlib
import time
from typing import Optional, Tuple, List

from config import JWT_ALGORITHM, JWT_SECRET_KEY as LEGACY_JWT_SECRET, os as _os  # type: ignore

# Base secret for derivation (fallback to legacy if not provided)
JWT_SECRET_BASE: str = _os.getenv("JWT_SECRET_BASE", LEGACY_JWT_SECRET)

# Rotation window in seconds (30 minutes)
ROTATION_WINDOW_SECONDS: int = 30 * 60


def get_window_id(ts: Optional[float] = None) -> int:
    """Return integer window id for the given unix timestamp (UTC)."""
    if ts is None:
        ts = time.time()
    return int(ts // ROTATION_WINDOW_SECONDS)


def derive_key(window_id: int, algorithm: str = JWT_ALGORITHM) -> bytes:
    """Derive a per-window key using HMAC-SHA256 over the base secret.

    Using HMAC with the base secret ensures keys are deterministic across instances
    that share the same base secret, without storing rotating keys.
    """
    msg = f"jwt:{algorithm}:{window_id}".encode("utf-8")
    base = JWT_SECRET_BASE.encode("utf-8")
    return hmac.new(base, msg, hashlib.sha256).digest()


def current_key_and_kid() -> Tuple[bytes, str]:
    kid = str(get_window_id())
    return derive_key(int(kid)), kid


def candidate_keys_for_legacy_verification() -> List[bytes]:
    """Keys to try when token has no kid or for backward compatibility."""
    now = time.time()
    current = derive_key(get_window_id(now))
    previous = derive_key(get_window_id(now - ROTATION_WINDOW_SECONDS))
    candidates: List[bytes] = [current, previous]
    # Add legacy static secret if set
    if LEGACY_JWT_SECRET:
        candidates.append(LEGACY_JWT_SECRET.encode("utf-8"))
    return candidates
