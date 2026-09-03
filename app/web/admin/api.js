// Admin API layer migration target.
// Phase 1.5 keeps existing admin.js request handling unchanged.
// Future commits will move fetch wrappers here.

export async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    throw new Error("authentication required");
  }
  return response;
}
