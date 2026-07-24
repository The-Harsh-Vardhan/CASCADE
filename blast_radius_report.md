# Blast Radius Report — PR #3046
### *fix: tighten permission and validation checks*

> **Target:** [documenso/documenso #3046](https://github.com/documenso/documenso/pull/3046)  
> **Run ID:** `26e8fc39` | **Analysis Mode:** JSON (entity_links.json) | **Pipeline:** v4

---

## TL;DR

- **1 UI page affected** at medium confidence (`/settings/profile` — team profile page)
- **13 functions changed with no traceable impact** — require manual review before closing this PR's test cycle
- **No product requirements directly traced** to changed code; this PR is a security hardening change whose modified functions sit below the tRPC boundary that static analysis can reach

---

## Executive Summary

PR #3046 changed **29 files** across `packages/lib/server-only/`, `packages/trpc/server/`, and `apps/remix/`. The changes tighten permission checks and add URL validation across the document, attachment, recipient, team, and Zapier webhook subsystems.

Of **32 indexed functions** touched by this PR:
- **1 page** (`/settings/profile`) is reachable via the call graph — medium confidence
- **13 functions** are **dark changes** (no traceable path to any UI or requirement)
- **3 requirements** have **no code coverage** in the graph (absent — possibly unimplemented or infrastructure-only)

The dominant finding is that **this PR is a security hardening change**, not a feature change. Most modified functions are deep utility/validation layers (permission gates, URL validators) that the call graph cannot trace upward to product features without more crawl coverage of authenticated flows.

---

## Affected UI / Pages

| Page | Risk | Impact Score | Confidence | Evidence Path |
|---|---|---|---|---|
| `https://app.documenso.com/settings/profile` | **MEDIUM** | 0.50 | 0.57 | `getTeamPublicProfile (get-team-public-profile.ts)` → `page:{sha}` |

> The `/settings/profile` page is reachable from `getTeamPublicProfile`, which was modified in this PR to tighten permission checks. QA should verify the team profile page still loads and saves correctly after this change.

---

## Affected Requirements

*No requirements directly traced to changed code via the call graph.*

> **Why:** The 13 dark-change functions are security/validation utilities called BY tRPC procedures, not calling them. PPR propagates forward (seed → callee), so leaf validation nodes don't reach requirement nodes upstream. This is expected for a permission-hardening PR — the actual risk is in the functions that **call** these validators, which are outside this PR's diff.

---

## ⚫ Dark Changes (13)

These changed functions could not be traced to any UI page or product requirement through the call graph. This is not a bug in the analysis — it means either (a) these functions are pure utility code with no UI surface, or (b) the call chain passes through an abstraction layer (tRPC) that static analysis cannot follow. **All 13 require manual QA review.**

| Function | File | Risk Reason |
|---|---|---|
| `isHttpUrl` | `is-http-url.ts` | New URL validator — verify no legitimate attachment URLs are rejected |
| `forgotPassword` | `forgot-password.ts` | Auth flow — regression risk on password reset |
| `createOrGetShareLink` | `create-or-get-share-link.ts` | Share link generation — verify share links still work |
| `result` (subscribe) | `zapier/subscribe.ts` | Zapier webhook registration — verify webhook setup flow |
| `result` (unsubscribe) | `zapier/unsubscribe.ts` | Zapier webhook removal — verify webhook teardown |
| `createAttachment` | `create-attachment.ts` | Attachment creation — verify file uploads work |
| `deleteAttachment` | `delete-attachment.ts` | Attachment deletion — verify attachment removal works |
| `updateAttachment` | `update-attachment.ts` | Attachment update — verify attachment edit works |
| `findAttachmentsByEnvelopeId` | `find-attachments-by-envelope-id.ts` | Attachment list — verify attachments display |
| `updatedEnvelope` | `cancel-document.ts` | Document cancellation — verify cancel flow |
| `getEnvelopeRecipientRoute` | `get-envelope-recipient.ts` | Recipient lookup — verify recipient data retrieval |
| `member` | `update-organisation-group.ts` | Organisation group update — verify org group management |
| `getRecipientById` | `get-recipient-by-id.ts` | Recipient lookup — verify recipient detail retrieval |

---

## Absent Requirements — No Code Coverage (3)

These requirements exist in the PRD but have no `IMPLEMENTS` edge in the graph. They may be unimplemented, or only reachable via authenticated UI flows not yet crawled:

| Requirement | Status |
|---|---|
| Support for Docker and Docker Compose containerized deployments | ABSENT |
| PostgreSQL database storage with Prisma ORM data modeling and migrations | ABSENT |
| Self-hosted deployment using Docker, Kubernetes, or Railway | ABSENT |

> **Note:** These are infrastructure requirements. They would not be touched by permission/validation code changes. Their absence reflects a gap in the crawl coverage (infrastructure configs are outside the TypeScript code graph), not a risk from this PR.

---

## Recommended QA Actions

Based on this blast radius analysis, the following manual test cases are recommended for the QA team before merging:

1. **Attachment URL validation** — The `isHttpUrl` utility was added to validate attachment URLs. Test that attachment URLs containing only HTTP (not HTTPS) are correctly rejected in the document editor, and that valid HTTPS attachment URLs are still accepted without error.

2. **Attachment popover behavior** — Three attachment functions (`createAttachment`, `updateAttachment`, `deleteAttachment`) were modified with tightened permission checks. Manually verify that attachments can be added, viewed, edited, and removed in each of three contexts: document signing, document management, and the embedded editor.

3. **Permission boundary checks** — Server-side permission logic was tightened in `cancel-document.ts` and `delete-document.ts`. Test that users without the required permissions receive correct error responses (not silent failures or 500 errors) when attempting to cancel or delete documents they don't own.

4. **Zapier webhook subscription** — `subscribe.ts` and `unsubscribe.ts` were modified. Verify that Zapier integration setup and teardown still completes without error — both registering a new webhook and removing an existing one.

5. **Team profile page** (`/settings/profile`) — The only UI element directly traced by the call graph. Verify the team public profile page still loads, saves profile changes, and enforces visibility permissions correctly after the permission-check tightening in `getTeamPublicProfile`.

6. **Password reset flow** — `forgotPassword` was modified. Verify that password reset emails still send and that reset links work end-to-end.

> *3 absent infrastructure requirements (Docker, PostgreSQL, Kubernetes) are not impacted by this PR and require no additional testing.*

---

## Changed Files

| File | Status | +Lines | −Lines |
|---|---|---|---|
| `packages/lib/server-only/document/cancel-document.ts` | modified | +14 | −14 |
| `packages/lib/server-only/document/delete-document.ts` | modified | +23 | −12 |
| `packages/lib/server-only/envelope-attachment/create-attachment.ts` | modified | +9 | −5 |
| `packages/lib/server-only/envelope-attachment/delete-attachment.ts` | modified | +19 | −4 |
| `packages/lib/server-only/envelope-attachment/find-attachments-by-envelope-id.ts` | modified | +9 | −5 |
| `packages/lib/server-only/envelope-attachment/update-attachment.ts` | modified | +19 | −4 |
| `packages/lib/server-only/public-api/get-user-by-token.ts` | **removed** | +0 | −44 |
| `packages/lib/server-only/recipient/get-recipient-by-id.ts` | modified | +22 | −0 |
| `packages/lib/server-only/share/create-or-get-share-link.ts` | modified | +27 | −0 |
| `packages/lib/server-only/team/get-team-public-profile.ts` | modified | +11 | −13 |
| `packages/lib/server-only/team/update-team-public-profile.ts` | modified | +6 | −1 |
| `packages/lib/server-only/user/forgot-password.ts` | modified | +18 | −23 |
| `packages/lib/server-only/webhooks/zapier/subscribe.ts` | modified | +34 | −6 |
| `packages/lib/server-only/webhooks/zapier/unsubscribe.ts` | modified | +26 | −4 |
| `packages/lib/utils/is-http-url.ts` | **added** | +32 | −0 |
| `packages/trpc/server/envelope-router/attachment/create-attachment.types.ts` | modified | +2 | −1 |
| `packages/trpc/server/envelope-router/attachment/update-attachment.types.ts` | modified | +2 | −1 |
| `packages/trpc/server/envelope-router/envelope-recipients/get-envelope-recipient.ts` | modified | +22 | −0 |
| `packages/trpc/server/organisation-router/update-organisation-group.ts` | modified | +18 | −0 |
| `packages/app-tests/e2e/…` (6 new E2E test files) | added | +469 | −0 |

---

## Coverage Statistics

| Metric | Count |
|---|---|
| Seeds (changed indexed functions) | 32 |
| Affected UI elements / pages | 1 |
| Affected requirements (traced) | 0 |
| Absent requirements | 3 |
| Dark changes (no graph path) | 13 |
| Manual review items | 2 |
| IMPLEMENTS edges in graph | 90 |
| RENDERS edges in graph | 80 |

---

*Report generated by Blast Radius Analyzer v4 · Pipeline: Phases 1–6 · Run ID: `26e8fc39`*
