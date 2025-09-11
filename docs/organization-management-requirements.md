# Organization Management Requirements & Acceptance Matrix

## Overview
This document defines the requirements for organization management functionality, with special consideration for superadmin access patterns to prevent accidental data access.

## User Roles & Permissions

### Regular User
- **Organization Switcher**: Can only see and switch to organizations where they are members
- **Organization Creation**: Can create new organizations and automatically become owner
- **Organization Management**: Can manage organizations where they have owner or admin role
- **Data Access**: Only to organizations where they are members

### Superadmin
- **Organization Switcher**: Can only see and switch to organizations where they are members (same as regular users)
- **Organization Management**: Full administrative access with safety mechanisms for ALL organizations
- **Data Access**: Only to organizations where they are members (data privacy preserved)

## Organization Management Panel Access Control

### Access Requirements
- **Who can access**: 
  - Regular users: Can access to manage organizations where they have owner/admin role
  - Superadmins: Can access to manage ALL organizations (`is_superadmin: true`)
- **Access denied behavior**: Show clear message if user has no manageable organizations

### Organization Display Modes

#### Mode 1: Member Organizations (Default)
- **Default view**: Shows only organizations where superadmin is a member
- **Visual styling**: Standard styling, clear and familiar
- **Interaction**: Can immediately manage these organizations
- **Purpose**: Safe default for routine organization management tasks

#### Mode 2: All Organizations (Explicit Opt-in)
- **Access method**: Requires explicit user action (toggle/button)
- **Visual indicators**: 
  - Clear visual distinction between member vs non-member organizations
  - Green border/background for organizations where superadmin is a member
  - Red border/background for organizations where superadmin is NOT a member
  - Badge/tag indicating membership status ("Member" vs "Admin Access Only")
- **Warning mechanism**: Confirmation prompt when accessing non-member organization
- **Purpose**: Administrative tasks on all organizations

### Safety Mechanisms

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

## Implementation Specifications

### Backend Endpoints

#### `/organizations/` 
- **Purpose**: Organization switcher dropdown
- **Returns**: Only organizations where user is a member
- **Access**: All authenticated users
- **Behavior**: Same for regular users and superadmins

#### `/organizations/manageable`
- **Purpose**: Organization management (organizations user can manage)
- **Returns**: Organizations where user has owner/admin role, or all organizations for superadmins
- **Access**: All authenticated users
- **Behavior**: Regular users see only their manageable orgs, superadmins see all

#### `/organizations/admin`
- **Purpose**: Legacy superadmin-only endpoint for all organizations
- **Returns**: All organizations with `created_by` information
- **Access**: Superadmins only (`is_superadmin: true`)
- **Error**: 403 Forbidden for non-superadmins

#### `/organizations/{org_id}/members`
- **Purpose**: Get organization membership information
- **Returns**: List of organization members
- **Access**: Organization members + superadmins
- **Usage**: Determine superadmin's membership status

### Frontend Components

#### OrganizationManagement Component

##### State Management
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

##### Safety Controls
- Default to 'member' mode
- Require explicit toggle to 'all' mode
- Show confirmation dialog when switching to 'all' mode
- Visual indicators for membership status
- Warning when selecting non-member organization

## Acceptance Criteria

### AC1: Organization Switcher (Both User Types)
- [ ] Shows only organizations where user is a member
- [ ] Allows switching only to member organizations
- [ ] Returns appropriate error for non-member organization access
- [ ] Consistent behavior between regular users and superadmins

### AC2: Organization Management Access Control
- [ ] Regular users can access organization management panel for organizations they own/admin
- [ ] Regular users can create, edit, delete organizations where they have owner/admin role
- [ ] Regular users can manage members of organizations they own/admin
- [ ] Superadmins can access organization management panel for ALL organizations
- [ ] Superadmins can create, edit, delete all organizations
- [ ] Superadmins can manage members of all organizations
- [ ] Users with no manageable organizations see appropriate message

### AC3: Safe Default Behavior 
- [ ] Regular users: Organization management shows only organizations they can manage (owner/admin role)
- [ ] Superadmins: Organization management shows only member organizations by default
- [ ] Clear visual indication of current view mode for superadmins
- [ ] Familiar, uncluttered interface in default mode
- [ ] Can perform all routine tasks without switching modes

### AC4: Explicit All-Organizations Access (Superadmin)
- [ ] Requires explicit user action to view all organizations
- [ ] Shows confirmation dialog when switching to "all organizations" mode
- [ ] Clear visual distinction between member vs non-member organizations
- [ ] Membership status badges/indicators visible
- [ ] Can switch back to member-only view easily

### AC5: Visual Safety Indicators
- [ ] Green styling for member organizations
- [ ] Red styling for non-member organizations  
- [ ] "Member" vs "Admin Access Only" badges
- [ ] Current mode clearly displayed (Member Organizations / All Organizations)
- [ ] Prominent mode toggle button

### AC6: Interaction Safety
- [ ] Warning dialog when selecting non-member organization for management
- [ ] Confirmation required for destructive actions on non-member organizations
- [ ] Breadcrumb or context indicator showing current organization's membership status
- [ ] Clear "back to member organizations" option always available

### AC7: Data Access Boundaries (Both User Types)
- [ ] Users can only access data from organizations where they are members
- [ ] Superadmins cannot access organization data they're not members of
- [ ] API endpoints enforce membership-based data access
- [ ] Clear error messages for unauthorized data access attempts

### AC8: Organization Dropdown Auto-refresh
- [ ] Organization dropdown automatically refreshes after creating new organization
- [ ] Organization dropdown automatically refreshes after exiting organization management panel
- [ ] New organizations become immediately available for selection without page reload
- [ ] Smooth UX transition with no manual refresh required

## User Experience Flow

### Superadmin Organization Management Flow

1. **Initial Access**: Opens organization management → sees only member organizations
2. **Routine Management**: Can immediately manage member organizations (safe zone)
3. **Admin Tasks**: Clicks "Show All Organizations" → confirmation dialog → sees all organizations with visual indicators
4. **Safe Selection**: Green organizations = member (can access data), Red organizations = admin-only (management only)
5. **Return to Safety**: Can easily return to member-only view

### Error Prevention Mechanisms

1. **Visual Cues**: Immediate visual feedback about membership status
2. **Default Safety**: Safe behavior by default, dangerous behavior requires opt-in
3. **Confirmation Dialogs**: Extra confirmation for potentially risky actions
4. **Clear Context**: Always know what mode you're in and what access you have

## Technical Considerations

### Performance
- Minimize API calls by caching membership information
- Efficient filtering for large numbers of organizations

### Security  
- Server-side validation of all permissions
- Client-side indicators are UX only, not security boundaries
- Audit logging for superadmin actions on non-member organizations

### Accessibility
- Clear visual indicators that work with screen readers
- Keyboard navigation support for mode switching
- High contrast options for color-coded indicators

## Future Enhancements

1. **Audit Trail**: Log superadmin access to non-member organizations
2. **Temporary Access**: Time-limited access grants for specific organizations
3. **Delegation**: Allow organization owners to grant temporary admin access
4. **Notification**: Alert organization owners when superadmin accesses their organization
