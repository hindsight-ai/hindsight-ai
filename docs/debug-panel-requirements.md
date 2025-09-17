# Debug Panel Requirements

## Overview
Implement a debug panel component that is only visible in development mode to facilitate end-to-end testing of toast notifications and other debug functionality.

## Requirements

### Functional Requirements
1. **Dev Mode Only Visibility**
   - Debug panel must only be visible when `VITE_DEV_MODE=true` or `NODE_ENV=development`
   - Must not be visible in production builds
   - Must not be accessible via any production URLs

2. **Toast Notification Testing**
   - Provide buttons to trigger different types of toast notifications with specific icons:
     - ✅ **Success** - Green success notifications
     - ℹ️ **Info** - Blue informational notifications
     - ⚠️ **Warning** - Yellow warning notifications
     - ❌ **Error** - Red error notifications
     - 🌐 **Network Error** - Gray network error notifications
     - 🚫 **403** - Orange permission denied notifications
     - 🔍 **404** - Purple not found notifications
     - 💥 **500 Server Error** - Dark red server error notifications
   - Each button should trigger the corresponding toast type with appropriate test messages
   - Toast notifications must display the specified icons alongside the messages

3. **UI/UX Requirements**
   - Panel should be visually distinct (e.g., colored border, debug label)
   - Should be positioned in a non-intrusive location (e.g., bottom-right corner)
   - Should be collapsible/expandable
   - Should have clear labeling for each test button
   - **Notifications must appear in the bottom-right corner of the screen**
   - **Notifications must stack upwards (newer notifications appear above older ones)**

4. **Technical Requirements**
   - Must use existing toast notification system
   - Must integrate with current notification service
   - Must be implemented as a reusable React component
   - Must follow existing code patterns and styling

## Acceptance Criteria

### Development Environment
- [ ] Debug panel is visible when `VITE_DEV_MODE=true`
- [ ] Debug panel is hidden when `VITE_DEV_MODE=false` or not set
- [ ] Debug panel is not present in production builds
- [ ] Debug panel is accessible via navigation menu in development mode
- [ ] Debug panel is not accessible in production mode
- [ ] Debug panel is not accessible in guest mode
- [ ] Debug panel is not accessible for regular authenticated users (non-dev mode)
- [ ] Debug panel is accessible via navigation menu in development mode
- [ ] Debug panel is not accessible in production mode
- [ ] Debug panel is not accessible in guest mode
- [ ] Debug panel is not accessible for regular authenticated users (non-dev mode)

### Toast Notification Testing
- [ ] Info button triggers info toast with test message
- [ ] Warning button triggers warning toast with test message
- [ ] Error button triggers error toast with test message
- [ ] Success button triggers success toast with test message
- [ ] All toasts display correctly with proper styling
- [ ] All toasts auto-dismiss after appropriate timeout
- [ ] Success toasts display with ✅ green styling
- [ ] Info toasts display with ℹ️ blue styling
- [ ] Warning toasts display with ⚠️ yellow styling
- [ ] Error toasts display with ❌ red styling
- [ ] Network error toasts display with 🌐 gray styling
- [ ] 403 error toasts display with 🚫 orange styling
- [ ] 404 error toasts display with 🔍 purple styling
- [ ] 500 error toasts display with 💥 dark red styling

### UI/UX
- [ ] Panel has clear "DEBUG" label
- [ ] Panel is positioned in bottom-right corner
- [ ] Panel has distinct visual styling (e.g., red border)
- [ ] Panel is collapsible/expandable
- [ ] Buttons are clearly labeled and accessible
- [ ] **Notifications appear in bottom-right corner of screen**
- [ ] **Notifications stack upwards (newer on top)**
- [ ] **Notification close buttons are clickable (not blocked by other elements)**

### Technical Implementation
- [ ] Component uses existing toast notification hooks/services
- [ ] Component follows existing TypeScript patterns
- [ ] Component uses existing CSS/styling system
- [ ] No console errors or warnings
- [ ] Component is properly typed

## Implementation Notes

### Environment Detection
```typescript
const isDevMode = import.meta.env.VITE_DEV_MODE === 'true' || import.meta.env.DEV;
```

### Toast Integration
- Use existing `useToast` hook or notification service
- Ensure compatibility with current toast implementation
- Test with various toast configurations

### Security Considerations
- Ensure debug panel cannot be enabled in production
- Verify that debug functionality doesn't expose sensitive information
- Confirm that debug panel doesn't affect production performance

## Testing Strategy

### Unit Tests
- Test component rendering in dev mode
- Test component not rendering in production mode
- Test button click handlers
- Test toast notification integration

### Integration Tests
- Test end-to-end toast notification flow
- Test debug panel visibility toggling
- Test multiple toast notifications

### E2E Tests
- Test debug panel presence/absence based on environment
- Test toast notification triggering and display
- Test debug panel in different viewport sizes

## Future Enhancements
- Add more debug functionality (API testing, state inspection, etc.)
- Add configurable toast options (duration, position, etc.)
- Add logging/debugging utilities
- Add performance monitoring tools
