export type ActiveScope = 'personal' | 'organization' | 'public' | undefined;

export interface ScopeSnapshot {
  scope: ActiveScope;
  orgId: string | undefined;
}

// Default provider reads from localStorage (the persistence seed).
// This handles the boot window where API calls fire before OrganizationContext
// mounts (e.g., AuthContext.refresh() → /user-info). Once OrganizationContext
// mounts, it overrides this provider via setScopeProvider() with live React
// state. localStorage is only written by OrganizationContext and survives across
// page reloads, so first-load API calls preserve the user's last-used scope.
const defaultProvider = (): ScopeSnapshot => {
  try {
    const stored = localStorage.getItem('selectedScope');
    const scope: ActiveScope =
      stored === 'organization' || stored === 'personal' || stored === 'public'
        ? stored
        : undefined;
    const orgId = localStorage.getItem('selectedOrganizationId') ?? undefined;
    return { scope, orgId };
  } catch {
    return { scope: undefined, orgId: undefined };
  }
};

let provider: () => ScopeSnapshot = defaultProvider;

export const setScopeProvider = (fn: () => ScopeSnapshot): void => {
  provider = fn;
};

export const getScope = (): ScopeSnapshot => provider();

// Test helper: restore the default provider (reads localStorage).
export const __resetScopeProviderForTests = (): void => {
  provider = defaultProvider;
};
