import {
  FEATURE_FLAG_DEFAULTS,
  FEATURE_FLAG_ENV_KEYS,
  FeatureFlagsState,
  deriveApiFlagOverrides,
  mergeFeatureFlags,
  normalizeFlagValue,
  readFlagsFromRuntime,
} from '../featureFlags';
import { CurrentUserInfo } from '../../api/authService';

describe('normalizeFlagValue', () => {
  it('parses string representations consistently', () => {
    expect(normalizeFlagValue('false', true)).toBe(false);
    expect(normalizeFlagValue('FALSE', true)).toBe(false);
    expect(normalizeFlagValue('1', false)).toBe(true);
    expect(normalizeFlagValue('on', false)).toBe(true);
  });

  it('falls back to default for unknown values', () => {
    expect(normalizeFlagValue('maybe', false)).toBe(false);
    expect(normalizeFlagValue(42 as unknown as string, true)).toBe(true);
  });
});

describe('readFlagsFromRuntime', () => {
  it('returns defaults when runtime env is missing', () => {
    const result = readFlagsFromRuntime(undefined);
    expect(result).toEqual(FEATURE_FLAG_DEFAULTS);
    expect(result).not.toBe(FEATURE_FLAG_DEFAULTS);
  });

  it('coerces runtime strings into booleans using env keys', () => {
    const runtimeEnv = Object.entries(FEATURE_FLAG_ENV_KEYS).reduce<Record<string, unknown>>(
      (acc, [, envKey]) => {
        acc[envKey] = 'false';
        return acc;
      },
      {},
    );

    const result = readFlagsFromRuntime(runtimeEnv);
    Object.values(result).forEach(value => expect(value).toBe(false));
  });
});

describe('mergeFeatureFlags', () => {
  it('returns the original object when no override changes occur', () => {
    const base: FeatureFlagsState = { ...FEATURE_FLAG_DEFAULTS };
    const merged = mergeFeatureFlags(base, { llmEnabled: base.llmEnabled });
    expect(merged).toBe(base);
  });

  it('applies overrides immutably when values change', () => {
    const base: FeatureFlagsState = { ...FEATURE_FLAG_DEFAULTS };
    const merged = mergeFeatureFlags(base, { llmEnabled: false });

    expect(merged).not.toBe(base);
    expect(merged.llmEnabled).toBe(false);
    expect(base.llmEnabled).toBe(true);
  });
});

describe('deriveApiFlagOverrides', () => {
  it('extracts boolean fields from CurrentUserInfo', () => {
    const info: CurrentUserInfo = {
      authenticated: true,
      llm_features_enabled: false,
    };

    expect(deriveApiFlagOverrides(info)).toEqual({ llmEnabled: false });
  });

  it('ignores non-boolean values', () => {
    const info = {
      authenticated: true,
      llm_features_enabled: 'nope',
    } as unknown as CurrentUserInfo;

    expect(deriveApiFlagOverrides(info)).toEqual({});
  });
});
