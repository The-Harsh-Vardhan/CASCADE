# Blast Radius Report -- PR #3046

**PR:** [fix: tighten permission and validation checks](https://github.com/documenso/documenso/pull/3046)  
**Mode:** json  **Run ID:** `e197c8ef`

---

## Executive Summary

This pull request updates document attachment popovers across the signing experience, document management views, and the embedded editor, along with end-to-end tests for attachment URL validation and visibility access permissions. QA should focus verification on attachment popups and links across these workflows, noting that 12 changes are untraceable to existing features and 6 requirements currently lack code coverage.

---

## Changed Files

| File | Status | +/− |
|---|---|---|
| `apps/remix/app/components/general/document-signing/document-signing-attachments-popover.tsx` | modified | +2/−1 |
| `apps/remix/app/components/general/document/document-attachments-popover.tsx` | modified | +3/−2 |
| `apps/remix/app/components/general/document/embedded-editor-attachment-popover.tsx` | modified | +3/−2 |
| `packages/app-tests/e2e/documents/document-visibility-access.spec.ts` | added | +89/−0 |
| `packages/app-tests/e2e/envelope-editor-v2/attachment-url-validation.spec.ts` | added | +70/−0 |
| `packages/app-tests/e2e/envelope-editor-v2/attachment-visibility-access.spec.ts` | added | +121/−0 |
| `packages/app-tests/e2e/organisations/organisation-permission-hierarchy.spec.ts` | modified | +64/−0 |
| `packages/app-tests/e2e/recipient/recipient-visibility-access.spec.ts` | added | +72/−0 |
| `packages/app-tests/e2e/teams/team-profile-access.spec.ts` | added | +53/−0 |
| `packages/lib/server-only/document/cancel-document.ts` | modified | +14/−14 |
| `packages/lib/server-only/document/delete-document.ts` | modified | +23/−12 |
| `packages/lib/server-only/envelope-attachment/create-attachment.ts` | modified | +9/−5 |
| `packages/lib/server-only/envelope-attachment/delete-attachment.ts` | modified | +19/−4 |
| `packages/lib/server-only/envelope-attachment/find-attachments-by-envelope-id.ts` | modified | +9/−5 |
| `packages/lib/server-only/envelope-attachment/update-attachment.ts` | modified | +19/−4 |
| `packages/lib/server-only/public-api/get-user-by-token.ts` | removed | +0/−44 |
| `packages/lib/server-only/recipient/get-recipient-by-id.ts` | modified | +22/−0 |
| `packages/lib/server-only/share/create-or-get-share-link.ts` | modified | +27/−0 |
| `packages/lib/server-only/team/get-team-public-profile.ts` | modified | +11/−13 |
| `packages/lib/server-only/team/update-team-public-profile.ts` | modified | +6/−1 |
| `packages/lib/server-only/user/forgot-password.ts` | modified | +18/−23 |
| `packages/lib/server-only/webhooks/zapier/subscribe.ts` | modified | +34/−6 |
| `packages/lib/server-only/webhooks/zapier/unsubscribe.ts` | modified | +26/−4 |
| `packages/lib/utils/is-http-url.test.ts` | added | +45/−0 |
| `packages/lib/utils/is-http-url.ts` | added | +32/−0 |
| `packages/trpc/server/envelope-router/attachment/create-attachment.types.ts` | modified | +2/−1 |
| `packages/trpc/server/envelope-router/attachment/update-attachment.types.ts` | modified | +2/−1 |
| `packages/trpc/server/envelope-router/envelope-recipients/get-envelope-recipient.ts` | modified | +22/−0 |
| `packages/trpc/server/organisation-router/update-organisation-group.ts` | modified | +18/−0 |

## Affected UI / Pages (1)

### 🟡 Medium Confidence

- **https://app.documenso.com/settings/profile** (impact: 1.00)

## Affected Requirements (101)

### Low Risk (verify before updating test plans)

- **Ensure each backup recovery code can only be used once to regain account access when losing authenticator app access.**
  - Confidence: 0.31
  - Evidence path: forgotPassword (forgot-password.ts) -> Ensure each backup recovery code can only be used once to regain account access when losing authenticator app access.

- **The system must trigger a webhook notification with payload event 'DOCUMENT_CANCELLED' when a document owner or team member deletes or cancels a document.**
  - Confidence: 0.38
  - Evidence path: cancelDocument (cancel-document.ts) -> The system must trigger a webhook notification with payload event 'DOCUMENT_CANCELLED' when a document owner or team member deletes or cancels a document.

- **Allow users to delete draft/pending documents or hide completed documents with appropriate confirmation and notification side effects.**
  - Confidence: 0.37
  - Evidence path: cancelDocument (cancel-document.ts) -> Allow users to delete draft/pending documents or hide completed documents with appropriate confirmation and notification side effects.

- **Automatically expire recipient signing links upon completion or deletion of the document.**
  - Confidence: 0.35
  - Evidence path: cancelDocument (cancel-document.ts) -> Automatically expire recipient signing links upon completion or deletion of the document.

- **Support team email address configuration to enable team inbox, sending documents on behalf of the team identity, document tracking, and unified recipient branding.**
  - Confidence: 0.67
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Support team email address configuration to enable team inbox, sending documents on behalf of the team identity, document tracking, and unified recipient branding.

- **Enable users to showcase active direct link templates on their public Documenso profile page for visitors to sign.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Enable users to showcase active direct link templates on their public Documenso profile page for visitors to sign.

- **Provide administrative controls in Team Settings to define default preferences for new documents created within the team.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide administrative controls in Team Settings to define default preferences for new documents created within the team.

- **Allow teams to customize email notification behavior for team document events.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow teams to customize email notification behavior for team document events.

- **Allow users to update their Full Name field in Settings > Profile, which updates the name shown on documents and recipient email notifications.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to update their Full Name field in Settings > Profile, which updates the name shown on documents and recipient email notifications.

- **Restrict document creation via API to a maximum of 5 documents per month for Free account tiers.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Restrict document creation via API to a maximum of 5 documents per month for Free account tiers.

- **Allow users to upload a custom profile avatar image (PNG or JPG format, maximum 1MB) from Settings > Profile, which appears on sent documents and public profiles.**
  - Confidence: 0.61
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to upload a custom profile avatar image (PNG or JPG format, maximum 1MB) from Settings > Profile, which appears on sent documents and public profiles.

- **Allow users to register a device-specific passkey using biometrics, hardware keys, or password managers for login and document signing.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to register a device-specific passkey using biometrics, hardware keys, or password managers for login and document signing.

- **Allow team admins to set default document visibility settings for newly created documents within team settings.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow team admins to set default document visibility settings for newly created documents within team settings.

- **Allow teams to set up webhooks for integrating document events with external services.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow teams to set up webhooks for integrating document events with external services.

- **Allow users with active 2FA to authenticate with a TOTP code to view their account backup recovery codes.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users with active 2FA to authenticate with a TOTP code to view their account backup recovery codes.

- **Control document viewing and signing permissions requiring recipient account sign-in or two-factor authentication.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Control document viewing and signing permissions requiring recipient account sign-in or two-factor authentication.

- **Support placeholder emails in templates to be replaced with actual recipient details when generating documents.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Support placeholder emails in templates to be replaced with actual recipient details when generating documents.

- **Restrict direct link functionality to document templates, preventing direct links on standalone single documents.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Restrict direct link functionality to document templates, preventing direct links on standalone single documents.

- **Automatically surface signed direct link documents in a user's dashboard if they hold a Documenso account matching the entered email.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Automatically surface signed direct link documents in a user's dashboard if they hold a Documenso account matching the entered email.

- **Enable TOTP-based two-factor authentication (2FA) using an authenticator app for account login and high-compliance signatures.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Enable TOTP-based two-factor authentication (2FA) using an authenticator app for account login and high-compliance signatures.

- **The platform must allow senders to set document language code and configure custom email settings, subject, and message.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The platform must allow senders to set document language code and configure custom email settings, subject, and message.

- **Restrict password change UI visibility to accounts created via email/password authentication.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Restrict password change UI visibility to accounts created via email/password authentication.

- **Override template-level settings when creating a document, including title, email communications, localized formatting, and signature input modes.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Override template-level settings when creating a document, including title, email communications, localized formatting, and signature input modes.

- **Configure default email preferences at the organisation level with team-level override capabilities.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Configure default email preferences at the organisation level with team-level override capabilities.

- **Allow users with password-based accounts to change their account password from the Security settings tab.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users with password-based accounts to change their account password from the Security settings tab.

- **Allow settings configuration for managing the public profile and presence of the team.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow settings configuration for managing the public profile and presence of the team.

- **Allow senders to specify a custom Reply-To email address so recipient responses are directed to a non-default inbox.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow senders to specify a custom Reply-To email address so recipient responses are directed to a non-default inbox.

- **The system must send automated transactional emails for signing invitations, signature completion, and document updates using react-email templates.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The system must send automated transactional emails for signing invitations, signature completion, and document updates using react-email templates.

- **The application must persist user account data, document metadata, signatures, and configuration settings in a PostgreSQL database managed via Prisma ORM.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The application must persist user account data, document metadata, signatures, and configuration settings in a PostgreSQL database managed via Prisma ORM.

- **Display the user's email address as a read-only field on the profile settings page, requiring support contact for changes.**
  - Confidence: 0.56
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Display the user's email address as a read-only field on the profile settings page, requiring support contact for changes.

- **Require a valid recipient email address for document invitation delivery.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Require a valid recipient email address for document invitation delivery.

- **Allow invited users to accept an organisation invitation via email link after signing in or creating an account.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow invited users to accept an organisation invitation via email link after signing in or creating an account.

- **Allow users to initiate document creation from a template via the sidebar templates list context menu or the template detail page.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to initiate document creation from a template via the sidebar templates list context menu or the template detail page.

- **Document senders can add one or more recipients to a document by entering their full name and email address.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Document senders can add one or more recipients to a document by entering their full name and email address.

- **The platform strictly accepts PDF documents for sending and creation, without converting non-PDF file formats automatically.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The platform strictly accepts PDF documents for sending and creation, without converting non-PDF file formats automatically.

- **Documenso must trigger webhook notifications for actions performed on templates, including creation, updates, deletion, and usage.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Documenso must trigger webhook notifications for actions performed on templates, including creation, updates, deletion, and usage.

- **Users can click the 'Upload Document' button in the Documents dashboard to open a native file selection dialog.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Users can click the 'Upload Document' button in the Documents dashboard to open a native file selection dialog.

- **Allow users to revoke an active API token from the settings interface to immediately invalidate its access.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to revoke an active API token from the settings interface to immediately invalidate its access.

- **Allow Enterprise organizations to configure custom domain sender email addresses from organization settings.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow Enterprise organizations to configure custom domain sender email addresses from organization settings.

- **Allow team administrators to update Team Name, Team URL, Team Avatar, and Team Email under General Team Settings.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow team administrators to update Team Name, Team URL, Team Avatar, and Team Email under General Team Settings.

- **Allow users to access the document editor from the dashboard or automatically after completing a document upload.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to access the document editor from the dashboard or automatically after completing a document upload.

- **Allow teams to set a brand website URL linked to the logo and set custom brand details displayed in email footers.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow teams to set a brand website URL linked to the logo and set custom brand details displayed in email footers.

- **Enforce team role access levels (Admin, Manager, Member) for team settings, member management, team deletion, and document visibility.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Enforce team role access levels (Admin, Manager, Member) for team settings, member management, team deletion, and document visibility.

- **Allow users to create a custom signature during document signing without modifying their default profile signature.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to create a custom signature during document signing without modifying their default profile signature.

- **Provides an interface listing active API tokens along with their scope, target account/team, and expiration details.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provides an interface listing active API tokens along with their scope, target account/team, and expiration details.

- **Specify field coordinates and dimensions on PDF documents using relative percentage values (0-100) along with 1-based page numbers and 0-based document file indices.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Specify field coordinates and dimensions on PDF documents using relative percentage values (0-100) along with 1-based page numbers and 0-based document file indices.

- **Allow modifying recipient name, email, role, and signing order prior to sending the document.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow modifying recipient name, email, role, and signing order prior to sending the document.

- **Provide general document configuration options in editor sidebar including language, signature types, date format, time zone, external ID, and redirect URL.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide general document configuration options in editor sidebar including language, signature types, date format, time zone, external ID, and redirect URL.

- **Recipients click email link to open document viewer and fill/sign assigned fields.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Recipients click email link to open document viewer and fill/sign assigned fields.

- **Add and manage recipient roles for documents generated from a template.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Add and manage recipient roles for documents generated from a template.

- **Enforce member limits and team creation restrictions based on current subscription plan (Platform, Teams, Enterprise).**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Enforce member limits and team creation restrictions based on current subscription plan (Platform, Teams, Enterprise).

- **Provide a drawing interface in the profile signature editor allowing users to draw a signature using a mouse or touchscreen.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide a drawing interface in the profile signature editor allowing users to draw a signature using a mouse or touchscreen.

- **Update general template properties and email/redirect metadata.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Update general template properties and email/redirect metadata.

- **Allow users to upload an image file of their signature in the profile signature editor.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to upload an image file of their signature in the profile signature editor.

- **Provide a Send Document button within the editor to initiate distribution and open email or link setup options.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide a Send Document button within the editor to initiate distribution and open email or link setup options.

- **Open and update an existing template's recipients, fields, or settings.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Open and update an existing template's recipients, fields, or settings.

- **The system must integrate with Stripe to manage payment processing, cloud subscriptions, and enterprise account billing.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The system must integrate with Stripe to manage payment processing, cloud subscriptions, and enterprise account billing.

- **Allow users to specify an optional secret key during webhook setup to sign event payloads with the X-Documenso-Secret header for endpoint security verification.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to specify an optional secret key during webhook setup to sign event payloads with the X-Documenso-Secret header for endpoint security verification.

- **Senders can track real-time recipient status and document progress from the Documents dashboard.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Senders can track real-time recipient status and document progress from the Documents dashboard.

- **Enforce organisation-level roles (Owner, Admin, Manager, Member) and their respective permissions for managing settings, teams, members, billing, and organisation deletion.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Enforce organisation-level roles (Owner, Admin, Manager, Member) and their respective permissions for managing settings, teams, members, billing, and organisation deletion.

- **The system must allow users to upload PDF documents into the application, storing them securely in S3-compatible object storage for viewing and signature processing.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The system must allow users to upload PDF documents into the application, storing them securely in S3-compatible object storage for viewing and signature processing.

- **Allow teams to enable custom branding or inherit branding settings from the parent organisation.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow teams to enable custom branding or inherit branding settings from the parent organisation.

- **Send email notifications to recipients when an envelope is distributed, providing a direct link to sign or view the document.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Send email notifications to recipients when an envelope is distributed, providing a direct link to sign or view the document.

- **Capture email and optional display name for each defined recipient slot when generating a document from a template.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Capture email and optional display name for each defined recipient slot when generating a document from a template.

- **Ensure generated documents become independent entities, allowing pre-send modifications without altering the original template.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Ensure generated documents become independent entities, allowing pre-send modifications without altering the original template.

- **Allow teams to upload a custom branding logo (up to 5MB in JPG, PNG, or WebP format) to display on document signing pages.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow teams to upload a custom branding logo (up to 5MB in JPG, PNG, or WebP format) to display on document signing pages.

- **Allow users to initiate creating a reusable document template from the Templates section.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to initiate creating a reusable document template from the Templates section.

- **Configure default document preferences at the organisation level with team-level override capabilities.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Configure default document preferences at the organisation level with team-level override capabilities.

- **Provide a typed signature generator in the profile signature editor allowing users to enter their name and select from generated font styles.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide a typed signature generator in the profile signature editor allowing users to enter their name and select from generated font styles.

- **Allow users to write a custom message for recipient emails utilizing dynamic template variables.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to write a custom message for recipient emails utilizing dynamic template variables.

- **Provide functionality to generate and manage API tokens scoped to the team for programmatic access.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide functionality to generate and manage API tokens scoped to the team for programmatic access.

- **Allow team creator to set whether all organisation members get automatic access to the team's documents or restrict initial access to organisation admins and managers.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow team creator to set whether all organisation members get automatic access to the team's documents or restrict initial access to organisation admins and managers.

- **The system must allow senders to configure custom display timezone and date format preferences for dates appearing on documents.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The system must allow senders to configure custom display timezone and date format preferences for dates appearing on documents.

- **Provide a user interface within Team Settings allowing team administrators to configure a new HTTP/HTTPS webhook endpoint.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Provide a user interface within Team Settings allowing team administrators to configure a new HTTP/HTTPS webhook endpoint.

- **List all documents generated from a specific template on the template detail page.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> List all documents generated from a specific template on the template detail page.

- **Allow users to remove their existing profile avatar image by hovering over the avatar display in Settings > Profile.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to remove their existing profile avatar image by hovering over the avatar display in Settings > Profile.

- **Allow users to disable active two-factor authentication by verifying a 6-digit code from their authenticator app.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to disable active two-factor authentication by verifying a 6-digit code from their authenticator app.

- **Standard plans enforce a limit of uploading a maximum of 5 documents simultaneously.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Standard plans enforce a limit of uploading a maximum of 5 documents simultaneously.

- **Allow template owners to generate a shareable signing URL for a template, enabling signing without knowing recipient email addresses in advance.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow template owners to generate a shareable signing URL for a template, enabling signing without knowing recipient email addresses in advance.

- **Users can drag and drop PDF or DOCX files anywhere on the Documents dashboard to initiate document upload.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Users can drag and drop PDF or DOCX files anywhere on the Documents dashboard to initiate document upload.

- **Support two-factor authentication and passkeys as additional security layers for signing high-security and high-compliance documents.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Support two-factor authentication and passkeys as additional security layers for signing high-security and high-compliance documents.

- **Webhook configuration and management features must be exclusively accessible to team accounts, explicitly blocking personal accounts from creating or managing webhooks.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Webhook configuration and management features must be exclusively accessible to team accounts, explicitly blocking personal accounts from creating or managing webhooks.

- **Send a completed document copy via email to the direct link signer immediately upon signing completion.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Send a completed document copy via email to the direct link signer immediately upon signing completion.

- **The platform must support password protection on documents to restrict document access to authorized recipients.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The platform must support password protection on documents to restrict document access to authorized recipients.

- **Allow users to drag field types from a palette and drop them onto specific pages in a document editor.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allow users to drag field types from a palette and drop them onto specific pages in a document editor.

- **Display recipient signing order in read-only mode during document generation for sequential signing templates.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Display recipient signing order in read-only mode during document generation for sequential signing templates.

- **Retrieve a paginated list of templates with support for filtering by type (PRIVATE or PUBLIC) and folder ID, as well as sorting by creation date.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Retrieve a paginated list of templates with support for filtering by type (PRIVATE or PUBLIC) and folder ID, as well as sorting by creation date.

- **API tokens carry full account permissions equivalent to the token owner, with no scoped or granular permission restrictions supported.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> API tokens carry full account permissions equivalent to the token owner, with no scoped or granular permission restrictions supported.

- **Users can select or drag multiple PDF and DOCX files simultaneously to create a single envelope containing multiple documents sharing recipients and signing workflow.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Users can select or drag multiple PDF and DOCX files simultaneously to create a single envelope containing multiple documents sharing recipients and signing workflow.

- **System checks user account plan limits upon upload and blocks document creation if the monthly quota has been reached.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> System checks user account plan limits upon upload and blocks document creation if the monthly quota has been reached.

- **Send an automated notification email containing document details and a unique signing access button to each recipient.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Send an automated notification email containing document details and a unique signing access button to each recipient.

- **Allows users to specify lifespan or expiration dates when generating API tokens to enhance security.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Allows users to specify lifespan or expiration dates when generating API tokens to enhance security.

- **Configure default document visibility settings at the organisation level with team-level override capabilities.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Configure default document visibility settings at the organisation level with team-level override capabilities.

- **Require users to select a pricing plan during organisation creation, with separate billing per organisation.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Require users to select a pricing plan during organisation creation, with separate billing per organisation.

- **Generate a direct link template that automatically creates and initiates a signing document when accessed by recipients.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Generate a direct link template that automatically creates and initiates a signing document when accessed by recipients.

- **Document creation from templates via POST /template/use does not support PDF placeholder parsing.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Document creation from templates via POST /template/use does not support PDF placeholder parsing.

- **Users can upload PDF documents by selecting a file or dragging and dropping it into the designated upload area on the Documents dashboard.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Users can upload PDF documents by selecting a file or dragging and dropping it into the designated upload area on the Documents dashboard.

- **Authenticate API requests using an API token provided in the Authorization header. Tokens require the 'api_' prefix.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Authenticate API requests using an API token provided in the Authorization header. Tokens require the 'api_' prefix.

- **The web application must render PDF documents natively in the client browser using pdf.js to enable document review and field placement.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> The web application must render PDF documents natively in the client browser using pdf.js to enable document review and field placement.

- **Save the created (drawn, typed, or uploaded) signature as the default signature for the account upon clicking 'Update profile'.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Save the created (drawn, typed, or uploaded) signature as the default signature for the account upon clicking 'Update profile'.

- **Retrieve a paginated list of envelopes/documents created within the account, including metadata and current status.**
  - Confidence: 0.49
  - Evidence path: updateTeamPublicProfile (update-team-public-profile.ts) -> https://app.documenso.com/settings/profile -> Retrieve a paginated list of envelopes/documents created within the account, including metadata and current status.

## Absent Requirements - No Coverage Found (6)

These requirements exist in documentation but have no CodeFunction or UIElement linked in the graph. Each is a candidate for manual verification.

- **The software must be packaged as standard Docker container images allowing users to self-host the platform on Docker, Do**
- **The platform must support secure vulnerability disclosures via GitHub Security Advisories to protect self-hosted and clo**
- **Allow teams to set up webhooks for integrating document events with external services.**
- **Standard plans enforce a limit of uploading a maximum of 5 documents simultaneously.**
- **The system must trigger a webhook notification with payload event 'DOCUMENT_CREATED' whenever a new document or template**
- **The system must trigger a webhook notification with payload event 'DOCUMENT_OPENED' when a recipient opens the document **

## ⚫ Dark Changes (12)

These changed functions have no traceable path to any UI or requirement:

- `updatedEnvelope (cancel-document.ts)`
- `createAttachment (create-attachment.ts)`
- `createOrGetShareLink (create-or-get-share-link.ts)`
- `isHttpUrl (is-http-url.ts)`
- `updateAttachment (update-attachment.ts)`
- `findAttachmentsByEnvelopeId (find-attachments-by-envelope-id.ts)`
- `member (update-organisation-group.ts)`
- `result (subscribe.ts)`
- `deleteAttachment (delete-attachment.ts)`
- `getRecipientById (get-recipient-by-id.ts)`
- `result (unsubscribe.ts)`
- `getEnvelopeRecipientRoute (get-envelope-recipient.ts)`

## ⚠️ Manual Review Required

- 101 node(s) have LOW confidence -- verify before updating test plans.
- 12 changed function(s) have no traceable path to UI or requirements: updatedEnvelope (cancel-document.ts), createAttachment (create-attachment.ts), createOrGetShareLink (create-or-get-share-link.ts)...
- 6 requirement(s) have no code or UI coverage. They may be unimplemented features or gaps in the crawl coverage.

## Coverage Statistics

| Metric | Count |
|---|---|
| Affected UI elements / pages | 1 |
| Affected requirements | 101 |
| Absent requirements | 6 |
| Dark changes | 12 |
| Manual review items | 3 |

---
*Report generated by Blast Radius Analyzer v4 · Run ID: `e197c8ef`*