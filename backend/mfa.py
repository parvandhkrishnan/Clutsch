"""MFA (TOTP) implementation for Clutsch."""
import os
import pyotp
import hashlib
import secrets
import base64
from typing import List, Optional

# Generate a consistent app secret for MFA from the encryption key
# so that MFA secrets are deterministic within the same deployment.
def _get_mfa_secret() -> str:
    enc_key = os.environ.get("ENCRYPTION_KEY", "")
    if not enc_key:
        raise RuntimeError("ENCRYPTION_KEY must be set for MFA secret generation")
    # Use a deterministic hash of the encryption key as the MFA issuer secret
    return hashlib.sha256(enc_key.encode()).hexdigest()[:32]


def generate_totp_secret() -> str:
    """Generate a new TOTP secret for a user."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Clutsch") -> str:
    """Get the otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generate a list of recovery codes (one-time use)."""
    codes = []
    for _ in range(count):
        code = secrets.token_hex(4).upper()  # 8-char hex code
        codes.append(f"{code[:4]}-{code[4:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage."""
    return hashlib.sha256(code.encode()).hexdigest()