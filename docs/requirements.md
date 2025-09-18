# Hindsight AI — Product & Technical Requirements

This document specifies the expected behavior, constraints, and operational requirements of the Hindsight AI application across environments (staging, product4) From any app page (e.g., `/memory-blocks`), top‑right "Sign In" goes directly to G## 14. Acceptance Criteria (Key Scenarios)

### Core Application Flow
1) First visit (unauthenticated) to `/` redirects to `/login`.
2) On `/login`, clicking "Sign In" sends user to Google and returns to `/dashboard` authenticated.
3) On `/login`, clicking "Explore as Guest" navigates to `/dashboard` with guest badge and write actions blocked.
4) From any app page (e.g., `/memory-blocks`), top‑right "Sign In" goes directly to Google and returns to the same page authenticated.
5) After successful OAuth, the same tab shows authenticated state without opening a new tab.
6) Switching environments uses the same dashboard image with a different runtime `HINDSIGHT_SERVICE_API_URL`.
7) Certificates are issued successfully for `APP_HOST` and `TRAEFIK_DASHBOARD_HOST`; no literal `${...}` placeholders appear in Traefik logs.
8) CI prevents overlapping deploys per branch (concurrency), and staging deploys never affect production.

### Organization Management Acceptance Criteria

#### AC-ORG-1: Organization Switcher (Both User Types)
- ✅ Shows only organizations where user is a member
- ✅ Allows switching only to member organizations
- ✅ Returns appropriate error for non-member organization access
- ✅ Consistent behavior between regular users and superadmins

#### AC-ORG-2: Organization Management Access Control
- ✅ Regular users can access organization management panel for organizations they own/admin
- ✅ Regular users can create, edit, delete organizations where they have owner/admin role
- ✅ Regular users can manage members of organizations they own/admin
- ✅ Superadmins can access organization management panel for ALL organizations
- ✅ Superadmins can create, edit, delete all organizations
- ✅ Superadmins can manage members of all organizations
- ✅ Users with no manageable organizations see appropriate message

#### AC-ORG-3: Safe Default Behavior 
- ✅ Regular users: Organization management shows only organizations they can manage (owner/admin role)
- ✅ Superadmins: Organization management shows only member organizations by default
- ✅ Clear visual indication of current view mode for superadmins
- ✅ Familiar, uncluttered interface in default mode
- ✅ Can perform all routine tasks without switching modes

#### AC-ORG-4: Explicit All-Organizations Access (Superadmin)
- ✅ Requires explicit user action to view all organizations
- ✅ Shows confirmation dialog when switching to "all organizations" mode
- ✅ Clear visual distinction between member vs non-member organizations
- ✅ Membership status badges/indicators visible
- ✅ Can switch back to member-only view easily

#### AC-ORG-5: Visual Safety Indicators
- ✅ Green styling for member organizations
- ✅ Red styling for non-member organizations  
- ✅ "Member" vs "Admin Access Only" badges
- ✅ Current mode clearly displayed (Member Organizations / All Organizations)
- ✅ Prominent mode toggle button

#### AC-ORG-6: Interaction Safety
- ✅ Warning dialog when selecting non-member organization for management
- ✅ Confirmation required for destructive actions on non-member organizations
- ✅ Breadcrumb or context indicator showing current organization's membership status
- ✅ Clear "back to member organizations" option always available

#### AC-ORG-7: Data Access Boundaries (Both User Types)
- ✅ Users can only access data from organizations where they are members
- ✅ Superadmins cannot access organization data they're not members of
- ✅ API endpoints enforce membership-based data access
- ✅ Clear error messages for unauthorized data access attempts

#### AC-ORG-9: Dynamic Role-Based Permission System ✅ **NEWLY IMPLEMENTED**
- ✅ Role permissions are defined in centralized configuration (`core/utils/role_permissions.py`)
- ✅ Owner, admin, and editor roles have `can_read=True` and `can_write=True` by default
- ✅ Viewer role has `can_read=True` and `can_write=False` by default
- ✅ API endpoints automatically apply correct permissions when adding/updating members
- ✅ Explicit permission overrides are supported when needed
- ✅ Invalid roles are rejected with clear error messages
- ✅ Permission changes require only configuration updates, not code changes
- ✅ Existing members can be updated to match new permission configurations
- ✅ Comprehensive unit and integration test coverage for permission logic

#### AC-ORG-10: Permission System Flexibility and Extensibility
- ✅ Easy to add new roles by updating `ROLE_PERMISSIONS` configuration
- ✅ Easy to modify existing role permissions without touching business logic
- ✅ Consistent permission application across all API endpoints
- ✅ Migration tools available to update existing data after configuration changes
- ✅ Role validation prevents invalid role assignments
- ✅ Permission resolution logic handles edge cases gracefully
- ✅ Audit trail maintained for permission changes

#### AC-ORG-11: Permission System Testing and Validation
- ✅ Unit tests cover all role permission utility functions
- ✅ Integration tests validate API endpoints with dynamic permissions
- ✅ Test coverage for permission override functionality
- ✅ Tests for invalid role handling and error scenarios
- ✅ Validation of permission consistency across add/update operations
- ✅ Automated testing prevents regression in permission logic

### Organization Management Testing Implementation

#### RGB Methodology Test Coverage
The delete button state refresh functionality has been validated using comprehensive RGB (Red-Green-Blue) methodology testing:

**RED Phase - Expected Behavior Definition:**
- ✅ Test for refresh call when creating organization
- ✅ Test for refresh call when switching organizations  
- ✅ Test for proper role-based access controls after refresh

**GREEN Phase - Core Functionality:**
- ✅ Test that validates refresh is called gracefully even when it fails
- ✅ Test that organization operations continue despite refresh errors
- ✅ Test for error logging and user feedback mechanisms

**BLUE Phase - Advanced Scenarios:**
- ✅ Test for consistent refresh behavior across multiple organization switches
- ✅ Test for robust error handling and concurrent operations
- ✅ Test for UI responsiveness during background refresh operations

**Test Results:** All 20 OrganizationManagement tests pass, including 4 new RGB methodology tests specifically for delete button state refresh functionality.

**Implementation Details:**
- Frontend: Added `refreshUser()` calls in organization creation and switching handlers
- Error Handling: Graceful fallback when refresh operations fail
- Background Operations: Non-blocking user data synchronization
- Test Coverage: Comprehensive validation of timing, error scenarios, and edge cases returns to the same page authenticated.
5) After successful OAuth, the same tab shows authenticated state without opening a new tab.
6) **Organization Management**: Authenticated users can create and manage their own organizations through the user account dropdown menu:
   - **"Manage Organizations"** menu item opens a modal dialog with organization and member management
   - **Create Organizations**: Any authenticated user can create new organizations with name and optional slug, becoming the owner
   - **Manage Own Organizations**: Users can manage organizations where they have owner or admin role (view, edit, member management)
   - **Superadmin Global Access**: Superadmins can manage ALL organizations (including those they don't own) with visual safety indicators
   - **Member Management**: For manageable organizations, users can view, add, update, and remove members
   - **Role Management**: Support for owner, admin, editor, viewer roles with appropriate permissions
   - **Self-Protection**: Users cannot remove themselves or change their own role
   - **Real-time Updates**: Changes are immediately reflected in the UI with success/error notifications
   - **Immediate UI State Refresh**: Delete buttons and other role-dependent controls appear immediately after organization creation or switching without requiring panel close/reopen
7) **Dev Mode Experience**: In local development only (when `APP_BASE_URL` resolves to `localhost`), "Sign In" automatically authenticates as `dev@localhost` with superadmin privileges, enabling full testing without OAuth setup. Remote environments must run with `DEV_MODE=false`; the API refuses to start otherwise.
8) **Profile Privileges Panel**: The dashboard profile page lists only privileges that are actually granted. Superadmin and beta-access-admin badges appear when enabled; otherwise the panel shows a neutral "No elevated privileges" indicator alongside the user's beta access status.

Roadmap Reference
- Execution ordering, phased delivery plan, and acceptance criteria for in-progress governance & UX work are tracked in `docs/roadmap.md`. This requirements file defines the target state; the roadmap file defines how we get there iteratively.

## 1. Scope & Goals
- Provide a secure web UI to manage AI Agent memories and related operations.
- Ensure environment parity and safe deployments with minimal drift.
- Support authenticated usage via Google OAuth (through oauth2-proxy) and a read‑only Guest Mode.

## 2. Stakeholders
- Product owner: sets functional priorities.
- Engineers: implement and operate the system (backend, frontend, DevOps).
- Operators: manage infrastructure, DNS, certificates, and secrets.

## 3. Glossary
- Dashboard: Frontend React/Vite UI (served by Nginx).
- Service/API: FastAPI backend (hindsight-service).
- oauth2-proxy: Reverse proxy handling Google OAuth and auth cookies.
- Traefik: Edge reverse proxy, TLS termination via Let’s Encrypt DNS‑01.
- GHCR: GitHub Container Registry for images.

## 4. Environments
- Production: branch `main`, environment name `production`.
- Staging: branch `staging`, environment name `staging`.
- Local development: docker compose or `vite dev` + API.

A single compose file `docker-compose.app.yml` is used for both staging and production, parameterized by `.env` on the server.

### 4.1 Local Development Authentication
In local development mode, the system provides a simplified authentication mechanism:
- **Dev Authentication**: Click "Sign In" button automatically authenticates as `dev@localhost`
- **Full Permissions**: Dev user has superadmin privileges and can access all features
- **Organization Management**: Dev user can create, manage organizations and memberships through the user menu
- **Production Parity**: Same permission logic as production, just bypasses OAuth flow
- **Dev Mode Indicators**: UI shows "Development Mode" status and admin badge
- **Simplified Logout**: In dev mode, logout redirects to home page instead of OAuth logout flow

## 5. Organization Management Detailed Requirements

### 5.1 User Roles & Permissions

#### Regular User
- **Organization Switcher**: Can only see and switch to organizations where they are members
- **Organization Creation**: Can create new organizations and automatically become owner
- **Organization Management**: Can manage organizations where they have owner or admin role
- **Data Access**: Only to organizations where they are members

#### Superadmin
- **Organization Switcher**: Can only see and switch to organizations where they are members (same as regular users)
- **Organization Management**: Full administrative access with safety mechanisms for ALL organizations
- **Data Access**: Only to organizations where they are members (data privacy preserved)

### 5.2 Organization Management Panel Access Control

#### Access Requirements
- **Who can access**: 
  - Regular users: Can access to manage organizations where they have owner/admin role
  - Superadmins: Can access to manage ALL organizations (`is_superadmin: true`)
- **Access denied behavior**: Show clear message if user has no manageable organizations

#### Organization Display Modes

##### Mode 1: Member Organizations (Default)
- **Default view**: Shows only organizations where superadmin is a member
- **Visual styling**: Standard styling, clear and familiar
- **Interaction**: Can immediately manage these organizations
- **Purpose**: Safe default for routine organization management tasks

##### Mode 2: All Organizations (Explicit Opt-in)
- **Access method**: Requires explicit user action (toggle/button)
- **Visual indicators**: 
  - Clear visual distinction between member vs non-member organizations
  - Green border/background for organizations where superadmin is a member
  - Red border/background for organizations where superadmin is NOT a member
  - Badge/tag indicating membership status ("Member" vs "Admin Access Only")
- **Warning mechanism**: Confirmation prompt when accessing non-member organization
- **Purpose**: Administrative tasks on all organizations

### 5.3 Real-time UI State Management

#### Immediate State Refresh Requirements
- **Organization Creation**: Delete buttons and role-dependent controls appear immediately after creating organization without manual refresh
- **Organization Switching**: UI updates immediately when switching between organizations
- **User Data Synchronization**: User membership data refreshes automatically to ensure accurate permission display
- **Error Handling**: Graceful handling of refresh failures without blocking operations
- **Background Operations**: State refresh operations run asynchronously without affecting user experience

#### Implementation Details
- **Frontend Refresh Calls**: Automatic `refreshUser()` calls after organization creation and switching
- **Optimistic UI Updates**: UI updates immediately while background data synchronization occurs
- **Fallback Mechanisms**: Manual refresh options available if automatic refresh fails
- **Test Coverage**: Comprehensive RGB methodology testing ensures reliable state management

### 5.4 Safety Mechanisms

#### Visual Safety Indicators
1. **Color Coding**:
   - Green: Organizations where superadmin is a member (safe zone)
   - Red: Organizations where superadmin is NOT a member (admin-only access)

2. **Membership Badges**:
   - "Member": User has actual membership and data access
   - "Admin Access Only": User can manage but cannot access organization data

3. **Mode Indicator**:
   - Clear indication of current view mode (Member Orgs vs All Orgs)
   - Prominent toggle to switch between modes

#### Interaction Safety
1. **Default Filter**: Show only member organizations by default
2. **Explicit Opt-in**: Require deliberate action to view non-member organizations
3. **Confirmation Dialogs**: Warn when performing actions on non-member organizations
4. **Breadcrumb Context**: Always show current mode and organization membership status

### 5.5 Implementation Specifications

#### Backend API Endpoints

##### `/organizations/` 
- **Purpose**: Organization switcher dropdown
- **Returns**: Only organizations where user is a member
- **Access**: All authenticated users
- **Behavior**: Same for regular users and superadmins

##### `/organizations/manageable`
- **Purpose**: Organization management (organizations user can manage)
- **Returns**: Organizations where user has owner/admin role, or all organizations for superadmins
- **Access**: All authenticated users
- **Behavior**: Regular users see only their manageable orgs, superadmins see all

### 5.6 Dynamic Role-Based Permission System

#### Overview
The system implements a dynamic, configuration-driven approach to role-based permissions that eliminates hardcoded permission logic and enables easy modification of role capabilities without code changes.

#### Role Permission Configuration
```python
ROLE_PERMISSIONS = {
    "owner": {
        "can_read": True,
        "can_write": True,
    },
    "admin": {
        "can_read": True,
        "can_write": True,
    },
    "editor": {
        "can_read": True,
        "can_write": True,
    },
    "viewer": {
        "can_read": True,
        "can_write": False,
    },
}
```

#### Key Features
1. **Centralized Configuration**: All role permissions defined in `core/utils/role_permissions.py`
2. **Dynamic Resolution**: Permissions automatically applied based on role during member addition/update
3. **Override Support**: Explicit permission overrides still supported when needed
4. **Extensible Design**: Easy to add new roles or modify existing permissions
5. **Consistent Application**: Same permission logic used across all API endpoints

#### Permission Resolution Logic
- **Default Behavior**: When adding/updating members, permissions default to role-based values
- **Explicit Overrides**: API accepts explicit `can_read`/`can_write` parameters to override defaults
- **Validation**: Invalid roles rejected with clear error messages
- **Data Integrity**: Existing members can be updated to match new permission configurations

#### Implementation Components
1. **Utility Module** (`core/utils/role_permissions.py`):
   - `get_role_permissions(role)`: Returns default permissions for a role
   - `validate_role(role)`: Validates role against allowed set
   - `update_permissions_for_role()`: Applies overrides to role permissions

2. **API Integration** (`core/api/orgs_fixed.py`):
   - `add_member()`: Uses dynamic permissions when creating memberships
   - `update_member()`: Applies role-based permissions when role changes

3. **Migration Tools** (`update_member_permissions.py`):
   - Updates existing members to match current role permissions
   - Handles bulk permission corrections after configuration changes

#### Benefits
- **Maintainability**: Permission changes require only configuration updates
- **Consistency**: Eliminates hardcoded permission logic scattered throughout codebase
- **Flexibility**: Easy to introduce new roles or modify existing permissions
- **Reliability**: Centralized validation and error handling
- **Testability**: Comprehensive unit and integration test coverage

##### `/organizations/{org_id}/members`
- **Purpose**: Get organization membership information
- **Returns**: List of organization members
- **Access**: Organization members + superadmins
- **Usage**: Determine superadmin's membership status

#### Frontend Component Implementation

##### OrganizationManagement Component State Management
```typescript
const [viewMode, setViewMode] = useState<'member' | 'all'>('member');
const [organizations, setOrganizations] = useState<Organization[]>([]);
const [userMemberOrganizations, setUserMemberOrganizations] = useState<Organization[]>([]);
const [showAllConfirmation, setShowAllConfirmation] = useState(false);
```

##### Display Logic
```typescript
const displayedOrganizations = viewMode === 'member' 
  ? organizations.filter(org => isUserMember(org.id))
  : organizations;

const isUserMember = (orgId: string): boolean => {
  return userMemberOrganizations.some(org => org.id === orgId);
};
```

##### Safety Controls Implementation
- Default to 'member' mode
- Require explicit toggle to 'all' mode
- Show confirmation dialog when switching to 'all' mode
- Visual indicators for membership status
- Warning when selecting non-member organization

### 5.6 Technical Considerations

#### Performance
- Minimize API calls by caching membership information
- Efficient filtering for large numbers of organizations

#### Security  
- Server-side validation of all permissions
- Client-side indicators are UX only, not security boundaries
- Audit logging for superadmin actions on non-member organizations

#### Accessibility
- Clear visual indicators that work with screen readers
- Keyboard navigation support for mode switching
- High contrast options for color-coded indicators

### 5.7 Future Enhancements

1. **Audit Trail**: Log superadmin access to non-member organizations
2. **Temporary Access**: Time-limited access grants for specific organizations
3. **Delegation**: Allow organization owners to grant temporary admin access
4. **Notification**: Alert organization owners when superadmin accesses their organization

### 5.8 User Experience Flow

#### Superadmin Organization Management Flow
1. **Initial Access**: Opens organization management → sees only member organizations
2. **Routine Management**: Can immediately manage member organizations (safe zone)
3. **Admin Tasks**: Clicks "Show All Organizations" → confirmation dialog → sees all organizations with visual indicators
4. **Safe Selection**: Green organizations = member (can access data), Red organizations = admin-only (management only)
5. **Return to Safety**: Can easily return to member-only view

#### Error Prevention Mechanisms
1. **Visual Cues**: Immediate visual feedback about membership status
2. **Default Safety**: Safe behavior by default, dangerous behavior requires opt-in
3. **Confirmation Dialogs**: Extra confirmation for potentially risky actions
4. **Clear Context**: Always know what mode you're in and what access you have

## 6. Notification System Requirements

### 7.1 Implementation Plan and Status Tracking

```xml
<!-- STATUS TRACKING: This section tracks the implementation progress of the notification system -->
<!-- INSTRUCTIONS: Update status attributes when work begins or completes -->
<!-- STATUSES: not-started | in-progress | testing | completed -->
<!-- LAST UPDATED: September 11, 2025 -->

<implementation-plan name="notification-system" last-updated="2025-09-11">
  <phase number="1" name="Foundation" status="completed">
    <task name="database-schema" status="completed">Design and implement notification tables</task>
    <task name="backend-service" status="completed">Create NotificationService class</task>
    <task name="basic-email" status="completed">Basic email notification for membership changes</task>
    <task name="in-app-infrastructure" status="completed">In-app notification system foundation</task>
    <task name="api-endpoints" status="completed">Basic notification API endpoints</task>
    <task name="integration" status="completed">Integration with organization invitation flow</task>
  </phase>
  <phase number="2" name="User Interface" status="not-started">
    <task name="notification-bell" status="not-started">Header notification bell with badge</task>
    <task name="notification-dropdown" status="not-started">Quick notification preview dropdown</task>
    <task name="settings-page" status="not-started">User notification preferences page</task>
    <task name="notification-center" status="not-started">Full notification management page</task>
  </phase>
  <phase number="3" name="Enhanced Features" status="not-started">
    <task name="email-templates" status="not-started">Rich HTML email templates</task>
    <task name="real-time-updates" status="not-started">WebSocket real-time notifications</task>
    <task name="batch-operations" status="not-started">Mark all read, bulk actions</task>
    <task name="delivery-tracking" status="not-started">Email delivery monitoring</task>
  </phase>
  <phase number="4" name="Testing & Documentation" status="not-started">
    <task name="unit-tests" status="not-started">Comprehensive test suite</task>
    <task name="integration-tests" status="not-started">End-to-end notification flow tests</task>
    <task name="documentation" status="not-started">API documentation and user guides</task>
  </phase>
</implementation-plan>
```

### 7.2 System Overview

#### Multi-Channel Notification Architecture
The notification system provides both email and in-app notifications to ensure users are always informed of important organization events while respecting their communication preferences.

#### Core Principles
- **Security-First**: Critical notifications (membership changes) always delivered via in-app
- **User Control**: Granular email preferences while maintaining security notifications
- **Reliability**: Robust delivery tracking and retry mechanisms
- **Performance**: Efficient batching and real-time updates

### 7.3 Notification Channels

#### Email Notifications (External)
- **Purpose**: Professional external communication
- **User Control**: Can be disabled per category
- **Templates**: Rich HTML with organization branding
- **Delivery**: Immediate for critical events, batched for summaries

#### In-App Notifications (Internal)
- **Purpose**: Real-time system communication
- **Security**: Always active for critical events (cannot be disabled)
- **Interface**: Bell icon with badge count positioned in top-right header area near user account controls + notification center
- **Positioning**: Following standard UX conventions, notification bell appears in top-right corner where users expect to find it
- **Persistence**: Retained until acknowledged by user

### 7.4 Notification Categories

#### Security-Critical (Always Delivered Both Ways)
- ✅ **Organization Membership**: Added to or removed from organization
- ✅ **Role Changes**: User role modified within organization  
- ✅ **Security Events**: Account access, permission changes

#### Informational (Email Optional, In-App Always)
- 📋 **Organization Updates**: Name changes, settings modifications
- 📢 **System Announcements**: New features, maintenance windows
- 📊 **Activity Summaries**: Weekly digest emails (optional)

#### Activity (Fully Optional)
- 💬 **Collaboration**: Comments, shared content
- 🔔 **General Updates**: Non-critical system events

### 7.5 User Preference Management

#### Notification Settings Page
**Location**: User Account Dropdown → "Notification Settings"

#### Email Notification Controls
```
📧 Email Notifications
├── ✅ Organization Membership (when added/removed) [Security - Always On]
├── ✅ Role Changes (when your role is modified) [Security - Always On] 
├── ⬜ Organization Updates (name changes, settings)
├── ⬜ Weekly Activity Summary (digest emails)
└── ⬜ System Announcements (new features, maintenance)

📱 In-App Notifications  
├── ✅ Security Events (always on for compliance)
├── ✅ Organization Events (always on)
├── ⬜ Activity Notifications (comments, collaborations)
└── ⬜ System Messages (tips, feature suggestions)
```

### 7.6 Database Schema Design

#### User Notification Preferences
```sql
CREATE TABLE user_notification_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    email_org_membership BOOLEAN DEFAULT true,
    email_role_changes BOOLEAN DEFAULT true, 
    email_org_updates BOOLEAN DEFAULT false,
    email_weekly_digest BOOLEAN DEFAULT false,
    email_system_announcements BOOLEAN DEFAULT true,
    in_app_activity BOOLEAN DEFAULT true,
    in_app_system_messages BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### In-App Notifications
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL, -- 'org_membership', 'role_change', 'org_update', etc.
    category VARCHAR(20) NOT NULL, -- 'security', 'info', 'activity'
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    read_at TIMESTAMP,
    related_org_id UUID REFERENCES organizations(id),
    metadata JSONB, -- Additional context data
    expires_at TIMESTAMP -- Auto-cleanup old notifications
);
```

#### Email Delivery Tracking
```sql
CREATE TABLE email_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES notifications(id),
    user_id UUID NOT NULL REFERENCES users(id),
    email_address VARCHAR(255) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    failed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 7.7 Backend Implementation Specifications

#### NotificationService Class
```python
class NotificationService:
    async def notify_user(
        self, 
        user_id: UUID, 
        type: str, 
        title: str, 
        content: str,
        category: str = "info",
        org_id: UUID = None,
        metadata: dict = None
    ) -> Notification:
        """Create and dispatch notification via all appropriate channels"""
        
    async def send_email_notification(
        self, 
        user_id: UUID, 
        notification: Notification
    ) -> EmailNotification:
        """Send email if user preferences allow"""
        
    async def create_in_app_notification(
        self, 
        user_id: UUID, 
        notification_data: dict
    ) -> Notification:
        """Always create in-app notification"""
        
    async def get_user_notifications(
        self, 
        user_id: UUID, 
        filters: dict = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Retrieve user notifications with filtering"""
        
    async def mark_notifications_read(
        self, 
        user_id: UUID, 
        notification_ids: List[UUID]
    ) -> int:
        """Mark specific notifications as read"""
        
    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for badge"""
```

#### Email Template System
```python
class EmailTemplateService:
    templates = {
        'org_membership_added': 'Welcome to {org_name}! You have been added as {role}.',
        'org_membership_removed': 'You have been removed from {org_name}.',
        'role_changed': 'Your role in {org_name} has been changed to {new_role}.',
        'org_updated': '{org_name} has been updated by {updated_by}.',
        'weekly_digest': 'Your weekly activity summary for {date_range}.'
    }
    
    async def render_template(
        self, 
        template_name: str, 
        context: dict
    ) -> Tuple[str, str]:
        """Return (subject, html_content) for email"""
```

### 7.8 Frontend Implementation Specifications

#### React Components Architecture

##### NotificationBell Component
```typescript
interface NotificationBellProps {
  user: User;
  onNotificationClick: () => void;
}

const NotificationBell: React.FC<NotificationBellProps> = ({ user, onNotificationClick }) => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  
  // Real-time unread count updates
  // Dropdown with recent notifications
  // Click handlers for navigation
};
```

##### NotificationCenter Component  
```typescript
interface NotificationCenterProps {
  user: User;
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({ user }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [filters, setFilters] = useState({ category: 'all', read: 'all' });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Pagination, filtering, search
  // Bulk operations (mark read, delete)
  // Real-time updates via WebSocket
};
```

##### NotificationSettings Component
```typescript
interface NotificationSettingsProps {
  user: User;
  onSettingsUpdate: (settings: NotificationSettings) => void;
}

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ user, onSettingsUpdate }) => {
  const [emailSettings, setEmailSettings] = useState<EmailNotificationSettings>({});
  const [inAppSettings, setInAppSettings] = useState<InAppNotificationSettings>({});
  
  // Toggle controls for each notification type
  // Save/cancel functionality
  // Preview email templates
};
```

### 7.9 Integration Points

#### Organization Management Integration
- **Member Addition**: Trigger `org_membership_added` notification
- **Role Changes**: Trigger `role_changed` notification  
- **Member Removal**: Trigger `org_membership_removed` notification
- **Organization Updates**: Trigger `org_updated` notification

#### API Endpoints
```python
# New notification endpoints
GET /api/notifications/ # Get user notifications with pagination/filtering
POST /api/notifications/mark-read # Mark notifications as read
GET /api/notifications/unread-count # Get unread notification count
GET /api/notifications/settings # Get user notification preferences
PUT /api/notifications/settings # Update user notification preferences

# Integration with existing endpoints
POST /api/organizations/{org_id}/members # Enhanced to send notifications
PUT /api/organizations/{org_id}/members/{user_id} # Enhanced to send notifications
DELETE /api/organizations/{org_id}/members/{user_id} # Enhanced to send notifications
```

### 7.10 Real-time Updates

#### WebSocket Integration
- **Connection**: Establish WebSocket on login
- **Events**: Real-time notification delivery
- **Fallback**: Polling mechanism for WebSocket failures
- **Scaling**: Redis pub/sub for multi-instance deployments

#### Event Types
```typescript
interface NotificationEvent {
  type: 'notification_created' | 'notification_read' | 'notification_deleted';
  data: {
    notification_id: string;
    user_id: string;
    unread_count: number;
    notification?: Notification;
  };
}
```

### 6.6 Acceptance Criteria

#### AC-NOTIF-1: Basic Email Notifications
**Given** a user is invited to an organization
**When** the invitation is created
**Then** an email notification should be sent to the invitee's email address
**And** the email should contain organization name, inviter name, and accept/decline links

#### AC-NOTIF-2: Email Notification Preferences
**Given** a user has email notifications disabled
**When** they are invited to an organization
**Then** no email should be sent
**But** an in-app notification should still be created

#### AC-NOTIF-3: In-App Notification Creation and UI Positioning
**Given** a user receives any organization-related event
**When** the event occurs
**Then** an in-app notification should be created
**And** the notification should appear in their notification list
**And** the unread count should be updated
**And** the notification bell should be positioned in the top-right header area near the user account button
**And** the notification bell should follow standard UX conventions for notification placement

#### AC-NOTIF-4: Real-Time Notification Updates
**Given** a user has the application open
**When** they receive a new notification
**Then** the notification should appear in real-time without refresh
**And** the unread count should update immediately

#### AC-NOTIF-5: Notification Persistence
**Given** a user receives notifications
**When** they log out and log back in
**Then** unread notifications should still be visible
**And** read notifications should be preserved for 30 days

#### AC-NOTIF-6: Notification Settings Management
**Given** a user wants to change notification preferences
**When** they access notification settings
**Then** they should be able to toggle email notifications on/off
**And** changes should take effect immediately for new events

#### AC-NOTIF-7: Multiple Notification Events
**Given** various organization events occur (invite, accept, remove, role change)
**When** each event happens
**Then** appropriate notifications should be generated for relevant users
**And** each notification should contain event-specific information

#### AC-NOTIF-8: Notification Performance
**Given** the notification system is operational
**When** notifications are created and delivered
**Then** email delivery should complete within 30 seconds
**And** in-app notifications should appear within 5 seconds
**And** the system should handle at least 100 concurrent notifications

## 7. Secrets & Configuration
All secrets are environment‑scoped in GitHub Environments. Use the same key names for both envs; values differ per env.

Required secrets (per env):
- SSH: `SSH_HOST`, `SSH_USERNAME`, `SSH_KEY`, `SSH_PORT`.
- Domains: `APP_HOST` (e.g., app.hindsight-ai.com or app-staging.hindsight-ai.com), `TRAEFIK_DASHBOARD_HOST`.
- TLS/ACME: `ACME_EMAIL`, `CLOUDFLARE_DNS_EMAIL`, `CLOUDFLARE_DNS_API_TOKEN`.
- App/API: `API_URL` (recommended: `/api`), `AUTHORIZED_EMAILS_CONTENT` (newline separated).
- OAuth: `OAUTH2_PROXY_CLIENT_ID`, `OAUTH2_PROXY_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET`.
- DB: `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- LLM: `LLM_API_KEY`, `LLM_MODEL_NAME`.
- Tuning: `CONSOLIDATION_BATCH_SIZE`, `FALLBACK_SIMILARITY_THRESHOLD`.

Runtime env (set in server `.env` by the workflow):
- `HINDSIGHT_SERVICE_IMAGE`, `HINDSIGHT_DASHBOARD_IMAGE` (GHCR digests/tags).
- `APP_HOST`, `TRAEFIK_DASHBOARD_HOST`, `HINDSIGHT_SERVICE_API_URL`.
- Backend build meta: `BACKEND_BUILD_SHA`, `FRONTEND_BUILD_SHA`, `BUILD_TIMESTAMP` (informational).

## 8. Deployment Pipeline
- Trigger: push to `main` or `staging`.
- Jobs:
  - Build & push backend image to GHCR.
  - Build & push dashboard image to GHCR.
  - Deploy job (dynamic environment selection; concurrency per branch to avoid overlap).
- Deploy steps (remote host):
  - Copy `docker-compose.app.yml`, `config/`, `templates/`, `letsencrypt/`.
  - Write server `.env` with environment secrets.
  - Replace ACME email placeholder in Traefik config.
  - Authenticate to GHCR, `docker compose pull`, `up -d`.
  - Health check: containers stay Up; logs printed on failure.
- Remote directories:
  - Production: `~/hindsight-ai-production`
  - Staging: `~/hindsight-ai-staging`

## 9. Networking, DNS, TLS
- DNS: `APP_HOST` and `TRAEFIK_DASHBOARD_HOST` point to their respective servers.
- TLS: Traefik obtains certs via Let’s Encrypt DNS‑01 using Cloudflare API.
- Universal SSL limitation: avoid two‑level subdomains like `app.staging.domain`; use single level such as `app-staging.domain` unless you manage a delegated sub‑zone or advanced cert.

## 10. Reverse Proxy & Routing
- Traefik terminates TLS and routes:
  - Dashboard: `Host(${APP_HOST})` → Nginx (dashboard).
  - OAuth paths: `/oauth2/*` to oauth2-proxy.
  - API via oauth2-proxy for app host: `/api` → oauth2-proxy → Nginx → backend.
- Nginx (dashboard container):
  - Proxies `/api/` to backend with auth headers forwarded.
  - Proxies `/guest-api/` to backend without auth headers.
  - Serves SPA with fallback to `index.html`.
  - Serves `/env.js` with `Cache-Control: no-store`.

## 11. Frontend Runtime Configuration
- Single image for all envs with runtime configuration via `env.js` (generated at container start from `HINDSIGHT_SERVICE_API_URL`).
- Build metadata passed as Vite vars: `VITE_VERSION`, `VITE_BUILD_SHA`, `VITE_BUILD_TIMESTAMP`, `VITE_DASHBOARD_IMAGE_TAG` (shown in About dialog).

## 12. Authentication & Authorization
- Identity provider: Google OAuth via oauth2-proxy.
- Cookie domain: `.hindsight-ai.com` (works for staging and production).
- Backend requires auth for mutating operations; unauthenticated POST/PUT/PATCH/DELETE return 401 with a guest‑mode message.
- Guest mode: UI allows read‑only exploration when enabled.

### 10.1 Login & Guest Flow (Authoritative)
- Routes:
  - `/login`: dedicated full‑screen login page.
  - `/dashboard`: main app dashboard route.
  - `/`: trampoline — if authenticated, redirect to `/dashboard`; else if not in guest mode, redirect to `/login`.
- Header “Sign In” button (top‑right):
  - Goes directly to `/oauth2/sign_in?rd=<current_path>` (no stop at `/login`).
- Login page “Sign In” button:
  - Clears guest mode if set, and goes to `/oauth2/sign_in?rd=/dashboard`.
- Login page “Explore as Guest” button:
  - Enables guest mode and navigates to `/dashboard`.
- After OAuth callback:
  - The app checks `/api/user-info` (never the guest endpoint). If authenticated, guest mode is cleared and the app renders authenticated state in the same tab.
- Unauthenticated fetch to `/api/user-info` may 302 to Google; the UI treats it as “not authenticated” and redirects to `/login` (no crash).

### 10.3 Edge-Case Rules
- Do not auto-redirect to `/login` on any `/oauth2/*` paths (allow direct navigation to oauth2-proxy).
- In guest mode, clicking Sign In does not clear guest pre-redirect; guest is cleared automatically after a successful auth check.

### 10.2 CORS & Security Headers
- Same‑origin allowed automatically by Nginx (origin equals `$scheme://$host`).
- `/env.js` caching disabled.
- OAuth2‑proxy headers forwarded to backend for identity (`X-Auth-Request-*` and `X-Forwarded-*`).

## 13. Backend API Expectations
The backend exposes a FastAPI application with the following expectations:

- General
  - Health: `GET /health` returns `{ status: "ok", service: "hindsight-service" }`.
  - Auth reflection: `GET /user-info` returns `{ authenticated, user, email }` based on oauth2-proxy headers in production; returns a fake dev user locally.
  - Conversations KPI: `GET /conversations/count` returns `{ count }` of unique conversations.
- Agents
  - `POST /agents/` create (unique `agent_name`).
  - `GET /agents/` list (pagination via `skip`, `limit`).
  - `GET /agents/{agent_id}` details.
  - `GET /agents/search/?query=…` simple search.
  - `DELETE /agents/{agent_id}` delete.
- Memory Blocks
  - `GET /memory-blocks/` list with filters:
    - `agent_id`, `conversation_id`, `search_query`, `start_date`, `end_date`, `min/max_feedback_score`, `min/max_retrieval_count`, `keywords` (comma‑separated UUIDs), `sort_by`, `sort_order`, `skip`, `limit`, `include_archived`.
  - `POST /memory-blocks/` create (requires existing agent).
  - `GET /memory-blocks/{id}` details.
  - `PUT /memory-blocks/{id}` update.
  - `POST /memory-blocks/{id}/archive` soft-archive; `DELETE /memory-blocks/{id}/hard-delete` hard delete.
  - Feedback: `POST /memory-blocks/{id}/feedback/` with `{ feedback_type, feedback_details }`.
- Keywords
  - `POST /keywords/`, `GET /keywords/`, `GET /keywords/{id}`, `PUT /keywords/{id}`, `DELETE /keywords/{id}`.
  - Associations: `POST /memory-blocks/{id}/keywords/{keyword_id}` and `DELETE` for removal.
- Pruning
  - `POST /memory/prune/suggest` with `{ batch_size, target_count, max_iterations }` → suggestion payload.
  - `POST /memory/prune/confirm` with `{ memory_block_ids: [...] }` → archive counts.
- Compression (LLM)
  - `POST /memory-blocks/{id}/compress` with optional `{ user_instructions }` → suggestion payload; requires `LLM_API_KEY`.
  - `POST /memory-blocks/{id}/compress/apply` with `{ compressed_content, compressed_lessons_learned }` → updated memory block.
- Keyword Generation (Bulk)
  - `POST /memory-blocks/bulk-generate-keywords` with `{ memory_block_ids: [...] }` → suggestion set.
  - `POST /memory-blocks/bulk-apply-keywords` with `{ applications: [...] }` → results.
- Search
  - Full-text: `GET /memory-blocks/search/fulltext` with `query`, `limit`, optional filters.
  - Semantic (placeholder): `GET /memory-blocks/search/semantic` with `query`, `similarity_threshold`.
  - Hybrid: `GET /memory-blocks/search/hybrid` with weighted params; validates weights sum to 1.0.
- Organizations
  - `GET /organizations/` list organizations for current user (superadmin sees all)
  - `POST /organizations/` create new organization with `{ name, slug }` (creator becomes owner)
  - `GET /organizations/{org_id}` get organization details
  - `PUT /organizations/{org_id}` update organization name/slug (requires owner/admin role)
  - `DELETE /organizations/{org_id}` delete organization (requires owner role)
  - `GET /organizations/{org_id}/members` list organization members
  - `POST /organizations/{org_id}/members` add member with `{ email, role, can_read, can_write }`
  - `PUT /organizations/{org_id}/members/{user_id}` update member role/permissions
  - `DELETE /organizations/{org_id}/members/{user_id}` remove member from organization

Access control
- Read-only enforcement for unauthenticated POST/PUT/PATCH/DELETE via ASGI middleware (checks oauth2-proxy headers).
- Guest consumers must use `/guest-api` proxy in the dashboard, which strips auth headers.
- Organization management requires authentication and appropriate role permissions (owner/admin for most operations).

## 14. Non‑Functional Requirements
- Parity: same container images for staging and production (runtime config only).
- Availability: dashboard, backend, oauth2‑proxy, traefik remain Up after deploy health check.
- Observability: basic container logs visible in CI on failure.
- Security: secrets never baked into images; all secret values come from environment.
- Performance: dashboard loads without blocking on cross‑origin OAuth redirect attempts.

## 15. Local Development Requirements
- Compose dev: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
  - Dashboard at `http://localhost:3000`, API at `http://localhost:8000`.
  - Vite dev proxy forwards `/api` and `/guest-api` to `http://localhost:8000`.
- Standalone dev: `npm run dev` in dashboard, `uvicorn` for backend.

### 13.1 Frontend Dev
- Vite dev server: `npm run dev` in `apps/hindsight-dashboard`.
- Runtime config: `public/env.js` provides defaults for dev; for custom API, set `VITE_HINDSIGHT_SERVICE_API_URL` in `.env.local`.
- Dev proxy (vite.config.js): `/api` and `/guest-api` → `http://localhost:8000`.
- Entry points: `src/main.jsx`, `src/App.jsx`.

### 13.2 Backend Dev
- Uvicorn: `uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000` from `apps/hindsight-service`.
- Database: Postgres 13 via compose; migrations via Alembic (auto-run in container at startup per scripts).
- Env vars: `DATABASE_URL`, `LLM_API_KEY`, `LLM_MODEL_NAME` minimal for full feature coverage.

### 13.3 Docker Compose Dev
- Override file `docker-compose.dev.yml` exposes DB (5432), API (8000), Dashboard (3000) and enables `develop.watch` for hot rebuild.
- Use `./start_hindsight.sh --watch` for watch mode (Compose v2.21+).

## 16. Acceptance Criteria (Key Scenarios)
1) First visit (unauthenticated) to `/` redirects to `/login`.
2) On `/login`, clicking “Sign In” sends user to Google and returns to `/dashboard` authenticated.
3) On `/login`, clicking “Explore as Guest” navigates to `/dashboard` with guest badge and write actions blocked.
4) From any app page (e.g., `/memory-blocks`), top‑right “Sign In” goes directly to Google and returns to the same page authenticated.
5) After successful OAuth, the same tab shows authenticated state without opening a new tab.
6) Switching environments uses the same dashboard image with a different runtime `HINDSIGHT_SERVICE_API_URL`.
7) Certificates are issued successfully for `APP_HOST` and `TRAEFIK_DASHBOARD_HOST`; no literal `${...}` placeholders appear in Traefik logs.
8) CI prevents overlapping deploys per branch (concurrency), and staging deploys never affect production.

## 17. Risks & Mitigations
- OAuth redirect mismatch: ensure Google Cloud OAuth has `https://<APP_HOST>/oauth2/callback` for both envs.
- DNS wildcard limitations: prefer single‑level subdomains (e.g., `app-staging.domain`).
- Browser caching: hard refresh after deploy if UI changes appear inconsistent.

## 18. Change Management
- All changes flow via PRs/branch pushes to `staging` or `main`.
- This document must be updated when routes, auth flows, secrets, or deploy steps change.

---
Last updated: manual

## 19. Frontend Application Shell & Layout
- Layout structure:
  - Fixed left sidebar that never scrolls with page content (positioned fixed; app content accounts for its width).
  - Top header within main content contains page title, scale selector, guest badge (when applicable), notification bell, and user account button.
  - Header layout: Page title and controls on left, notification bell and user account button positioned in top-right corner following standard UX conventions.
  - Main content area scrolls independently (internal scroll container), preserving the fixed sidebar and header positions.
- Responsive behavior:
  - Sidebar collapsible; collapsed width ~16 (Tailwind) vs expanded ~64.
  - Mobile: hamburger button toggles sidebar visibility.
  - Content scale control in header with presets 100%, 75%, 50%; persisted in `localStorage` (`UI_SCALE`).
- Notifications:
  - Global notification container overlays messages (success/info/warning/error).
  - 401 helper shows a persistent prompt with a “refresh auth” action linking to `/oauth2/sign_in?rd=<current>`.
- Guest badge:
  - When in guest mode, header shows “Guest Mode · Read-only”.
  - All mutating actions are blocked with a warning via the notification service.

## 20. Routing Map & Navigation
- Routes:
  - `/login`: full-screen login page (standalone, no app layout).
  - `/dashboard`: default authenticated landing page.
  - `/`: trampoline → `/dashboard` (authenticated) or `/login` (unauthenticated and not guest).
  - `/memory-blocks` (+ detail `/:id`), `/keywords`, `/agents`, `/analytics`, `/consolidation-suggestions`, `/archived-memory-blocks`, `/pruning-suggestions`, `/memory-optimization-center`.
- Navigation:
  - Left sidebar items link to each top-level route; active state highlights current section.
  - Top-right account button: shows avatar initial; unauthenticated shows “Sign In” button.
  - Sign In in header goes directly to `/oauth2/sign_in?rd=<current_path>` (bypasses `/login`).
  - Sign Out redirects to `/oauth2/sign_out?rd=<origin>`.

## 21. Login & Guest Page UX (/login)
- Content:
  - Title, short description, two buttons: “Sign In” (primary) and “Explore as Guest”.
- Behavior:
  - Sign In: navigates to `/oauth2/sign_in?rd=/dashboard`.
  - Explore as Guest: sets session guest mode and navigates to `/dashboard`.
  - No app layout chrome; page fills viewport.

## 20. Dashboard Page (/dashboard)
- KPI cards:
  - Agents count, Memory Blocks count, Conversations count; click opens relevant pages.
  - Loading skeletons while data loads.
- Recent Memory Blocks:
  - List of latest entries with preview, tags, and quick actions.
  - Manual Refresh button updates lists and shows “Last updated”.
- Data sources:
  - Agents: GET `/agents/?limit=…`.
  - Memory blocks count: GET `/memory-blocks/?limit=…` (reads `total_items`).
  - Conversations: GET `/conversations/count`.

## 21. Memory Blocks Page (/memory-blocks)
- Filters & search:
  - Search term, agent filter, conversation filter; synced to URL query (`search`, `agent`, `conversation`).
  - Pagination: `page` query param; page size default 12.
  - Sorting: by `created_at desc`.
- Cards grid:
  - Responsive grid (1/2/3 columns by breakpoint) of memory blocks.
  - Actions per card: View (opens detail modal), Archive, Delete, Suggest Keywords, Compact Memory.
  - Guest mode blocks all mutating actions with clear warnings.
- Pagination controls:
  - Previous/Next buttons; display of range and total.
- Modals:
  - Detail modal: fetches by ID; shows full content, metadata, actions.
  - Compaction modal: runs LLM-driven compression (`POST /memory-blocks/{id}/compress`) and apply (`POST /memory-blocks/{id}/compress/apply`).
- Empty/error states:
  - Clear filters CTA when filters active; Create Memory Block CTA otherwise.

## 22. Keywords Management (/keywords)
- Capabilities:
  - List keywords (GET `/keywords/`).
  - Create, update, delete keywords (POST/PUT/DELETE routes).
  - Associate/disassociate keywords with memory blocks (POST/DELETE `/memory-blocks/{id}/keywords/{keyword_id}`).
  - Suggestions: bulk suggest and apply keywords for selected memory blocks.
- UI:
  - Table/list of keywords with counts/usage; modals for add/edit; bulk apply flows with progress feedback.

## 23. Agents Management (/agents)
- Capabilities:
  - List agents, search, create, delete (GET/POST/DELETE).
- UI:
  - Table/list with search field and add agent modal.

## 24. Consolidation Suggestions (/consolidation-suggestions)
- Capabilities:
  - List suggestions with statuses; view details; validate or reject.
- API:
  - GET `/consolidation-suggestions/` and `/{id}`; POST validate/reject endpoints.

## 25. Pruning Suggestions (/pruning-suggestions)
- Capabilities:
  - Generate pruning suggestions (batched, LLM-assisted) and confirm pruning (archives selected blocks).
- API:
  - POST `/memory/prune/suggest` with `{ batch_size, target_count, max_iterations }`.
  - POST `/memory/prune/confirm` with `{ memory_block_ids: [...] }`.

## 26. Memory Optimization Center (/memory-optimization-center)
- Capabilities:
  - Fetch optimization suggestions, execute selected suggestions, view details.
- API:
  - Under `/memory-optimization/*` (router included in backend), including list, execute, details.

## 27. Search
- Full-text search:
  - GET `/memory-blocks/search/fulltext?query=…&limit=…&include_archived=`.
- Semantic search (placeholder):
  - GET `/memory-blocks/search/semantic?query=…&similarity_threshold=…`.
- Hybrid search:
  - GET `/memory-blocks/search/hybrid?query=…&fulltext_weight=…&semantic_weight=…&min_combined_score=…`.

## 28. Data Model (High-level)
- Agent: `{ agent_id (UUID), agent_name, created_at, updated_at }`.
- MemoryBlock: `{ id (UUID), agent_id, conversation_id, timestamp, content, errors, lessons_learned, metadata(JSON), feedback_score, retrieval_count, archived, archived_at, created_at, updated_at, search_vector, content_embedding }`.
- FeedbackLog: `{ feedback_id, memory_id, feedback_type, feedback_details, created_at }`.
- Keyword: `{ keyword_id, keyword_text, created_at }`.
- MemoryBlockKeyword: join table `{ memory_id, keyword_id }`.
- ConsolidationSuggestion: `{ suggestion_id, group_id, suggested_content, suggested_lessons_learned, suggested_keywords(JSON), original_memory_ids(JSON), status, timestamp, created_at, updated_at }`.

## 29. Write-Access Enforcement & Headers
- Backend enforces read-only for unauthenticated requests across POST/PUT/PATCH/DELETE via ASGI middleware.
- oauth2-proxy passes identity headers and auth token to Nginx → backend:
  - X-Auth-Request-User, X-Auth-Request-Email, X-Auth-Request-Access-Token, Authorization.
- Backend accepts either `X-Auth-Request-*` or `X-Forwarded-*` identity headers on `/user-info`.

## 30. OAuth & Cookies
- oauth2-proxy configuration:
  - Provider: Google; Redirect URL: `https://<APP_HOST>/oauth2/callback`.
  - Upstream: dashboard container.
  - Cookie domain: `.hindsight-ai.com`; Secure; SameSite=Lax; reverse-proxy mode.
  - Skip auth: `/manifest.json`, `/favicon.ico`, `/guest-api/*`.
- Session persistence: cookie available on both staging and production due to shared eTLD+1.

## 31. Error Pages & Templates
- Custom 403 page (templates/error.html) for unauthorized emails with admin contact and sign-out.

## 32. Accessibility & UX Guidelines
- Keyboard focus maintained across modal open/close; ESC closes modals.
- Sufficient color contrast for critical elements; visible focus states on interactive elements.
- Loading states with skeletons where applicable to avoid layout shift.

## 33. Performance & Caching
- SPA assets under `/assets/` are immutable and cached for 1 year.
- `/env.js` is never cached and must be requested fresh at load.
- Avoid blocking UI on cross-origin OAuth redirects; handle as unauthenticated state.

## 34. Security & Privacy
- No secrets in frontend bundles; runtime config exposes only public endpoints.
- All cookies marked Secure and SameSite=Lax via oauth2-proxy.
- Restrictive CSRF policy on Nginx for mutating methods; same-origin permitted.

## 35. Operational Playbook (Staging/Production)
- Staging and production use the same images; config differs via `.env`.
- Concurrency ensures only one deploy per branch.
- To rotate oauth2-proxy cookies or client secrets: update environment secrets and redeploy.
- To reset Let’s Encrypt: set `recreate_acme_json` input to true on manual workflow dispatch.
- oauth2-proxy parameters (compose env):
  - `OAUTH2_PROXY_PROVIDER=google`
  - `OAUTH2_PROXY_REDIRECT_URL=https://<APP_HOST>/oauth2/callback`
  - `OAUTH2_PROXY_UPSTREAMS=http://hindsight-dashboard:80`
  - `OAUTH2_PROXY_COOKIE_SAMESITE=lax`, `OAUTH2_PROXY_COOKIE_SECURE=true`, cookie domain `.hindsight-ai.com`
  - `OAUTH2_PROXY_REVERSE_PROXY=true`, `OAUTH2_PROXY_SET_XAUTHREQUEST=true`, `OAUTH2_PROXY_PASS_ACCESS_TOKEN=true`, `OAUTH2_PROXY_SET_AUTHORIZATION_HEADER=true`
  - `OAUTH2_PROXY_SKIP_AUTH_ROUTES=/manifest.json$,/favicon.ico$,^/guest-api/.*`
  - `OAUTH2_PROXY_EMAIL_DOMAINS=*` to accept any Google account that completes OAuth (set `OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE=/etc/oauth2-proxy/authorized_emails.txt` and mount `authorized_emails.txt` only if you need to reinstate a closed allowlist).
  - `OAUTH2_PROXY_LOGOUT_REDIRECT_URL=https://accounts.google.com/Logout`

Traefik labels:
- Dashboard router: `Host(${TRAEFIK_DASHBOARD_HOST})` → `api@internal` over `websecure` with `letsencrypt` resolver.
- OAuth routers: `Host(${APP_HOST}) && PathPrefix('/oauth2')` and `Host(${APP_HOST}) && PathPrefix('/api')` → `oauth2-proxy`.
- App router: `Host(${APP_HOST})` → dashboard (port 80).
