export const isValidUuid = (value: string): boolean => {
  if (!value) {
    return false;
  }

  const trimmed = value.trim();
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidPattern.test(trimmed);
};

export const sanitizeUuidInput = (value: string): string => value.trim();
