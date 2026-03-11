from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class AuthConfig:
    auth_mode: str
    tenant_mode: str
    user_id: str
    oauth_provider: str
    oauth_client_id: str
    oauth_redirect_uri: str
    vinnova_api_key: str
    grants_gov_api_key: str
    eu_sedia_api_key: str


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_auth_config(env_file: Path | None = None) -> AuthConfig:
    env_values = dict(os.environ)
    if env_file is not None:
        file_values = _read_env_file(env_file)
        # Environment variables should always override file values.
        for key, value in file_values.items():
            env_values.setdefault(key, value)

    return AuthConfig(
        auth_mode=env_values.get("GRANT_AUTH_MODE", "api_key"),
        tenant_mode=env_values.get("GRANT_TENANT_MODE", "single_user"),
        user_id=env_values.get("GRANT_USER_ID", "local_user"),
        oauth_provider=env_values.get("GRANT_OAUTH_PROVIDER", ""),
        oauth_client_id=env_values.get("GRANT_OAUTH_CLIENT_ID", ""),
        oauth_redirect_uri=env_values.get("GRANT_OAUTH_REDIRECT_URI", ""),
        vinnova_api_key=env_values.get("VINNOVA_API_KEY", ""),
        grants_gov_api_key=env_values.get("GRANTS_GOV_API_KEY", ""),
        eu_sedia_api_key=env_values.get("EU_SEDIA_API_KEY", ""),
    )


def validate_auth_config(config: AuthConfig) -> list[str]:
    warnings: list[str] = []

    if config.auth_mode not in {"api_key", "oauth"}:
        warnings.append("GRANT_AUTH_MODE should be 'api_key' or 'oauth'.")

    if config.tenant_mode not in {"single_user", "multi_tenant"}:
        warnings.append("GRANT_TENANT_MODE should be 'single_user' or 'multi_tenant'.")

    if config.auth_mode == "oauth":
        if not config.oauth_provider:
            warnings.append("GRANT_OAUTH_PROVIDER is missing for oauth mode.")
        if not config.oauth_client_id:
            warnings.append("GRANT_OAUTH_CLIENT_ID is missing for oauth mode.")
        if not config.oauth_redirect_uri:
            warnings.append("GRANT_OAUTH_REDIRECT_URI is missing for oauth mode.")

    return warnings
