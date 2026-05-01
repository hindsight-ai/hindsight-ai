import { apiFetch, jsonOrThrow } from './http';

export const getBuildInfo = async () => {
  const resp = await apiFetch('/build-info');
  return jsonOrThrow(resp);
};

export const getConversationsCount = async () => {
  const params = new URLSearchParams();
  const resp = await apiFetch('/conversations/count', { searchParams: params });
  return jsonOrThrow(resp);
};

const metaService = {
  getBuildInfo,
  getConversationsCount,
};

export default metaService;
