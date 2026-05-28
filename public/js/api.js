(function () {
  async function request(path, options = {}) {
    const headers = {
      ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {})
    };
    const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const detail = data.detail || {};
      const message = data.error || detail.error || (typeof detail === "string" ? detail : "");
      throw new Error(message || `Request failed: ${response.status}`);
    }

    return data;
  }

  window.AUApi = {
    get(path) {
      return request(path);
    },
    post(path, body) {
      return request(path, {
        method: "POST",
        body: body instanceof FormData ? body : JSON.stringify(body || {})
      });
    },
    put(path, body) {
      return request(path, {
        method: "PUT",
        body: JSON.stringify(body || {})
      });
    },
    delete(path) {
      return request(path, { method: "DELETE" });
    }
  };
})();
