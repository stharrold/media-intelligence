# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Key Management for Media Intelligence Pipeline.

Provides secure key storage and retrieval with two backends:
- Local/Air-gapped: OS keyring (encrypted, platform-native)
- Cloud: Google Cloud Key Management Service (KMS)

Usage:
    from src.key_manager import KeyManager

    # Auto-detect backend based on environment
    km = KeyManager()
    token = km.get_secret("huggingface_token")

    # Explicitly use keyring (local/air-gapped)
    km = KeyManager(backend="keyring")
    km.set_secret("huggingface_token", "hf_xxx")
    token = km.get_secret("huggingface_token")

    # Explicitly use GCP KMS (cloud)
    km = KeyManager(backend="gcp-kms", project_id="my-project")
    token = km.get_secret("huggingface_token")
"""

import os
from abc import ABC, abstractmethod
from typing import Literal


class KeyBackend(ABC):
    """Abstract base class for key storage backends."""

    @abstractmethod
    def get_secret(self, key_name: str) -> str | None:
        """Retrieve a secret by name."""

    @abstractmethod
    def set_secret(self, key_name: str, value: str) -> None:
        """Store a secret."""

    @abstractmethod
    def delete_secret(self, key_name: str) -> bool:
        """Delete a secret. Returns True if deleted, False if not found."""


class KeyringBackend(KeyBackend):
    """
    OS Keyring backend for local/air-gapped deployments.

    Uses the system keyring (macOS Keychain, Windows Credential Manager,
    Linux Secret Service) for encrypted key storage.
    """

    SERVICE_NAME = "media-intelligence"

    def __init__(self):
        """Initialize keyring backend."""
        try:
            import keyring

            self._keyring = keyring
        except ImportError as e:
            raise ImportError("keyring package required for local key management. " "Install with: pip install keyring") from e

    def get_secret(self, key_name: str) -> str | None:
        """Retrieve a secret from the OS keyring."""
        return self._keyring.get_password(self.SERVICE_NAME, key_name)

    def set_secret(self, key_name: str, value: str) -> None:
        """Store a secret in the OS keyring."""
        self._keyring.set_password(self.SERVICE_NAME, key_name, value)

    def delete_secret(self, key_name: str) -> bool:
        """Delete a secret from the OS keyring."""
        try:
            self._keyring.delete_password(self.SERVICE_NAME, key_name)
            return True
        except self._keyring.errors.PasswordDeleteError:
            return False


class GCPKMSBackend(KeyBackend):
    """
    Google Cloud KMS backend for cloud deployments.

    Stores encrypted secrets in Secret Manager, with encryption keys
    managed by Cloud KMS.
    """

    def __init__(self, project_id: str | None = None):
        """
        Initialize GCP KMS backend.

        Args:
            project_id: GCP project ID. Falls back to GOOGLE_CLOUD_PROJECT env var.
        """
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GCP project ID required. Set GOOGLE_CLOUD_PROJECT or pass project_id.")

        try:
            from google.cloud import secretmanager

            self._client = secretmanager.SecretManagerServiceClient()
        except ImportError as e:
            raise ImportError("google-cloud-secret-manager required for GCP key management. " "Install with: pip install google-cloud-secret-manager") from e

    def _secret_path(self, key_name: str) -> str:
        """Get the full secret path."""
        return f"projects/{self.project_id}/secrets/{key_name}/versions/latest"

    def _secret_parent(self, key_name: str) -> str:
        """Get the secret parent path."""
        return f"projects/{self.project_id}/secrets/{key_name}"

    def get_secret(self, key_name: str) -> str | None:
        """Retrieve a secret from GCP Secret Manager."""
        from google.api_core import exceptions

        try:
            response = self._client.access_secret_version(name=self._secret_path(key_name))
            return response.payload.data.decode("UTF-8")
        except exceptions.NotFound:
            return None

    def set_secret(self, key_name: str, value: str) -> None:
        """Store a secret in GCP Secret Manager."""
        from google.api_core import exceptions

        parent = f"projects/{self.project_id}"
        secret_id = key_name

        # Try to create the secret, or add a new version if it exists
        try:
            self._client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except exceptions.AlreadyExists:
            pass  # Secret exists, we'll add a new version

        # Add the secret version
        self._client.add_secret_version(
            request={
                "parent": self._secret_parent(key_name),
                "payload": {"data": value.encode("UTF-8")},
            }
        )

    def delete_secret(self, key_name: str) -> bool:
        """Delete a secret from GCP Secret Manager."""
        from google.api_core import exceptions

        try:
            self._client.delete_secret(name=self._secret_parent(key_name))
            return True
        except exceptions.NotFound:
            return False


class EnvironmentBackend(KeyBackend):
    """
    Environment variable backend (fallback).

    Maps key names to environment variables:
    - huggingface_token -> HUGGINGFACE_TOKEN
    - gcp_project -> GOOGLE_CLOUD_PROJECT
    """

    ENV_MAPPING = {
        "huggingface_token": "HUGGINGFACE_TOKEN",
        "gcp_project": "GOOGLE_CLOUD_PROJECT",
        "gcp_region": "GOOGLE_CLOUD_REGION",
    }

    def get_secret(self, key_name: str) -> str | None:
        """Retrieve a secret from environment variables."""
        env_var = self.ENV_MAPPING.get(key_name, key_name.upper())
        return os.environ.get(env_var)

    def set_secret(self, key_name: str, value: str) -> None:
        """Set an environment variable (current process only)."""
        env_var = self.ENV_MAPPING.get(key_name, key_name.upper())
        os.environ[env_var] = value

    def delete_secret(self, key_name: str) -> bool:
        """Remove an environment variable."""
        env_var = self.ENV_MAPPING.get(key_name, key_name.upper())
        if env_var in os.environ:
            del os.environ[env_var]
            return True
        return False


BackendType = Literal["keyring", "gcp-kms", "env", "auto"]


class KeyManager:
    """
    Unified key management interface.

    Automatically selects the appropriate backend based on environment:
    - If GOOGLE_CLOUD_PROJECT is set: uses GCP Secret Manager
    - Otherwise: uses OS keyring (falls back to env vars if unavailable)
    """

    def __init__(
        self,
        backend: BackendType = "auto",
        project_id: str | None = None,
        fallback_to_env: bool = True,
    ):
        """
        Initialize key manager.

        Args:
            backend: Backend to use ("keyring", "gcp-kms", "env", "auto")
            project_id: GCP project ID (for gcp-kms backend)
            fallback_to_env: Fall back to environment variables if secret not found
        """
        self.fallback_to_env = fallback_to_env
        self._env_backend = EnvironmentBackend() if fallback_to_env else None

        if backend == "auto":
            backend = self._detect_backend()

        if backend == "keyring":
            self._backend = KeyringBackend()
        elif backend == "gcp-kms":
            self._backend = GCPKMSBackend(project_id=project_id)
        elif backend == "env":
            self._backend = EnvironmentBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}")

        self._backend_type = backend

    def _detect_backend(self) -> BackendType:
        """Auto-detect the appropriate backend."""
        # If GCP project is set, assume cloud deployment
        if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            return "gcp-kms"

        # Try keyring, fall back to env
        try:
            import keyring

            # Test that keyring is functional
            keyring.get_keyring()
            return "keyring"
        except Exception:
            return "env"

    @property
    def backend_type(self) -> str:
        """Return the active backend type."""
        return self._backend_type

    def get_secret(self, key_name: str) -> str | None:
        """
        Retrieve a secret.

        Args:
            key_name: Name of the secret (e.g., "huggingface_token")

        Returns:
            Secret value or None if not found
        """
        value = self._backend.get_secret(key_name)

        # Fallback to environment if enabled and secret not found
        if value is None and self.fallback_to_env and self._env_backend:
            value = self._env_backend.get_secret(key_name)

        return value

    def set_secret(self, key_name: str, value: str) -> None:
        """
        Store a secret.

        Args:
            key_name: Name of the secret
            value: Secret value
        """
        self._backend.set_secret(key_name, value)

    def delete_secret(self, key_name: str) -> bool:
        """
        Delete a secret.

        Args:
            key_name: Name of the secret

        Returns:
            True if deleted, False if not found
        """
        return self._backend.delete_secret(key_name)

    def get_huggingface_token(self) -> str | None:
        """Convenience method to get HuggingFace token."""
        return self.get_secret("huggingface_token")

    def set_huggingface_token(self, token: str) -> None:
        """Convenience method to set HuggingFace token."""
        self.set_secret("huggingface_token", token)
