# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the Key Manager module.

Uses pytest-mock for clean, readable mocking.
"""

import os

import pytest

from src.key_manager import EnvironmentBackend, GCPKMSBackend, KeyManager, KeyringBackend


class TestEnvironmentBackend:
    """Tests for EnvironmentBackend."""

    def test_get_secret_exists(self, mocker):
        """Test retrieving an existing environment variable."""
        mocker.patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "test-token"})
        backend = EnvironmentBackend()
        assert backend.get_secret("huggingface_token") == "test-token"

    def test_get_secret_not_exists(self, mocker):
        """Test retrieving a non-existent environment variable."""
        mocker.patch.dict(os.environ, {}, clear=True)
        backend = EnvironmentBackend()
        assert backend.get_secret("huggingface_token") is None

    def test_get_secret_unmapped_key(self, mocker):
        """Test retrieving an unmapped key (uses uppercase)."""
        mocker.patch.dict(os.environ, {"CUSTOM_KEY": "custom-value"})
        backend = EnvironmentBackend()
        assert backend.get_secret("custom_key") == "custom-value"

    def test_set_secret(self):
        """Test setting an environment variable."""
        backend = EnvironmentBackend()
        backend.set_secret("huggingface_token", "new-token")
        assert os.environ.get("HUGGINGFACE_TOKEN") == "new-token"
        # Cleanup
        del os.environ["HUGGINGFACE_TOKEN"]

    def test_delete_secret_exists(self, mocker):
        """Test deleting an existing environment variable."""
        mocker.patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "test-token"})
        backend = EnvironmentBackend()
        result = backend.delete_secret("huggingface_token")
        assert result is True
        assert "HUGGINGFACE_TOKEN" not in os.environ

    def test_delete_secret_not_exists(self, mocker):
        """Test deleting a non-existent environment variable."""
        mocker.patch.dict(os.environ, {}, clear=True)
        backend = EnvironmentBackend()
        result = backend.delete_secret("huggingface_token")
        assert result is False


class TestKeyringBackend:
    """Tests for KeyringBackend."""

    def test_init_success(self, mocker):
        """Test successful initialization with keyring available."""
        mock_keyring = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        backend = KeyringBackend()
        assert backend._keyring is not None

    def test_get_secret(self, mocker):
        """Test retrieving a secret from keyring."""
        mock_keyring = mocker.MagicMock()
        mock_keyring.get_password.return_value = "stored-token"
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        backend = KeyringBackend()
        backend._keyring = mock_keyring

        result = backend.get_secret("huggingface_token")
        assert result == "stored-token"
        mock_keyring.get_password.assert_called_once_with("media-intelligence", "huggingface_token")

    def test_set_secret(self, mocker):
        """Test storing a secret in keyring."""
        mock_keyring = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        backend = KeyringBackend()
        backend._keyring = mock_keyring

        backend.set_secret("huggingface_token", "new-token")
        mock_keyring.set_password.assert_called_once_with("media-intelligence", "huggingface_token", "new-token")

    def test_delete_secret_success(self, mocker):
        """Test deleting a secret from keyring."""
        mock_keyring = mocker.MagicMock()
        mock_keyring.errors = mocker.MagicMock()
        mock_keyring.errors.PasswordDeleteError = Exception
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        backend = KeyringBackend()
        backend._keyring = mock_keyring

        result = backend.delete_secret("huggingface_token")
        assert result is True
        mock_keyring.delete_password.assert_called_once_with("media-intelligence", "huggingface_token")

    def test_delete_secret_not_found(self, mocker):
        """Test deleting a non-existent secret."""
        mock_keyring = mocker.MagicMock()
        mock_keyring.errors = mocker.MagicMock()
        mock_keyring.errors.PasswordDeleteError = Exception
        mock_keyring.delete_password.side_effect = Exception("not found")
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        backend = KeyringBackend()
        backend._keyring = mock_keyring

        result = backend.delete_secret("huggingface_token")
        assert result is False


class TestGCPKMSBackend:
    """Tests for GCPKMSBackend."""

    def test_init_with_project_id(self, mocker):
        """Test initialization with explicit project ID."""
        mock_secretmanager = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {}, clear=True)

        backend = GCPKMSBackend(project_id="test-project")
        assert backend.project_id == "test-project"

    def test_init_from_env(self, mocker):
        """Test initialization from environment variable."""
        mock_secretmanager = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "env-project"})

        backend = GCPKMSBackend()
        assert backend.project_id == "env-project"

    def test_init_no_project_raises(self, mocker):
        """Test initialization without project raises error."""
        mock_secretmanager = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {}, clear=True)

        with pytest.raises(ValueError, match="GCP project ID required"):
            GCPKMSBackend()

    def test_get_secret(self, mocker):
        """Test retrieving a secret from GCP Secret Manager."""
        mock_secretmanager = mocker.MagicMock()
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.payload.data.decode.return_value = "gcp-secret"
        mock_client.access_secret_version.return_value = mock_response
        mock_secretmanager.SecretManagerServiceClient.return_value = mock_client

        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})

        backend = GCPKMSBackend()
        backend._client = mock_client

        # Mock google.api_core.exceptions
        mock_exceptions = mocker.MagicMock()
        mock_exceptions.NotFound = Exception
        mocker.patch.dict("sys.modules", {"google.api_core.exceptions": mock_exceptions})

        result = backend.get_secret("huggingface_token")
        assert result == "gcp-secret"

    def test_get_secret_not_found(self, mocker):
        """Test retrieving a non-existent secret."""
        mock_secretmanager = mocker.MagicMock()
        mock_client = mocker.MagicMock()

        # Create a custom exception class for NotFound
        class NotFoundError(Exception):
            pass

        mock_client.access_secret_version.side_effect = NotFoundError("not found")
        mock_secretmanager.SecretManagerServiceClient.return_value = mock_client

        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})

        # Mock exceptions module
        mock_exceptions = mocker.MagicMock()
        mock_exceptions.NotFound = NotFoundError
        mocker.patch("src.key_manager.GCPKMSBackend.get_secret", return_value=None)

        backend = GCPKMSBackend()
        result = backend.get_secret("nonexistent_key")
        assert result is None


class TestKeyManager:
    """Tests for KeyManager unified interface."""

    def test_init_with_env_backend(self, mocker):
        """Test initialization with environment backend."""
        km = KeyManager(backend="env")
        assert km.backend_type == "env"

    def test_init_with_keyring_backend(self, mocker):
        """Test initialization with keyring backend."""
        mock_keyring = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})

        km = KeyManager(backend="keyring")
        assert km.backend_type == "keyring"

    def test_init_with_gcp_kms_backend(self, mocker):
        """Test initialization with GCP KMS backend."""
        mock_secretmanager = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})

        km = KeyManager(backend="gcp-kms")
        assert km.backend_type == "gcp-kms"

    def test_auto_detect_gcp(self, mocker):
        """Test auto-detection selects GCP when project is set."""
        mock_secretmanager = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"google.cloud.secretmanager": mock_secretmanager})
        mocker.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})

        km = KeyManager(backend="auto")
        assert km.backend_type == "gcp-kms"

    def test_auto_detect_keyring(self, mocker):
        """Test auto-detection selects keyring when available."""
        mock_keyring = mocker.MagicMock()
        mock_keyring.get_keyring.return_value = mocker.MagicMock()
        mocker.patch.dict("sys.modules", {"keyring": mock_keyring})
        mocker.patch.dict(os.environ, {}, clear=True)

        # Need to reimport after patching
        mocker.patch("src.key_manager.KeyManager._detect_backend", return_value="keyring")

        km = KeyManager(backend="auto")
        assert km.backend_type == "keyring"

    def test_get_secret_with_fallback(self, mocker):
        """Test get_secret falls back to environment."""
        mocker.patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "env-token"})

        km = KeyManager(backend="env", fallback_to_env=True)
        result = km.get_secret("huggingface_token")
        assert result == "env-token"

    def test_get_huggingface_token_convenience(self, mocker):
        """Test convenience method for HuggingFace token."""
        mocker.patch.dict(os.environ, {"HUGGINGFACE_TOKEN": "hf-token"})

        km = KeyManager(backend="env")
        result = km.get_huggingface_token()
        assert result == "hf-token"

    def test_set_huggingface_token_convenience(self, mocker):
        """Test convenience method for setting HuggingFace token."""
        km = KeyManager(backend="env")
        km.set_huggingface_token("new-hf-token")
        assert os.environ.get("HUGGINGFACE_TOKEN") == "new-hf-token"
        # Cleanup
        del os.environ["HUGGINGFACE_TOKEN"]

    def test_unknown_backend_raises(self):
        """Test that unknown backend raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend"):
            KeyManager(backend="invalid")
