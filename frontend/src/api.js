export const API_URL = import.meta.env.VITE_API_URL || '';
export async function apiFetch(path, options = {}) {
  let response;
  try { response = await fetch(path, {
    ...options, credentials: 'include',
    headers: { 'X-CareerNova-Client': 'web', ...options.headers },
  }); } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Connection interrupted. Your change could not be confirmed. Refresh your saved jobs before retrying; the free server may be waking up.');
  }
  if (response.status === 401 && !/\/api\/auth\//.test(path)) {
    window.dispatchEvent(new Event('careernova-session-expired'));
  }
  return response;
}
export async function request(path, options = {}) {
  const response = await apiFetch(`${API_URL}${path}`, {
    ...options, headers: { 'Content-Type': 'application/json', ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map(x => x.msg).join('; ') : 'Request failed. Please try again.');
  return data;
}
