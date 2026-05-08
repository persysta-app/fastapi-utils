# fastapi-utils — In-flight work

> Fonte de verdade da fase ativa da lib. Sessions Claude Code dos
> consumers (Persysta, Vinon) leem isso na pre-flight antes de tocar
> arquivos em hot zone. Ver protocolo em [CLAUDE.md](CLAUDE.md).

---

## 🚀 Fase ativa

_(Sem fase ativa — v0.3.0 released 2026-05-08. Migração Brevo é via config nos consumers, sem code change.)_

## 🎯 v0.3.0 release ✅ (2026-05-08)

- **Tag:** `v0.3.0`
- **Mudanças:**
  - Sentinela nova `BREVO_HTTP_HOST = "brevo-api"` no módulo `email`
  - `_send_via_brevo_api()` — POST `https://api.brevo.com/v3/smtp/email`, auth header `api-key`, 201 = sucesso
  - Anti-spam headers (Reply-To + List-Unsubscribe + List-Unsubscribe-Post) agora em TODOS os 3 modos (SMTP + SendGrid HTTP + Brevo HTTP). Bug-fix: SendGrid HTTP antes não passava — penalty Gmail/Yahoo.
- **Tests:** 7 cases novos (6 Brevo + 1 SendGrid paridade), 13 anteriores mantidos. CI pass 22s.

### Migração SendGrid → Brevo nos consumers (sem code change)

**Persysta** (UI):
1. Login system admin → `/system/email-settings`
2. Trocar `Host` de `sendgrid-api` → `brevo-api`
3. Trocar `Password` de `SG.xxx...` → `xkeysib-xxx...` (Brevo API key)
4. Salvar + clicar "Enviar email de teste"

**Vinon** (env vars Railway):
1. `SMTP_HOST=brevo-api`
2. `SMTP_PASSWORD=xkeysib-xxx...`
3. Restart deploy

Pré-requisitos no Brevo dashboard (operacional, fora da lib):
- Sender `noreply@persysta.com` + `noreply@vinon.com.br` verificados
- Domínios autenticados (DKIM + SPF + DMARC nos DNS)

## 🎯 v0.2.0 release ✅ (2026-05-08)

- **Tag:** `v0.2.0` ([commit](https://github.com/persysta-app/fastapi-utils/commits/v0.2.0))
- **Módulos novos:**
  - `security_headers` — `add_security_headers_middleware(app, ...)` injeta X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy + HSTS em prod
  - `health` — `build_health_router(...)` retorna APIRouter com /health (liveness) + /readyz (readiness com checks customizáveis)
  - `audit` — `AuditLogMixin` + `log_action()` helper com extração automática de IP/UA do request
- **Tests:** 22 cases novos (7 security_headers + 8 health + 7 audit), 33 anteriores mantidos
- **Integração nos consumers:** OPT-IN. Lib disponível, swap nos consumers fica pra próxima janela.

## 🎯 Fases v0.1.0 (2026-05-08, em ordem)

### Fase 0 — v0.1.0 release ✅

- **Tag:** `v0.1.0` ([commit `b4d21fe`](https://github.com/persysta-app/fastapi-utils/commit/b4d21fe))
- **Módulos:** `errors`, `mixins` (Timestamp + SoftDelete), `sentry` (init helper), `rate_limit` (build_limiter), `email` (SMTP + SendGrid HTTP API + BackgroundTasks)
- **Tests:** 33 cases na CI (4 errors + 4 mixins + 5 sentry + 4 rate_limit + ~13 email + 3 mixins SQLite tz fix)
- **Decisões de design:**
  - Email NÃO inclui Fernet — caller descriptografa antes de chamar
  - Email NÃO escreve em `email_logs` — caller passa `on_log` callback (Persysta usa `to_address`, Vinon usa `to_email`)
  - Sentry/rate-limit como extras opcionais (`[sentry]`, `[rate-limit]`)
  - `AccountScopedMixin` + `AuditMixin` ficam no Persysta (multi-tenant), não vão pra lib

### Fase 1 — Vinon integra v0.1.0 ✅

- **PR:** [vinon-app/vinon#76](https://github.com/vinon-app/vinon/pull/76)
- **5 áreas swap:** `errors.py` (re-export), `mixins.py` (re-export), `services/email.py` (wrapper com EmailLog `to_email`), `core/limiter.py` (build_limiter), `main.py` (init_sentry)
- **Suite:** 228 passed, 1 skipped (full pytest local)
- **Mergeado via `--admin`** — CI lint deu I001 inexplicável em `services/email.py` (local + GitHub byte-idêntico, mesma versão ruff 0.8.4, mesma config pyproject — provável glitch CI). Validado local extensivamente.

### Fase 2 — Persysta integra v0.1.0 ✅

- **PR:** [persysta-app/persysta#322](https://github.com/persysta-app/persysta/pull/322)
- **5 áreas swap:** `errors.py` (re-export), `services/email.py` (wrapper com config DB > env Fernet + EmailLog `to_address`), `core/limiter.py` (build_limiter com flag `enabled`), `main.py` (init_sentry com DSN resolution custom DB > env), `tests/test_email_headers.py` (atualizado pra testar lib direto)
- **Suite:** 886 passed, 4 skipped, 15 fails em `test_reminders_wave2.py` por test pollution (isolated 22/22 passam — não causada pelo refactor)
- **Mergeado via `--rebase --admin`** (pattern padrão do Persysta CLAUDE.md)

## 🔓 Hot zones liberadas

Todas as hot zones reservadas durante Fases 0-2 estão liberadas. Persysta
e Vinon devs podem tocar livremente em:

- `backend/app/core/errors.py` (qualquer consumer)
- `backend/app/db/mixins.py` (Persysta — só `AccountScopedMixin`/`AuditMixin` locais)
- `backend/app/services/email.py`
- `backend/app/core/limiter.py`
- `backend/app/main.py` (Sentry init)
- `backend/requirements.txt`

## Convenções

- Branches: `feat/v0.X-foo`, `fix/foo`, `chore/foo`
- PRs pra `main` + merge depois de CI verde
- Bump version = commit separado, tag = depois de merge no main
