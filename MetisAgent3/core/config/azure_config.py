"""
Azure Configuration for MetisAgent3

Environment variables:
- AZURE_SQL_CONNECTION_STRING: Full connection string for Azure SQL
- AZURE_STORAGE_CONNECTION_STRING: Connection string for Blob Storage
- AZURE_KEY_VAULT_URL: Key Vault URL (e.g., https://kv-metis-prod.vault.azure.net/)
- AZURE_TENANT_ID: Azure AD tenant ID (optional, for managed identity)
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureSQLConfig:
    """Azure SQL Database configuration"""
    server: str = "metissqldb.database.windows.net"
    database: str = "METISENGINE"
    username: str = ""
    password: str = ""
    driver: str = "ODBC Driver 18 for SQL Server"

    @property
    def connection_string(self) -> str:
        """Generate ODBC connection string"""
        if os.getenv("AZURE_SQL_CONNECTION_STRING"):
            return os.getenv("AZURE_SQL_CONNECTION_STRING")

        return (
            f"Driver={{{self.driver}}};"
            f"Server=tcp:{self.server},1433;"
            f"Database={self.database};"
            f"Uid={self.username};"
            f"Pwd={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

    @classmethod
    def from_env(cls) -> "AzureSQLConfig":
        """Create config from environment variables"""
        return cls(
            server=os.getenv("AZURE_SQL_SERVER", "metissqldb.database.windows.net"),
            database=os.getenv("AZURE_SQL_DATABASE", "METISENGINE"),
            username=os.getenv("AZURE_SQL_USERNAME", ""),
            password=os.getenv("AZURE_SQL_PASSWORD", ""),
            driver=os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
        )


@dataclass
class AzureBlobConfig:
    """Azure Blob Storage configuration for plugins"""
    account_name: str = "stmetisplugins"
    container_name: str = "plugins"
    connection_string: str = ""

    @classmethod
    def from_env(cls) -> "AzureBlobConfig":
        """Create config from environment variables"""
        return cls(
            account_name=os.getenv("AZURE_STORAGE_ACCOUNT", "stmetisplugins"),
            container_name=os.getenv("AZURE_STORAGE_CONTAINER", "plugins"),
            connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        )


@dataclass
class AzureKeyVaultConfig:
    """Azure Key Vault configuration"""
    vault_url: str = "https://kv-metis-prod.vault.azure.net/"

    @classmethod
    def from_env(cls) -> "AzureKeyVaultConfig":
        """Create config from environment variables"""
        return cls(
            vault_url=os.getenv("AZURE_KEY_VAULT_URL", "https://kv-metis-prod.vault.azure.net/")
        )


@dataclass
class AzureConfig:
    """Main Azure configuration container"""
    sql: AzureSQLConfig
    blob: AzureBlobConfig
    keyvault: AzureKeyVaultConfig

    # Entropi tenant specific
    tenant_id: str = "7bab0f6f-bc06-4083-b0a0-168677c2dd45"
    subscription_id: str = "33a6e4da-40ae-4f2c-baee-efdc68f61f43"
    resource_group: str = "MetisResource"
    container_registry: str = "rmmsreg.azurecr.io"

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """Create full Azure config from environment"""
        return cls(
            sql=AzureSQLConfig.from_env(),
            blob=AzureBlobConfig.from_env(),
            keyvault=AzureKeyVaultConfig.from_env(),
            tenant_id=os.getenv("AZURE_TENANT_ID", "7bab0f6f-bc06-4083-b0a0-168677c2dd45"),
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", "33a6e4da-40ae-4f2c-baee-efdc68f61f43"),
            resource_group=os.getenv("AZURE_RESOURCE_GROUP", "MetisResource"),
            container_registry=os.getenv("AZURE_CONTAINER_REGISTRY", "rmmsreg.azurecr.io")
        )


# Global config instance
_azure_config: Optional[AzureConfig] = None


def get_azure_config() -> AzureConfig:
    """Get or create Azure configuration"""
    global _azure_config
    if _azure_config is None:
        _azure_config = AzureConfig.from_env()
    return _azure_config


def is_azure_environment() -> bool:
    """Check if running in Azure environment"""
    return bool(
        os.getenv("AZURE_SQL_CONNECTION_STRING") or
        os.getenv("WEBSITE_SITE_NAME") or  # Azure App Service
        os.getenv("CONTAINER_APP_NAME")     # Azure Container Apps
    )
