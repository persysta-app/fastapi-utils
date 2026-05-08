# fastapi-utils (persysta-platform-fastapi-utils)

Shared utility lib for **Persysta** + **Vinon** FastAPI backends.
Companion to [`auth-fastapi`](https://github.com/persysta-app/auth-fastapi).

## Status

- **v0.1.0** (2026-05-08) — bootstrap with 5 modules: errors, mixins,
  sentry, rate_limit, email.

## Coordenação cross-projeto

Mesmo protocolo de [auth-fastapi/CLAUDE.md](../auth-fastapi/CLAUDE.md).
3 sessions Claude Code ativas:
- Eu (este repo) — autoria + integração nos 2 consumers
- Persysta dev (`C:/dev/persysta`) — work próprio
- Vinon dev (`C:/dev/vinon`) — work próprio

Comunicação assíncrona via IN-FLIGHT.md em cada repo. Antes de tocar hot
zones nos consumers (`backend/app/core/errors.py`,
`backend/app/db/mixins.py`, `backend/app/services/email.py`,
`backend/requirements.txt`), declarar nos IN-FLIGHTs deles.

## Stack

- Python 3.10+
- pyproject.toml + hatchling
- Deps obrigatórias: fastapi, sqlalchemy, httpx
- Deps opcionais: sentry-sdk (extras: `[sentry]`), slowapi (extras: `[rate-limit]`)
- Tests: pytest + pytest-asyncio
- CI: GitHub Actions (.github/workflows/ci.yml)

## Comandos

```bash
# Install dev mode com TODAS as deps opcionais (sentry + slowapi)
pip install -e ".[dev]"

# Tests
pytest -v

# Lint
ruff check src tests

# Release
# 1. Bump pyproject.toml version
# 2. PR + merge
# 3. git tag vX.Y.Z && git push origin vX.Y.Z
# 4. Sync requirements.txt nos consumers
```

## Convenções

- Branches: `feat/v0.X-foo`, `fix/foo`, `chore/foo`
- Commits PT-BR descritivos com `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- API pública NÃO quebra entre patches. Mudanças breaking = minor bump
  pré-1.0 (v0.2 → v0.3), major depois (v1 → v2).
