import { CurrentUserInfo } from '../api/authService';

export type FeatureFlagKey =
  | 'llmEnabled'
  | 'consolidationEnabled'
  | 'pruningEnabled'
  | 'archivedEnabled';

interface FeatureFlagConfig {
  envKey: string;
  defaultValue: boolean;
  apiField?: keyof CurrentUserInfo;
}

const FEATURE_FLAG_CONFIG: Record<FeatureFlagKey, FeatureFlagConfig> = {
  llmEnabled: {
    envKey: 'LLM_FEATURES_ENABLED',
    defaultValue: true,
    apiField: 'llm_features_enabled',
  },
  consolidationEnabled: {
    envKey: 'FEATURE_CONSOLIDATION_ENABLED',
    defaultValue: true,
  },
  pruningEnabled: {
    envKey: 'FEATURE_PRUNING_ENABLED',
    defaultValue: true,
  },
  archivedEnabled: {
    envKey: 'FEATURE_ARCHIVED_ENABLED',
    defaultValue: true,
  },
};

const FEATURE_FLAG_KEYS = Object.keys(FEATURE_FLAG_CONFIG) as FeatureFlagKey[];

export type FeatureFlagsState = Record<FeatureFlagKey, boolean>;

export const FEATURE_FLAG_DEFAULTS: FeatureFlagsState = Object.freeze(
  FEATURE_FLAG_KEYS.reduce<Record<FeatureFlagKey, boolean>>((acc, key) => {
    acc[key] = FEATURE_FLAG_CONFIG[key].defaultValue;
    return acc;
  }, {} as Record<FeatureFlagKey, boolean>),
);

export const FEATURE_FLAG_ENV_KEYS = Object.freeze(
  FEATURE_FLAG_KEYS.reduce<Record<FeatureFlagKey, string>>((acc, key) => {
    acc[key] = FEATURE_FLAG_CONFIG[key].envKey;
    return acc;
  }, {} as Record<FeatureFlagKey, string>),
);

export function normalizeFlagValue(rawValue: unknown, fallback: boolean): boolean {
  if (typeof rawValue === 'boolean') return rawValue;
  if (typeof rawValue === 'string') {
    const normalized = rawValue.trim().toLowerCase();
    if (['', '0', 'false', 'no', 'off'].includes(normalized)) return false;
    if (['1', 'true', 'yes', 'on'].includes(normalized)) return true;
  }
  return fallback;
}

export function readFlagsFromRuntime(runtimeEnv: Record<string, unknown> | undefined | null): FeatureFlagsState {
  const source = runtimeEnv ?? {};
  return FEATURE_FLAG_KEYS.reduce<Record<FeatureFlagKey, boolean>>((acc, key) => {
    const { envKey, defaultValue } = FEATURE_FLAG_CONFIG[key];
    acc[key] = normalizeFlagValue((source as Record<string, unknown>)[envKey], defaultValue);
    return acc;
  }, { ...FEATURE_FLAG_DEFAULTS });
}

export function mergeFeatureFlags(
  base: FeatureFlagsState,
  overrides?: Partial<FeatureFlagsState>,
): FeatureFlagsState {
  if (!overrides) return base;
  let changed = false;
  const next = { ...base } as FeatureFlagsState;
  FEATURE_FLAG_KEYS.forEach(key => {
    const override = overrides[key];
    if (typeof override === 'boolean' && override !== next[key]) {
      next[key] = override;
      changed = true;
    }
  });
  return changed ? next : base;
}

export function deriveApiFlagOverrides(info?: CurrentUserInfo | null): Partial<FeatureFlagsState> {
  if (!info) return {};
  const overrides: Partial<FeatureFlagsState> = {};
  FEATURE_FLAG_KEYS.forEach(key => {
    const field = FEATURE_FLAG_CONFIG[key].apiField;
    if (!field) return;
    const value = info[field];
    if (typeof value === 'boolean') {
      overrides[key] = value;
    }
  });
  return overrides;
}
