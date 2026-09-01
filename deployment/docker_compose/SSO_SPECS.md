# SSO SAML SETUP FEATURE SPEC

## Goal

Build a Community Edition SSO setup flow for SAML. Use only existing CE code paths under `backend/onyx` and non-EE frontend paths. Do not copy, move, or depend on code under `backend/ee` or `web/src/ee`. Do not remove or bypass license gates.

Primary demo IdP: Mock SAML at `https://mocksaml.com/`.

The UI must be self-explanatory for admins. An admin should be able to open the SSO setup page, see sample Mock SAML values, save a provider, test login, and understand callback/entity URLs.

Focus on SAML. OIDC can be mentioned as future/secondary, but the implementation should not try to solve OIDC unless explicitly requested later.

## Existing CE Areas To Inspect First

Backend:

- `backend/onyx/server/saml.py`
- `backend/onyx/server/saml_multi.py`
- `backend/onyx/db/saml.py`
- `backend/onyx/db/sso_provider.py`
- `backend/onyx/server/sso_discovery.py`
- `backend/onyx/server/manage/sso/api.py`
- `backend/onyx/db/models.py`
- `backend/onyx/db/enums.py`
- `backend/onyx/main.py`

Frontend:

- `web/src/app/admin/**`
- `web/src/views/admin/**`
- `web/src/lib/auth/**`
- `web/src/lib/sso/**`
- `web/src/app/auth/**`
- `web/src/i18n/messages/*.json`
- `web/src/sections/sidebar/AdminSidebar.tsx`

Before coding, verify which SSO admin API endpoints already exist in CE and what payloads they accept. Prefer extending those endpoints over creating parallel APIs.

## Legal/License Boundary

Do not use EE code.

Allowed:

- Use CE SAML/OIDC/SSO backend code under `backend/onyx`.
- Add new CE frontend UI under non-EE paths.
- Add CE schemas/helpers/tests.

Forbidden:

- Copying from `backend/ee` or `web/src/ee`.
- Moving EE UI/API code into CE.
- Setting `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true` as part of the feature.
- Removing license/tier checks.

## Product Requirements

Add an Admin SSO page or SSO setup modal that supports SAML configuration.

Admin must be able to configure:

- Provider name/slug, default `mocksaml`
- Display name, default `Mock SAML`
- Enabled flag
- Allowed email domains, optional
- IdP Entity ID
- IdP SSO URL
- IdP x509 certificate
- SP Entity ID
- SP ACS/callback URL display
- Optional email attribute name
- Optional SP signing certificate/private key if supported by existing backend config

Show copyable computed URLs:

- ACS/callback URL: `${WEB_DOMAIN}/auth/saml/callback`
- Login URL: `/api/auth/saml/{provider_name}/authorize`
- SP Entity ID: default based on `${WEB_DOMAIN}` and provider name

The UI should explain:

- What value comes from IdP metadata.
- What value must be pasted into the IdP.
- Why allowed domains matter.
- How to test with Mock SAML.
- How to recover if SSO setup fails.

## Mock SAML Defaults

Use Mock SAML as the in-product example.

Default/sample values must be clearly marked as sample values and editable.

Recommended defaults:

- Provider name: `mocksaml`
- Display name: `Mock SAML`
- IdP metadata URL: `https://mocksaml.com/api/saml/metadata`
- IdP SSO URL: `https://mocksaml.com/api/saml/sso`
- IdP Entity ID: use the entity ID from Mock SAML metadata after verifying it live or documenting that admins should paste from metadata.
- Email attribute: blank by default, with guidance that Onyx tries common email keys.
- Allowed email domains: blank by default.

Do not hardcode unverified certificates from the internet in source. If metadata import is implemented, fetch and parse metadata at runtime/server-side with URL validation. If metadata import is not implemented, show instructions for copying the certificate from Mock SAML metadata.

## Backend Requirements

Use existing SSO provider persistence if present.

Expected backend behavior:

- Admin-only list/create/update/delete/enable SSO providers.
- Validate provider name as URL-safe slug.
- Validate provider type is `saml` for SAML form.
- Validate SAML config with the existing `SAMLProviderConfig` model or equivalent CE model.
- Store secret fields encrypted/masked on read.
- Never return SP private key in plain text after save.
- Validate IdP URLs with existing outbound URL validation.
- Validate x509 certificate shape enough to catch obvious paste errors.
- Normalize allowed email domains.
- Support test/auth URL generation without saving secrets in query params.
- Surface safe user-facing errors for bad metadata, missing email claim, bad signature, disabled provider, or domain rejection.

Security requirements:

- ACS must validate SAML signatures through existing OneLogin library flow.
- Do not trust unsigned attributes.
- Do not trust RelayState unless it is an internal path.
- Do not use request Host/X-Forwarded headers to build ACS URLs. Use trusted `WEB_DOMAIN`.
- Enforce admin permission on management endpoints.
- Rate-limit or at least avoid adding unauthenticated expensive metadata fetch endpoints.
- Do not log SAML assertions, private keys, or full cert blobs.

Reliability requirements:

- Disabled provider cannot be used for login.
- Bad provider config fails closed.
- IdP-initiated SAML must resolve by issuer only after signature validation uses matching cert.
- Existing users with web-login account type can be reused by email.
- New SAML users should be created verified through existing `upsert_saml_user` behavior.
- Errors redirect to the web error page where existing code supports it.

## Frontend Requirements

Build a clear admin setup UI.

Suggested structure:

- Admin > SSO page or Organization > SSO card.
- Empty state explaining SAML setup.
- Provider list with enabled/disabled status.
- Create/Edit SAML modal or page.
- Mock SAML quick-start panel.
- Copy buttons for ACS URL and login URL.
- Test sign-in button that opens the authorize URL.

Form sections:

- Provider identity
- Service provider values to copy into IdP
- Identity provider values to paste into Onyx
- Access restrictions
- Advanced signing fields

The UI must preserve existing design system patterns. Use existing admin settings layout/components. Add i18n keys for all text.

Avoid UI-only security. Backend must enforce all critical checks.

## Optional Metadata Import

If small and safe, add metadata import.

Flow:

- Admin enters metadata URL.
- Backend validates URL and fetches metadata.
- Backend parses IdP Entity ID, SSO URL, and x509 cert.
- Backend returns parsed values to frontend for review before save.

Constraints:

- Use SSRF-safe URL validation.
- Time out HTTP requests.
- Limit response size.
- Do not persist fetched values until admin saves.
- Reject metadata without exactly the needed values.

If metadata import becomes large, skip it and ship manual paste with Mock SAML instructions.

## Database/Migrations

Before adding migrations, inspect current `SSOProvider` and related tables.

If existing schema supports all fields, do not add a migration.

Only add migration if a required product field cannot be represented.

Never store secrets outside encrypted columns/config wrappers.

## Test Plan

Prefer integration where feasible, but use focused unit tests for pure parsing/validation.

Backend tests:

- SAML provider config validation accepts valid Mock SAML-shaped config.
- Invalid provider slug rejected.
- Invalid URL rejected.
- Secret fields masked on read.
- Disabled provider cannot authorize.
- RelayState sanitizer rejects external URLs and accepts internal paths.
- Allowed email domain enforcement rejects mismatched domain.

Frontend tests:

- SAML setup form renders sample Mock SAML defaults.
- Save payload includes provider type `saml` and expected config shape.
- Existing provider edit preserves masked secret fields unless changed.
- Copyable URLs render from backend response/config.

Manual smoke test:
1. Start Onyx locally.
2. Configure SAML provider using Mock SAML metadata/values.
3. Open generated login URL.
4. Complete Mock SAML login.
5. Verify Onyx user is created/logged in.
6. Verify logs do not contain assertion/private key material.

## Demo Risk Areas To Watch

This feature is intentionally broad enough to show common vibe-coding failures:

- UI saves secrets but backend returns them unmasked.
- Frontend hides fields but backend accepts unsafe values.
- ACS URL built from untrusted Host header.
- RelayState open redirect.
- Metadata fetch SSRF.
- Missing admin permission on provider management.
- Disabled provider still usable.
- Domain restriction enforced only in UI.
- Certificate paste stored in logs.
- IdP-initiated SAML accepts issuer before validating signature correctly.
- Existing user takeover by unverified email claim.
- Multi-tenant ambiguity if SAML is enabled where unsupported.
- Poor recovery path causing admin lockout.

## Verification Commands

Run targeted backend tests added by the implementation:

```bash
uv run pytest -q backend/tests/unit/onyx/server/sso backend/tests/unit/onyx/server/saml
```

Run targeted frontend checks if dependencies are available:

```bash
cd web
bun run types:check
bun run lint
```

Run Docker smoke if the environment supports it:

```bash
cd deployment/docker_compose
docker compose up --build
```

## Deliverable

Return a concise summary with:

- Files changed.
- SAML setup flow.
- Mock SAML values used.
- Security controls added.
- Tests run.
- Known gaps.
