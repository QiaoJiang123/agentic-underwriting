(function () {
  const form = document.querySelector("#loginForm");
  const usernameInput = document.querySelector("#loginUsername");
  const passwordInput = document.querySelector("#loginPassword");
  const status = document.querySelector("#loginStatus");
  const sessionCard = document.querySelector("#loginSessionCard");

  const params = new URLSearchParams(window.location.search);
  const redirectTarget = params.get("redirect") || "/";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "Logging in...";
    try {
      const data = await AUApi.post("/api/auth/login", {
        username: usernameInput.value,
        password: passwordInput.value
      });
      const auth = data.login.auth;
      status.textContent = `Logged in as ${auth.display_name}.`;
      renderSession(auth, data.login.expires_at);
      window.location.href = redirectTarget;
    } catch (error) {
      status.textContent = error.message || "Login failed.";
    }
  });

  async function loadSession() {
    try {
      const data = await AUApi.get("/api/auth/context");
      renderSession(data.auth, null);
    } catch (error) {
      sessionCard.innerHTML = `<p class="empty-state">${escapeHtml(error.message || "Unable to load session.")}</p>`;
    }
  }

  function renderSession(auth, expiresAt) {
    sessionCard.innerHTML = `
      <div class="login-session-grid">
        <div>
          <span>Current User</span>
          <strong>${escapeHtml(auth.display_name || auth.user_id || "Unknown")}</strong>
        </div>
        <div>
          <span>Role</span>
          <strong>${escapeHtml(auth.role_label || auth.role || "Unknown")}</strong>
        </div>
        <div>
          <span>Auth Source</span>
          <strong>${escapeHtml(auth.auth_source || "Unknown")}</strong>
        </div>
        <div>
          <span>Session</span>
          <strong>${escapeHtml(expiresAt ? `Expires ${expiresAt}` : "Active or default")}</strong>
        </div>
      </div>
      <button class="ghost-button login-logout-button" id="logoutButton" type="button">Log Out</button>
    `;
    const logoutButton = document.querySelector("#logoutButton");
    logoutButton.addEventListener("click", async () => {
      status.textContent = "Logging out...";
      await AUApi.post("/api/auth/logout", {});
      status.textContent = "Logged out. Local default demo user may still be used for unauthenticated demo routes.";
      await loadSession();
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  loadSession();
})();
