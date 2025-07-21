# Security Credentials Refactor - Design

## Architecture Overview

### Credential Storage Abstraction
```python
from abc import ABC, abstractmethod
from typing import Protocol, Any

class CredentialStorage(Protocol):
    """Protocol for credential storage backends."""

    @abstractmethod
    def store(self, provider: str, key: str, value: str) -> None:
        """Store a credential securely."""
        ...

    @abstractmethod
    def retrieve(self, provider: str, key: str) -> str | None:
        """Retrieve a credential."""
        ...

    @abstractmethod
    def delete(self, provider: str, key: str) -> None:
        """Delete a credential."""
        ...

    @abstractmethod
    def exists(self, provider: str, key: str) -> bool:
        """Check if a credential exists."""
        ...

class CredentialManager:
    """Centralized credential management with pluggable backends."""

    def __init__(self, storage: CredentialStorage | None = None):
        self.storage = storage or self._get_default_storage()

    def _get_default_storage(self) -> CredentialStorage:
        """Auto-detect best available storage backend."""
        # Implementation details below
```

### Storage Backend Implementations

#### 1. Keyring Backend (Primary)
```python
import keyring
from typing import Any

class KeyringStorage(CredentialStorage):
    """System keyring-based credential storage."""

    SERVICE_NAME = "model-forge"

    def store(self, provider: str, key: str, value: str) -> None:
        """Store using system keyring."""
        service_key = f"{self.SERVICE_NAME}.{provider}.{key}"
        keyring.set_password(service_key, "credential", value)

    def retrieve(self, provider: str, key: str) -> str | None:
        """Retrieve from system keyring."""
        service_key = f"{self.SERVICE_NAME}.{provider}.{key}"
        return keyring.get_password(service_key, "credential")

    def delete(self, provider: str, key: str) -> None:
        """Delete from system keyring."""
        service_key = f"{self.SERVICE_NAME}.{provider}.{key}"
        keyring.delete_password(service_key, "credential")

    def exists(self, provider: str, key: str) -> bool:
        """Check if credential exists in keyring."""
        return self.retrieve(provider, key) is not None
```

#### 2. Environment Variable Backend (Fallback)
```python
import os

class EnvVarStorage(CredentialStorage):
    """Environment variable-based credential storage."""

    def store(self, provider: str, key: str, value: str) -> None:
        """Store in environment variables."""
        env_key = f"MODEL_FORGE_{provider.upper()}_{key.upper()}"
        os.environ[env_key] = value

    def retrieve(self, provider: str, key: str) -> str | None:
        """Retrieve from environment variables."""
        env_key = f"MODEL_FORGE_{provider.upper()}_{key.upper()}"
        return os.environ.get(env_key)

    def delete(self, provider: str, key: str) -> None:
        """Delete from environment variables."""
        env_key = f"MODEL_FORGE_{provider.upper()}_{key.upper()}"
        os.environ.pop(env_key, None)

    def exists(self, provider: str, key: str) -> bool:
        """Check if credential exists in environment."""
        return self.retrieve(provider, key) is not None
```

#### 3. Encrypted File Backend (Fallback)
```python
from cryptography.fernet import Fernet
import json
from pathlib import Path

class EncryptedFileStorage(CredentialStorage):
    """Encrypted file-based credential storage."""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".config" / "model-forge"
        self.key_file = self.config_dir / ".encryption_key"
        self.credentials_file = self.config_dir / "credentials.enc"
        self._ensure_key_exists()

    def _ensure_key_exists(self) -> None:
        """Generate encryption key if it doesn't exist."""
        if not self.key_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Restrict permissions

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher instance."""
        key = self.key_file.read_bytes()
        return Fernet(key)

    def store(self, provider: str, key: str, value: str) -> None:
        """Store encrypted credentials."""
        credentials = self._load_credentials()
        credentials[f"{provider}.{key}"] = value
        self._save_credentials(credentials)

    def retrieve(self, provider: str, key: str) -> str | None:
        """Retrieve decrypted credentials."""
        credentials = self._load_credentials()
        return credentials.get(f"{provider}.{key}")

    def delete(self, provider: str, key: str) -> None:
        """Delete credentials."""
        credentials = self._load_credentials()
        credentials.pop(f"{provider}.{key}", None)
        self._save_credentials(credentials)

    def exists(self, provider: str, key: str) -> bool:
        """Check if credential exists."""
        return self.retrieve(provider, key) is not None

    def _load_credentials(self) -> dict[str, str]:
        """Load and decrypt credentials."""
        if not self.credentials_file.exists():
            return {}

        cipher = self._get_cipher()
        encrypted_data = self.credentials_file.read_bytes()
        try:
            decrypted_data = cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception:
            return {}

    def _save_credentials(self, credentials: dict[str, str]) -> None:
        """Encrypt and save credentials."""
        cipher = self._get_cipher()
        data = json.dumps(credentials).encode()
        encrypted_data = cipher.encrypt(data)
        self.credentials_file.write_bytes(encrypted_data)
        self.credentials_file.chmod(0o600)  # Restrict permissions
```

### Auto-Detection Strategy
```python
class AutoStorage(CredentialStorage):
    """Automatically selects best available storage backend."""

    def __init__(self) -> None:
        self._backend = self._detect_best_backend()

    def _detect_best_backend(self) -> CredentialStorage:
        """Detect best available storage backend."""
        backends = [
            ("keyring", KeyringStorage),
            ("encrypted_file", EncryptedFileStorage),
            ("env_var", EnvVarStorage),
        ]

        for name, backend_class in backends:
            try:
                backend = backend_class()
                # Test basic functionality
                backend.store("test", "test", "test")
                retrieved = backend.retrieve("test", "test")
                backend.delete("test", "test")

                if retrieved == "test":
                    return backend
            except Exception:
                continue

        # Fallback to plain text (for backward compatibility)
        return PlainTextStorage()

    def store(self, provider: str, key: str, value: str) -> None:
        return self._backend.store(provider, key, value)

    def retrieve(self, provider: str, key: str) -> str | None:
        return self._backend.retrieve(provider, key)

    def delete(self, provider: str, key: str) -> None:
        return self._backend.delete(provider, key)

    def exists(self, provider: str, key: str) -> bool:
        return self._backend.exists(provider, key)
```

### Integration with Existing Code

#### Updated Authentication Flow
```python
# In auth.py
from modelforge.credentials import CredentialManager

class AuthStrategy(ABC):
    """Updated authentication strategy with credential manager."""

    def __init__(self, provider_name: str, credential_manager: CredentialManager | None = None):
        self.provider_name = provider_name
        self.credential_manager = credential_manager or CredentialManager()

    def store_credential(self, key: str, value: str) -> None:
        """Store credential securely."""
        self.credential_manager.store(self.provider_name, key, value)

    def get_credential(self, key: str) -> str | None:
        """Retrieve credential securely."""
        return self.credential_manager.retrieve(self.provider_name, key)

    def delete_credential(self, key: str) -> None:
        """Delete credential securely."""
        self.credential_manager.delete(self.provider_name, key)
```

#### Migration Strategy
```python
class CredentialMigrator:
    """Handle migration from plain text to secure storage."""

    def __init__(self, old_config_path: Path, new_storage: CredentialStorage):
        self.old_config_path = old_config_path
        self.new_storage = new_storage

    def migrate_credentials(self) -> dict[str, int]:
        """Migrate credentials from old format to new secure storage."""
        if not self.old_config_path.exists():
            return {}

        with open(self.old_config_path) as f:
            old_config = json.load(f)

        migration_stats = {}

        for provider, provider_data in old_config.get("providers", {}).items():
            credentials = provider_data.get("credentials", {})
            migrated = 0

            for key, value in credentials.items():
                if isinstance(value, str) and value.strip():
                    self.new_storage.store(provider, key, value)
                    migrated += 1

            migration_stats[provider] = migrated

        # Rename old config file to mark as migrated
        backup_path = self.old_config_path.with_suffix(".json.backup")
        self.old_config_path.rename(backup_path)

        return migration_stats

    def can_migrate(self) -> bool:
        """Check if migration is needed and possible."""
        return (self.old_config_path.exists() and
                self.old_config_path.stat().st_size > 0)
```

## Testing Strategy

### Test Storage Backends
```python
import pytest
from tempfile import TemporaryDirectory
from pathlib import Path

class TestStorageBackends:
    """Test all storage backend implementations."""

    @pytest.fixture
    def test_storage(self) -> CredentialStorage:
        """Provide test storage backend."""
        return EncryptedFileStorage()

    def test_store_retrieve_cycle(self, test_storage: CredentialStorage) -> None:
        """Test basic store/retrieve cycle."""
        test_storage.store("test_provider", "test_key", "secret_value")
        assert test_storage.retrieve("test_provider", "test_key") == "secret_value"

    def test_delete_credential(self, test_storage: CredentialStorage) -> None:
        """Test credential deletion."""
        test_storage.store("test_provider", "test_key", "secret_value")
        test_storage.delete("test_provider", "test_key")
        assert test_storage.retrieve("test_provider", "test_key") is None

    def test_nonexistent_credential(self, test_storage: CredentialStorage) -> None:
        """Test retrieval of non-existent credential."""
        assert test_storage.retrieve("nonexistent", "key") is None
```

## Error Handling

### Credential Storage Exceptions
```python
class CredentialStorageError(Exception):
    """Base exception for credential storage operations."""
    pass

class CredentialNotFoundError(CredentialStorageError):
    """Raised when a credential doesn't exist."""
    pass

class CredentialStorageUnavailableError(CredentialStorageError):
    """Raised when storage backend is unavailable."""
    pass

class CredentialValidationError(CredentialStorageError):
    """Raised when credential format is invalid."""
    pass
```
