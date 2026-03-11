# Grant Auth Model

Grant supports two operating modes per user environment.

## 1) API Key Mode (default)

Use this mode for fast pilot deployments.

- Each user (or each deployment) owns a separate `.env` file.
- API keys are loaded from environment variables.
- No central identity provider is required.

Recommended for:

- Local development
- Small lab setups
- Early product validation

## 2) OAuth Mode (production-ready path)

Use this mode for shared product deployments.

- Users authenticate through an OAuth/OIDC provider.
- Tokens are stored per user and per tenant.
- Grant can apply tenant-level access control and auditing.

Recommended for:

- Multi-user SaaS
- Institutional deployment
- Compliance-heavy workflows

## Tenant Strategy

- `single_user`: one user context per deployment.
- `multi_tenant`: isolated user/org contexts with separate credentials and outputs.

## Security Baseline

- Never commit `.env` files to Git.
- Store secrets in environment variables or a secret manager.
- Do not print API keys or tokens to logs.
- Rotate keys regularly.

## Runtime Integration

Grant reads auth settings through `config/auth_config.py`.

Config source order:

1. Process environment variables
2. Optional env file values (`--auth-env-file`)

Environment values take priority over file values.
