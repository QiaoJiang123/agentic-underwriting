(function () {
  const DEMO_USERNAME = "admin";
  const DEMO_PASSWORD = "AU-Admin-2026!";
  const LOGIN_SOURCE = "local login session";

  let state = {
    auth: null,
    loggedIn: false,
    loaded: false,
    error: ""
  };
  let widget = null;
  let loginModal = null;
  let loginPromise = null;
  let resolveLoginPromise = null;

  const ready = init();

  window.AUAuth = {
    ready,
    getState: () => ({ ...state }),
    isLoggedIn: () => Boolean(state.loggedIn),
    refresh,
    requireLogin,
    openLoginModal,
    logout
  };

  async function init() {
    mountWidget();
    renderWidget();
    await refresh();
  }

  function mountWidget() {
    const placeholder = document.querySelector(".auth-header-link, .login-nav-button");
    widget = document.createElement("div");
    widget.className = placeholder && placeholder.classList.contains("auth-header-link")
      ? "auth-widget inline-auth-widget"
      : "auth-widget floating-auth-widget";
    widget.setAttribute("aria-live", "polite");

    if (placeholder) {
      placeholder.replaceWith(widget);
    } else {
      document.body.appendChild(widget);
    }
  }

  async function refresh() {
    try {
      const data = await AUApi.get("/api/auth/context");
      const auth = data.auth || {};
      state = {
        auth,
        loggedIn: auth.auth_source === LOGIN_SOURCE,
        loaded: true,
        error: ""
      };
    } catch (error) {
      state = {
        auth: null,
        loggedIn: false,
        loaded: true,
        error: error.message || "Unable to load login status."
      };
    }
    renderWidget();
    return { ...state };
  }

  async function requireLogin({ reason = "Please log in to continue." } = {}) {
    await ready.catch(() => null);
    if (state.loggedIn) {
      return true;
    }
    return openLoginModal({ reason });
  }

  async function logout() {
    await AUApi.post("/api/auth/logout", {});
    await refresh();
    window.dispatchEvent(new CustomEvent("au-auth-changed", { detail: { ...state } }));
  }

  function renderWidget() {
    if (!widget) {
      return;
    }

    if (!state.loaded) {
      widget.innerHTML = `
        <button class="auth-avatar-button loading" type="button" aria-label="Loading login status" disabled>
          AU
        </button>
      `;
      return;
    }

    if (!state.loggedIn) {
      widget.innerHTML = `
        <button class="ghost-button auth-login-button" type="button">
          Login
        </button>
      `;
      widget.querySelector(".auth-login-button").addEventListener("click", () => {
        openLoginModal({ reason: "Log in to search, add submissions, and access protected tools." });
      });
      return;
    }

    const auth = state.auth || {};
    const initials = getInitials(auth.display_name || auth.user_id || "AU");
    widget.innerHTML = `
      <button class="auth-avatar-button" type="button" aria-label="User menu" aria-haspopup="menu" aria-expanded="false">
        ${escapeHtml(initials)}
      </button>
      <div class="auth-menu" role="menu" hidden>
        <div class="auth-menu-profile">
          <span>Signed in</span>
          <strong>${escapeHtml(auth.display_name || auth.user_id || "User")}</strong>
          <small>${escapeHtml(auth.role_label || auth.role || "Underwriter")}</small>
        </div>
        <button class="auth-menu-action" type="button" role="menuitem">Log out</button>
      </div>
    `;

    const avatarButton = widget.querySelector(".auth-avatar-button");
    const menu = widget.querySelector(".auth-menu");
    const logoutButton = widget.querySelector(".auth-menu-action");
    avatarButton.addEventListener("click", () => {
      const isOpen = menu.hasAttribute("hidden");
      menu.toggleAttribute("hidden", !isOpen);
      menu.classList.toggle("open", isOpen);
      avatarButton.setAttribute("aria-expanded", String(isOpen));
    });
    logoutButton.addEventListener("click", async () => {
      logoutButton.disabled = true;
      try {
        await logout();
      } catch (error) {
        console.warn(error);
        logoutButton.disabled = false;
      }
    });
  }

  function ensureLoginModal() {
    if (loginModal) {
      return loginModal;
    }

    loginModal = document.createElement("div");
    loginModal.className = "auth-modal";
    loginModal.setAttribute("aria-hidden", "true");
    loginModal.innerHTML = `
      <div class="auth-modal-backdrop" data-auth-modal-close></div>
      <section class="auth-modal-panel" role="dialog" aria-modal="true" aria-labelledby="authModalTitle">
        <header class="auth-modal-header">
          <div>
            <p class="eyebrow">Protected Demo</p>
            <h2 id="authModalTitle">Login Required</h2>
          </div>
          <button class="ghost-button auth-modal-close" type="button" data-auth-modal-close>Close</button>
        </header>
        <p class="auth-modal-reason" id="authModalReason">Please log in to continue.</p>
        <form class="auth-modal-form" id="authModalForm">
          <label>
            <span>Username</span>
            <input id="authModalUsername" type="text" autocomplete="username" value="${DEMO_USERNAME}" />
          </label>
          <label>
            <span>Password</span>
            <input id="authModalPassword" type="password" autocomplete="current-password" value="${DEMO_PASSWORD}" />
          </label>
          <p class="auth-modal-demo">Demo login is prefilled for local testing.</p>
          <p class="auth-modal-status" id="authModalStatus"></p>
          <div class="auth-modal-actions">
            <button class="ghost-button" type="button" data-auth-modal-close>Cancel</button>
            <button class="send-button" type="submit">Log In</button>
          </div>
        </form>
      </section>
    `;
    document.body.appendChild(loginModal);

    loginModal.querySelectorAll("[data-auth-modal-close]").forEach((button) => {
      button.addEventListener("click", () => closeLoginModal(false));
    });
    loginModal.querySelector("#authModalForm").addEventListener("submit", submitLoginModal);

    return loginModal;
  }

  function openLoginModal({ reason = "Please log in to continue." } = {}) {
    const modal = ensureLoginModal();
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    modal.querySelector("#authModalReason").textContent = reason;
    modal.querySelector("#authModalStatus").textContent = "";
    modal.querySelector("#authModalUsername").value = DEMO_USERNAME;
    modal.querySelector("#authModalPassword").value = DEMO_PASSWORD;
    window.setTimeout(() => modal.querySelector("#authModalUsername").focus(), 0);

    if (!loginPromise) {
      loginPromise = new Promise((resolve) => {
        resolveLoginPromise = resolve;
      });
    }
    return loginPromise;
  }

  async function submitLoginModal(event) {
    event.preventDefault();
    const modal = ensureLoginModal();
    const status = modal.querySelector("#authModalStatus");
    const submitButton = modal.querySelector('.auth-modal-form button[type="submit"]');
    const username = modal.querySelector("#authModalUsername").value;
    const password = modal.querySelector("#authModalPassword").value;

    status.textContent = "Logging in...";
    submitButton.disabled = true;
    try {
      await AUApi.post("/api/auth/login", { username, password });
      await refresh();
      window.dispatchEvent(new CustomEvent("au-auth-changed", { detail: { ...state } }));
      closeLoginModal(true);
    } catch (error) {
      status.textContent = error.message || "Login failed.";
    } finally {
      submitButton.disabled = false;
    }
  }

  function closeLoginModal(result) {
    if (loginModal) {
      loginModal.classList.remove("open");
      loginModal.setAttribute("aria-hidden", "true");
    }
    if (resolveLoginPromise) {
      resolveLoginPromise(Boolean(result));
    }
    loginPromise = null;
    resolveLoginPromise = null;
  }

  document.addEventListener("click", (event) => {
    if (!widget || widget.contains(event.target)) {
      return;
    }
    const menu = widget.querySelector(".auth-menu");
    const avatarButton = widget.querySelector(".auth-avatar-button");
    if (menu && !menu.hasAttribute("hidden")) {
      menu.setAttribute("hidden", "");
      menu.classList.remove("open");
      avatarButton?.setAttribute("aria-expanded", "false");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    closeLoginModal(false);
    const menu = widget?.querySelector(".auth-menu");
    const avatarButton = widget?.querySelector(".auth-avatar-button");
    if (menu && !menu.hasAttribute("hidden")) {
      menu.setAttribute("hidden", "");
      menu.classList.remove("open");
      avatarButton?.setAttribute("aria-expanded", "false");
    }
  });

  function getInitials(value) {
    const parts = String(value || "AU")
      .replace(/[^a-zA-Z0-9 ]/g, " ")
      .split(/\s+/)
      .filter(Boolean);
    if (!parts.length) {
      return "AU";
    }
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
