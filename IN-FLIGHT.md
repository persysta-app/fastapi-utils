# fastapi-utils — In-flight work

> Fonte de verdade da fase ativa da lib. Sessions Claude Code dos
> consumers (Persysta, Vinon) leem isso na pre-flight antes de tocar
> arquivos em hot zone. Ver protocolo em [CLAUDE.md](CLAUDE.md).

---

## 🚀 Fase ativa

### Fase 0 — v0.1.0 release (em curso, 2026-05-08)

**Status:** PR aberto, aguardando CI + tag

**Escopo:**
- Bootstrap repo + structure
- 5 módulos: errors, mixins, sentry, rate_limit, email
- Tests pra cada módulo
- CI workflow + tag v0.1.0

**Branch:** `feat/v0.1.0-bootstrap`

### Próximas fases

- **Fase 1** — Vinon integra v0.1.0 (errors + mixins; sentry + rate_limit; email opcional pra Sprint 1.20)
- **Fase 2** — Persysta integra v0.1.0 (errors + mixins; sentry + rate_limit; email opcional)

## 🔒 Hot zones reservadas nos consumers (durante Fases 0-2)

| Consumer | Arquivo | Tipo de freeze |
|---|---|---|
| Vinon | `backend/app/core/errors.py` | Total |
| Vinon | `backend/app/db/mixins.py` | Total |
| Vinon | `backend/app/services/email.py` | Opcional (decisão user) |
| Vinon | `backend/requirements.txt` | Adição |
| Persysta | `backend/app/core/errors.py` | Total |
| Persysta | `backend/app/db/mixins.py` | Parcial (`AccountScopedMixin` + `AuditMixin` ficam locais) |
| Persysta | `backend/app/services/email.py` | Opcional (decisão user) |
| Persysta | `backend/requirements.txt` | Adição |

Se outra session precisar tocar uma dessas zonas, declara no IN-FLIGHT
do consumer; cross-dev rebaseia.

## Convenções

- Branches: `feat/v0.X-foo`, `fix/foo`, `chore/foo`
- PRs pra `main` + merge depois de CI verde
- Bump version = commit separado, tag = depois de merge no main
