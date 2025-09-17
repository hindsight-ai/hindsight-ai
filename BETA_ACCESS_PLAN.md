# Closed Beta Access Workflow Implementation Plan

## 1. Database Schema Changes

# Closed Beta Access Workflow Implementation Plan

## 1. Database Schema Changes

### a. New Table: `beta_access_requests`
Tracks user requests to join the closed beta.

- `id` (UUID, PK)
- `user_id` (UUID, FK to `users.id`)
- `email` (Text, not null)
- `status` (Text, enum: `pending`, `accepted`, `denied`)
- `requested_at` (DateTime, default=now_utc)
- `reviewed_at` (DateTime, nullable)
- `reviewer_email` (Text, nullable)
- `decision_reason` (Text, nullable)

### b. Update Table: `users`
Add a field to track beta access status.

- `beta_access_status` (Text, enum: `accepted`, `pending`, `denied`, default `pending`)

### c. Audit Logging
Log all beta access events in `audit_logs` (already exists).

---

## 2. Traefik Configuration

### a. Access Control Middleware
- After authentication, check if the user's email is in the accepted closed list (from DB).
- If not accepted, redirect to a holding page or show a message.
- Ensure Traefik forwards authentication headers (email/JWT) to backend.

### b. Update `config/traefik.yml`
- Add middleware for closed-list enforcement.
- Route unauthorized users to a "request access" page.

---

## 3. Backend (FastAPI Service)

### a. On First Login
- If user is not in the closed list (`beta_access_status != accepted`), trigger email inviting them to request access.

### b. Request Access Endpoint
- User submits request.
- Create `beta_access_requests` entry (`pending`).
- Send confirmation email to user ("request received, pending review").
- Send notification email to `ibarz.jean@gmail.com` with accept/deny links.

### c. Admin Review Endpoints
- Accept/deny request via special endpoint (secured for admin).
- On accept: update request status, set user as `accepted`, send acceptance email.
- On deny: update request status, set user as `denied`, send denial email.

### d. On Subsequent Logins
- If user is `accepted`, allow access.
- If `pending` or `denied`, restrict access and show appropriate message.

### e. Notification/Email Service
- Add new templates for each email type:
  - Invitation to request beta access
  - Confirmation of request (pending)
  - Notification to admin (accept/deny links)
  - Acceptance email
  - Denial email

---

## 4. Dashboard (Frontend)

### a. User Experience
- On login, if not accepted:
  - Show prompt to request beta access.
  - Show status (pending, denied) if applicable.

### b. Admin Experience
- For `ibarz.jean@gmail.com`:
  - Add dashboard page to review pending requests.
  - Accept/deny actions trigger backend endpoints.

### c. UI Updates
- Reflect beta access status and guide users through the workflow.

---

## 5. Security & Edge Cases

- Only authorized admin can accept/deny requests.
- Prevent duplicate requests.
- Handle email delivery failures gracefully.
- Log all actions for audit.

---

## 6. Implementation Steps

- [x] **Design and apply DB migrations** for new table and user field.
- [x] **Implement backend endpoints** for request, review, and status checks.
- [x] **Extend notification/email service** with new templates and flows.
- [ ] **Update Traefik config** for closed-list enforcement.
- [ ] **Update dashboard UI** for user/admin interactions.
- [ ] **Test the full workflow** (unit/integration/e2e).
- [ ] **Document the new workflow** for users and admins.

---

## Next Steps

1. **Update Traefik Configuration**: Modify `config/traefik.yml` to enforce beta access status checks before allowing access to the application.

2. **Dashboard UI Updates**: 
   - Add beta access request form for new users
   - Add admin panel for reviewing pending requests
   - Update login flow to handle different beta access states

3. **Testing**: Create comprehensive tests for the beta access workflow including email sending and status transitions.

4. **Documentation**: Update user-facing documentation to explain the beta access process.

1. **Design and apply DB migrations** for new table and user field.
2. **Update Traefik config** for closed-list enforcement.
3. **Implement backend endpoints** for request, review, and status checks.
4. **Extend notification/email service** with new templates and flows.
5. **Update dashboard UI** for user/admin interactions.
6. **Test the full workflow** (unit/integration/e2e).
7. **Document the new workflow** for users and admins.

---

## Progress updates

- [x] Added `beta_access_status` column to `User` model (`apps/hindsight-service/core/db/models/users.py`).
- [x] Added `BetaAccessRequest` model (`apps/hindsight-service/core/db/models/beta_access.py`).
- [x] Generated Alembic migration: `apps/hindsight-service/migrations/versions/58d9df7d9301_add_beta_access_table.py`.
- [x] Applied migration to local DB (`uv run alembic upgrade head`).
- [x] Created `BetaAccessRepository` (`apps/hindsight-service/core/db/repositories/beta_access.py`).
- [x] Created `BetaAccessService` (`apps/hindsight-service/core/services/beta_access_service.py`).
- [x] Created API endpoints (`apps/hindsight-service/core/api/beta_access.py`).
- [x] Updated main router to include beta access endpoints (`apps/hindsight-service/core/api/main.py`).
- [x] Added audit actions for beta access (`apps/hindsight-service/core/audit.py`).
- [x] Extended notification service with beta access email methods (`apps/hindsight-service/core/services/notification_service.py`).
- [x] Updated beta access service to use notification methods instead of placeholders.
- [x] Created email templates for beta access workflow (`apps/hindsight-service/core/templates/email/`):
  - `beta_access_invitation.html` & `.txt` - Invitation to request beta access
  - `beta_access_request_confirmation.html` & `.txt` - Confirmation of request
  - `beta_access_admin_notification.html` & `.txt` - Admin notification with accept/deny links
  - `beta_access_acceptance.html` & `.txt` - Acceptance email to user
  - `beta_access_denial.html` & `.txt` - Denial email to user

Migration notes:

- The migration adds the `beta_access_requests` table and the non-nullable `users.beta_access_status` column.
- Server defaults were temporarily added in the migration for `status` and `requested_at` on the new table, and for `users.beta_access_status`, to make the migration safe for existing rows; the migration removes the server default on `users.beta_access_status` after creation to match the Python-side default behavior.

Let me know which step you want to start with next, or if you want a more granular breakdown for any section.
