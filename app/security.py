"""Password hashing for TestPath Manager (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 390_000
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    """Create a salted, one-way verifier suitable for storage in accounts.json."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must have at least {MIN_PASSWORD_LENGTH} characters.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join(
        (
            ALGORITHM,
            str(ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    """Return False if a verifier is invalid; never use plaintext fallback."""
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        if not 100_000 <= iterations <= 2_000_000:
            return False
        salt = base64.b64decode(salt_text, validate=True)
        expected = base64.b64decode(digest_text, validate=True)
        if len(salt) < 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False
