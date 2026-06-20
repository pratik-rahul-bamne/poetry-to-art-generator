"""
Unit tests for Core security utilities.
Tests password hashing and JWT token create/decode.
"""

import pytest
from datetime import timedelta

from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_different_hashes(self):
        """bcrypt uses random salts — same password → different hashes."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(subject="user-uuid-123", role="user")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-uuid-123"
        assert payload["role"] == "user"

    def test_admin_role_in_token(self):
        token = create_access_token(subject="admin-uuid", role="admin")
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_expired_token_raises(self):
        token = create_access_token(
            subject="test", expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(ValueError, match="Invalid or expired token"):
            decode_access_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            decode_access_token("this.is.not.a.valid.jwt")

    def test_tampered_token_raises(self):
        token = create_access_token(subject="user-1")
        # Tamper with the payload
        parts = token.split(".")
        tampered = parts[0] + ".tampered" + "." + parts[2]
        with pytest.raises(ValueError):
            decode_access_token(tampered)
