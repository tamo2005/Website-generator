"""
tests/unit/test_security.py — Unit tests for core.security primitives
"""
import pytest
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_token,
    hash_token,
)


class TestPasswordHashing:
    def test_hash_produces_different_result_from_input(self):
        pw = "TestPassword123!"
        hashed = hash_password(pw)
        assert hashed != pw

    def test_verify_correct_password(self):
        pw = "TestPassword123!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_deterministically_different_each_time(self):
        """bcrypt uses a unique salt per hash call."""
        pw = "SamePassword"
        assert hash_password(pw) != hash_password(pw)


class TestJWT:
    def test_create_and_decode_access_token(self):
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        role = "user"
        token = create_access_token(user_id, role)
        payload = decode_access_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert payload["type"] == "access"

    def test_decode_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_access_token("not.a.valid.token")


class TestTokenHelpers:
    def test_generate_token_is_url_safe_string(self):
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 10

    def test_hash_token_produces_64_char_hex(self):
        token = generate_token()
        hashed = hash_token(token)
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_is_deterministic(self):
        token = "fixed-test-token"
        assert hash_token(token) == hash_token(token)
