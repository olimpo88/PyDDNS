# Changelog

All notable changes to PyDDNS are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] — 2026-10-29

### Added

- **Two-factor authentication (TOTP)** — optional for every user, enabled from
  the avatar menu (`/common/2fa/`): QR code + manual key, 10 one-time backup
  codes, password required to disable or regenerate. Sign-in becomes two steps
  for accounts that enable it. Built on `django-otp` (per-device throttling),
  plus a per-IP limit and a restart after five wrong codes.
- **`ADMIN_FORCE_2FA`** — `0` by default (nothing changes, existing admins are
  not locked out). `1` sends staff/superusers to enrol right after their
  password and keeps them on the enrolment page until they do. Once enrolled
  they see a confirmation with their backup codes and carry on; they have no
  settings page and cannot disable it.
- **`/admin` honours 2FA** — its own password form is replaced by the app
  sign-in (with `next`), and sessions that must use a second factor are
  verified before entering. Login also accepts a safe same-site `next`.
- **Reset another user's 2FA** — admins can blank a user's two-factor setup
  from the Users list or the edit page (lost phone). The user keeps their
  password and can enrol again; never offered for your own account.
- **`manage.py reset_2fa <username>`** — recovery for a lost authenticator,
  including your own.
- Activity-log actions `2FA_ENABLE`, `2FA_DISABLE`, `2FA_RESET`,
  `2FA_BACKUP_CODES`, `LOGIN_2FA`; strings translated into the 8 locales.

### Changed

- Impersonation keeps the admin's verified state when returning
  (`Return to admin`), and 2FA settings cannot be edited while impersonating.
- The footer and login page show the real version (`PYDDNS_VERSION` in
  settings) instead of a hardcoded `v2.0`.
- New dependencies: `django-otp` 1.7.4, `qrcode` 8.2.

### Not covered

- `Authorization: Token` API requests and `/nic/update` (ddclient) keep their
  own credentials and do not go through the second factor.

## [2.1.0] — 2026-10-29

### Added

- **Password reset by email** — self-service flow with localized emails
  (HTML + plain text in all 8 supported locales). Plugs into Django's
  signed-token mechanism. SMTP via standard `EMAIL_HOST` etc., or zero-config
  console backend in dev.
- **`ALLOW_PASSWORD_RESET` toggle** — operators that prefer admin-controlled
  credentials can disable the entire flow with a single env var. URLs return
  404 and the "Forgot your password?" link disappears from login.
- **Migration pre-flight check** — `scripts/migrate-postgres.sh` now refuses
  to start unless `.env` already declares the variables PyDDNS v2 needs to
  boot (notably `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`, which v1
  deployments don't have). Avoids the "DB migrated but app won't start"
  failure mode.
- **Automatic Django migration reconciliation** — after restoring the
  Postgres data, the migration script now also moves any untracked
  v1-era migration files into `data/migrations-backup-<timestamp>/`
  and re-runs `migrate --fake-initial` so the `django_migrations` table
  aligns with v2's committed `0001_initial`. Fresh installs are unaffected.
- **`Activity_log` retention sweep** — `prune_activity_log` management
  command plus a daily background loop in the python container delete
  rows older than `ACTIVITY_LOG_RETENTION_WEEKS` (default `10`,
  `0` disables). Keeps the table bounded for high-volume deployments
  without operator intervention.
- **Separate Compose overlay for migration** — `docker-compose.migration.yml`
  holds `prep-migration` / `postgres-old` / `migrator`. The main
  `docker-compose.yml` no longer carries any legacy services.
- **Modernized UI** — full template rewrite from the legacy Bootstrap layout
  to a responsive dark theme with amber accents, Inter for UI text and
  JetBrains Mono for technical data (FQDNs, IPs, return codes). Powered by
  Alpine.js for interactivity (toasts, modals, dropdowns) — no SPA build
  pipeline.
- **Admin impersonation** — superusers can "Sign in as" any active user from
  the Users admin. A sticky banner shows who you are and who you're acting
  as, with a one-click "Return to admin". Both start and stop are logged to
  `Activity_log` (`IMPERSONATE_START` / `IMPERSONATE_STOP`).
- **Language picker dropdown** — globe icon, eight locales listed by full
  name with the current selection highlighted. Replaces the inline button
  row that didn't scale beyond a couple of languages.
- **3 additional locales** — `pt-br`, `fr`, `ru` (now 8 total alongside
  `en`/`es`/`de`/`ja`/`zh-hans`).
- **Operator-controlled language lock** — `DJANGO_LANGUAGE_CODE` empty
  enables international mode (browser auto-detect + in-app picker); set
  to a language code to lock the deployment to that language and hide the
  picker. Regional variants (`es-es`, `pt-BR`, `fr-FR`) canonicalize.
- **24h activity sparklines** per subdomain on the dashboard, derived from
  successful `SYNC` entries bucketed by hour.
- **Dashboard stats** — public IP card, subdomain count, syncs in last
  24h, failed in last 24h.
- **Quickstart card** with `ddclient.conf` and `curl` tabs, syntax-highlighted
  and copyable, generated from the user's own subdomains.
- **Demo data seed script** for screenshots / first-run experience.
- **Documentation** — README rewritten with screenshots, expanded
  configuration reference, troubleshooting entries for CSRF/proxy,
  language picker visibility, and Postgres data directory mismatch.

### Changed

- `MIDDLEWARE` now includes `SecurityMiddleware` first (was missing,
  silently disabling all `SECURE_*` settings).
- `LANGUAGE_CODE` defaults to `en` in international mode (was `es-es`).
- `set_language` flow now posts a path-without-locale-prefix as `next`
  so Django's `LocaleMiddleware` re-applies the new language reliably
  (workaround for `translate_url` not rewriting the prefix when the active
  language differs from the source URL).
- Pagination on Users and All-domains admin tables is now 10/page
  (was 6).

### Fixed

- **Critical**: `CSRF_COOKIE_HTTPONLY = True` (introduced during 3.0
  hardening) broke every AJAX POST in the dashboard because the JS
  helper reads `csrftoken` from `document.cookie`. Reverted to the
  Django default; HttpOnly does not improve CSRF protection per
  Django's own docs.
- URL regex `^main/(?P<id_user>.*)` matched the empty string and
  shadowed the named `^main/` pattern, breaking `reverse('main')` and
  any code calling `resolve('/main/')`. Same for `users/` and
  `domains/`. Tightened to `.+`.
- `dologin` returned `redirect: '/common/main/'` (a non-existent URL).
  Now returns `/main/`.
- `Argon2PasswordHasher` was set as the default password hasher in
  production but `argon2-cffi` was not always baked into the image.
  Settings now probe the import at startup and fall back to PBKDF2
  silently when the dep isn't available — the app no longer 500s on
  successful login from a stale image.
- `production.py` did not declare `CSRF_TRUSTED_ORIGINS`, breaking all
  POSTs over HTTPS behind the nginx proxy on Django 5+. Now derived
  automatically from `DJANGO_ALLOWED_HOSTS`.
- `set_ip` resolved the BIND nameserver via a hardcoded
  `socket.gethostbyname('ddns')`, ignoring `DNS_HOST`. This forced
  hidden-master deployments (BIND on a different host) to either run
  Compose with `network_mode: host` or patch the source. Now uses
  `settings.DNS_HOST` like the rest of the DNS API plumbing.
- Database connections were opened and closed per request, which
  exhausted Postgres `max_connections` on fleets of 1000+ clients
  (`FATAL: sorry, too many clients already`). Now uses persistent
  connections via `CONN_MAX_AGE` (default 60s, override with
  `DB_CONN_MAX_AGE`) and `CONN_HEALTH_CHECKS=True` for transparent
  reconnects. `GUNICORN_WORKERS` is also env-configurable so operators
  can size worker count to their device fanout.

### Security

- **Pillow 12.2.0 → 13.0.0** — fixes the reported security advisory.
- **Django 5.2.13 → 5.2.18** — upstream security patch releases (5.2 LTS).
- **gunicorn 23.0.0 → 26.0.0** — the removed `eventlet` worker was not used
  by PyDDNS; stricter HTTP request-target and header validation upstream.
- **requests 2.33.0 → 2.34.1**, **djangorestframework 3.16.0 → 3.17.1**,
  **psycopg2-binary 2.9.10 → 2.9.13**.
- **nginx 1.27 → 1.31** (`docker-compose.yml`); the bundled config validates
  unchanged.
- Dev/CI tooling: pytest 9.1.1, pytest-django 4.12.0, pytest-cov 7.1.0,
  pytest-env 1.6.0.

## [2.0.0] — 2026-04-25

Major modernization release. Stack upgraded end-to-end, security hardened,
test coverage added, deployment automated.

### Breaking changes

- **Postgres 9.6 → 15.** Existing v1 deployments must run
  `./scripts/migrate-postgres.sh` before upgrading; the script preserves the
  9.6 cluster in `data/dbdata-old/` until you confirm the migration.
- **`DJANGO_SECRET_KEY` is now required.** The application refuses to start
  without it. Generate one with
  `docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- **`DJANGO_ALLOWED_HOSTS` is required in production.** Empty value triggers
  a startup error.
- **WSGI server changed from Django dev server to Gunicorn.** Set
  `DJANGO_DEBUG=1` and `DJANGO_SETTINGS_MODULE=pyddns.settings.development`
  to keep auto-reload behavior in development.
- **Settings split.** `pyddns.settings` is now a package with
  `base / development / production` modules. `DJANGO_SETTINGS_MODULE` must
  point at one of the leaves.

### Added

- Argon2id password hashing (PBKDF2 fallback for transitioning legacy hashes)
- HSTS, `SECURE_SSL_REDIRECT`, `SECURE_REFERRER_POLICY`, hardened cookies in production
- nginx hardening: TLS 1.2/1.3 only, modern ciphers, `server_tokens off`, Permissions-Policy
- Per-user brute-force throttle on `/nic/update` (in addition to existing per-IP)
- Input validation on subdomain names (DNS-label regex) and IP addresses
- Container hardening: `cap_drop: ALL`, `no-new-privileges`, `read_only` filesystem
- One-command Postgres 9.6 → 15 migration via Compose profile + `scripts/migrate-postgres.sh`
- `pyddns.settings.development` and `pyddns.settings.production` split
- pytest suite (75+ tests) covering models, views, dyndns2 protocol, settings
- GitHub Actions CI running tests + ruff against Postgres 15
- Healthchecks for `postgres`, `python`, plus `service_healthy` `depends_on` gates
- `requirements-dev.txt` with pytest, pytest-django, ruff
- `SECURITY.md`, `CHANGELOG.md`, redesigned `README.md`

### Changed

- Python 3.7 → 3.11 (multi-stage Dockerfile, non-root `app` user)
- Django 3.x → 5.2 LTS (supported through April 2028)
- nginx pinned to `1.27` (no more floating `latest`)
- All `url(r'...')` migrated to `re_path(r'...')`
- `ugettext_lazy` migrated to `gettext_lazy`
- `LANGUAGES` now matches the locale directories (`es`, `en`, `ja`, `de`, `zh-hans`)
- `LANGUAGE_CODE` and `TIME_ZONE` configurable via `DJANGO_LANGUAGE_CODE` / `DJANGO_TIME_ZONE`
- `dnspython` 1.16 → 2.6 (`resolver.query()` → `resolver.resolve()`)
- BIND HTTP call uses `requests` `params={}` dict (closes parameter pollution risk)
- `Activity_log` now uses timezone-aware `timezone.now()` (was naive `datetime.now()`)
- Real client IP now resolved via private-network proxy trust (closes spoofed-XFF brute-force bypass)

### Removed

- `django-datatables-view` dependency (was unused)
- ~540 lines of dead ExtJS/legacy code from `common/utils.py`
- Hardcoded `SECRET_KEY` in source
- Hardcoded `DEBUG = True` and `ALLOWED_HOSTS = ['*']`
- `wait-for-it.sh` (replaced by Compose healthcheck-gated `depends_on`)
- Forced HTTPS redirect block in nginx (replaced with proper `SECURE_SSL_REDIRECT` via Django)

### Fixed

- `add_user` view caught a non-existent `OstUserEmail.DoesNotExist` exception
  (would `NameError` on invalid `id_user`); now catches `User.DoesNotExist`
- Duplicate `name="login"` in `common/urls.py` made `reverse('common:login')`
  return the wrong URL
- Anonymous users could hit `add_subdomain` and `set_ip_web`, triggering 500s
  on missing IDs (information disclosure / enumeration); now `@login_required`
- Basic Auth credentials were logged in plain text on every `/nic/update`
  request; now redacted (only username, gated by `DEBUG`)
- `SecurityMiddleware` was missing from `MIDDLEWARE`, silently disabling all
  `SECURE_*` settings

### Security

See `SECURITY.md` for the disclosure policy. This release closes 2 critical,
7 high and 8 medium severity findings from an internal audit.

---

[Unreleased]: https://github.com/olimpo88/PyDDNS/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/olimpo88/PyDDNS/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/olimpo88/PyDDNS/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/olimpo88/PyDDNS/releases/tag/v2.0.0
