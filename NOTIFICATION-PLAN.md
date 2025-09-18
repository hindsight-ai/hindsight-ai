NOTIFICATION PLAN: Organization membership events

Goal
- Notify users when organization membership changes affect them:
  1) When a user accepts an invitation and is successfully added as a member (with the assigned role). Notify the invited user.
  2) When a user's role changes in an organization (e.g., Reader -> Editor). Notify the affected user.
  3) When a user is removed from an organization. Notify the affected user.

Delivery channels
- In-app notifications: use the project's existing notification service/system so notifications appear in the UI Notification center.
- Email notifications: sent according to the user's current email notification preferences at the moment the event occurs.
- Both channels reuse the same message content (title + body) and consistent design.

Principles
- Reuse existing notification utilities (notificationService + email templates used for invitation notifications) to keep tone/brand consistent.
- Respect user notification settings: do not send emails when the user opted out, but always create in-app notifications unless the user disabled all in-app notifications (if such a setting exists). Document data checks.
- Provide clear actions in notifications where applicable (e.g., link to organization, link to profile or membership settings).
- Provide contextual variables: organization name, role name, actor (who changed the role or removed the user), and timestamp.
- Support i18n-friendly templates by keeping variables separate from copy (TODO: migrate to i18n system if/when available).

High-level flow
1) Invitation accepted and user added as member
   - Trigger point: existing invitation acceptance code path (server-side) after invite is validated and membership row created.
   - Actions:
     - Create an in-app notification record for the user with type `org:member_added` (payload: orgId, orgName, role, actorId)
     - If user email notifications for `org:membership` are enabled, send an email using the invitation-consistent template: subject "You're now a member of <orgName>" and body explaining the role and next steps.

2) Role changed
   - Trigger point: server-side function that updates a member's role (admin action). After DB update succeeds and transaction commits.
   - Actions:
     - Create an in-app notification record type `org:role_changed` (payload: orgId, orgName, oldRole, newRole, actorId)
     - If email notifications enabled, send email template subject "Your role in <orgName> changed to <newRole>" with body describing implications and link to org settings.

3) Removed from organization
   - Trigger point: server-side function that removes a membership row (admin action or self-removed). After DB update/commit.
   - Actions:
     - Create an in-app notification record type `org:removed` (payload: orgId, orgName, actorId, reason optional)
     - If email notifications enabled, send email with subject "Removed from <orgName>" describing what happened and links to create or request access.

Data shapes
- Notification record (reusing existing schema):
  - id, user_id, type (string), payload (json), read (bool), created_at
  - payload examples:
    - org:member_added: { orgId, orgName, role, actorId }
    - org:role_changed: { orgId, orgName, oldRole, newRole, actorId }
    - org:removed: { orgId, orgName, actorId, reason? }

Email templates
- Reuse the same layout/header/footer as the invitation email template; content blocks below are variable.
- Suggested variables: {{user_name}}, {{org_name}}, {{role}}, {{old_role}}, {{new_role}}, {{actor_name}}, {{action_link}}

Templates (subject + short body outline):
1) member_added
   - Subject: "You're now a member of {{org_name}}"
   - Preheader: "Your account has been added to {{org_name}} as a {{role}}."
   - Body: Short greeting, confirmation that the user was added with their role, a short bullet of what they can do, link to the org, and footer (same style as invite email).

2) role_changed
   - Subject: "Your role in {{org_name}} changed to {{new_role}}"
   - Preheader: "Your permissions were updated in {{org_name}}."
   - Body: Explain old -> new role, what changed, links to org settings and docs, contact actor (if available).

3) removed
   - Subject: "You were removed from {{org_name}}"
   - Preheader: "You no longer have access to {{org_name}}."
   - Body: Explain removal, reason if available, link to request access or contact support.

Implementation plan (steps)
1) Create `NOTIFICATION-PLAN.md` (this file) and confirm desired texts with stakeholders.
2) Wire server-side hooks in `apps/hindsight-service` at these locations:
   - invitation acceptance flow (after member row creation)
   - membership role update function
   - membership removal function
   Use existing notification sending utilities (e.g., `notificationService.createForUser` + `emailService.sendTemplate`). If utilities do not exist, reuse the code from invitation email path.
3) Add email templates (e.g., under `apps/hindsight-service/templates/emails/org_member_added.html` and matching plain text variants), reusing invitation template structure.
4) Ensure notification preferences: query user's notification settings and check `org:membership` or equivalent before sending email.
5) Add unit tests:
   - Test that invitation acceptance triggers a notification record and sends an email when enabled.
   - Test role change triggers notification + email when enabled.
   - Test removal triggers notification + email when enabled.
   - Edge cases: user opted out of emails; actor is null; org not found; DB failures.
6) Add integration tests simulating acceptance flow and admin role change.
7) Run test suite and fix regressions. Document results.

Testing plan and cases
- Nominal cases:
  - Accept invite -> membership created -> notification + email (if enabled)
  - Role change -> notification + email
  - Removal -> notification + email
- Edge cases:
  - User has email notifications disabled -> no email sent, in-app still created
  - Actor missing (system action) -> notification still created without actor name
  - DB rollback after notification queued -> ensure notifications sent only after commit (wrap in transaction hooks or send after commit)
  - Concurrent role change events -> last write wins; ensure notifications reflect final state

Notes and considerations
- Send emails asynchronously (background worker) to avoid blocking request flow. Use existing background job mechanism.
- Prefer sending notification creation after DB commit to avoid dangling notifications for rolled-back transactions.
- Keep templates consistent with invitation email design (header/footer styles). If the invitation email is in `apps/hindsight-service/templates/emails/invitation_*`, mirror structure.

Next actions (I'll execute now, one by one):
- [in-progress] Add `NOTIFICATION-PLAN.md` (completed)
- [next] Implement server-side hooks in the service for member_added, role_changed, and removed, and wire to notification utilities.
- After that, add templates, tests, and run test suite.

