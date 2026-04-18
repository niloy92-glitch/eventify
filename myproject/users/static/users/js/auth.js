async function submitAuthRequest(url, payload, csrfToken) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = { ok: false, message: "Unexpected server response." };
  }

  return { response, data };
}

function setActiveRole(authShell, role) {
  const form = authShell.querySelector("#auth-form");
  const roleInput = authShell.querySelector("#auth-role");
  const roleButtons = authShell.querySelectorAll(".auth-tab[data-role]");
  const rolePanels = authShell.querySelectorAll(".auth-role-panel[data-panel-role]");
  const roleLink = authShell.querySelector("#auth-role-link");
  const mode = authShell.dataset.authMode;
  const loginBase = form ? form.dataset.loginUrl : "/users/api/login/";
  const registerBase = form ? form.dataset.registerUrl : "/users/api/register/";

  if (!role || !roleInput) {
    return;
  }

  roleInput.value = role;

  roleButtons.forEach((button) => {
    const isActive = button.dataset.role === role;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });

  rolePanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panelRole === role);
  });

  if (roleLink) {
    if (mode === "login") {
      roleLink.href = `/users/register/?role=${encodeURIComponent(role)}`;
      const copyMap = {
        client: "Don't have an account? Register Now!",
        vendor: "Join as a vendor",
        admin: "Become an admin",
      };
      roleLink.textContent = copyMap[role] || copyMap.client;
    } else {
      roleLink.href = `/users/login/?role=${encodeURIComponent(role)}`;
      const copyMap = {
        client: "Already have a client account? Sign in now!",
        vendor: "Already have a vendor account? Sign in now!",
        admin: "Already have an admin account? Sign in now!",
      };
      roleLink.textContent = copyMap[role] || copyMap.client;
    }
  }

  const nextUrl = new URL(window.location.href);
  nextUrl.searchParams.set("role", role);
  window.history.replaceState({}, "", nextUrl.toString());

  return { loginBase, registerBase };
}

function collectRegisterPayload(authShell, role) {
  const payload = { role };

  if (role === "client") {
    payload.first_name = authShell.querySelector("#client-first-name")?.value.trim() || "";
    payload.last_name = authShell.querySelector("#client-last-name")?.value.trim() || "";
    payload.email = authShell.querySelector("#client-email")?.value.trim() || "";
    payload.password = authShell.querySelector("#client-password")?.value || "";
    payload.confirm_password = authShell.querySelector("#client-confirm-password")?.value || "";
    return payload;
  }

  if (role === "vendor") {
    payload.company_name = authShell.querySelector("#vendor-company-name")?.value.trim() || "";
    payload.email = authShell.querySelector("#vendor-email")?.value.trim() || "";
    payload.password = authShell.querySelector("#vendor-password")?.value || "";
    payload.confirm_password = authShell.querySelector("#vendor-confirm-password")?.value || "";
    return payload;
  }

  payload.first_name = authShell.querySelector("#admin-first-name")?.value.trim() || "";
  payload.last_name = authShell.querySelector("#admin-last-name")?.value.trim() || "";
  payload.email = authShell.querySelector("#admin-email")?.value.trim() || "";
  payload.password = authShell.querySelector("#admin-password")?.value || "";
  payload.confirm_password = authShell.querySelector("#admin-confirm-password")?.value || "";
  payload.referral_code = authShell.querySelector("#admin-referral-code")?.value.trim() || "";
  return payload;
}

function initAuthPage() {
  const authShell = document.querySelector(".auth-shell[data-auth-mode]");
  if (!authShell) {
    return;
  }

  const form = authShell.querySelector("#auth-form");
  const roleButtons = authShell.querySelectorAll(".auth-tab[data-role]");
  const mode = authShell.dataset.authMode;
  const selectedRole = authShell.dataset.activeRole || "client";
  const status = authShell.querySelector(".status-text");
  const csrfInput = form ? form.querySelector('input[name="csrfmiddlewaretoken"]') : null;

  setActiveRole(authShell, selectedRole);

  roleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const role = button.dataset.role;
      if (!role) {
        return;
      }
      setActiveRole(authShell, role);
    });
  });

  if (!form || !status || !csrfInput) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const role = authShell.querySelector("#auth-role")?.value || "client";
    const endpoints = {
      login: form.dataset.loginUrl,
      register: form.dataset.registerUrl,
    };

    status.textContent = mode === "register" ? "Creating account..." : "Signing in...";
    status.style.color = "var(--teal)";

    try {
      let payload;
      if (mode === "register") {
        payload = collectRegisterPayload(authShell, role);
      } else {
        payload = {
          role,
          email: authShell.querySelector("#auth-email")?.value.trim() || "",
          password: authShell.querySelector("#auth-password")?.value || "",
          remember: !!authShell.querySelector("#auth-remember")?.checked,
        };
      }

      const endpoint = endpoints[mode];
      if (!endpoint) {
        status.textContent = "Authentication endpoint unavailable.";
        status.style.color = "var(--red)";
        return;
      }

      const { data } = await submitAuthRequest(endpoint, payload, csrfInput.value);

      if (!data.ok) {
        status.textContent = data.message || "Request failed.";
        status.style.color = "var(--red)";
        return;
      }

      status.textContent = data.message || "Success. Redirecting...";
      status.style.color = "var(--teal)";
      window.location.href = data.redirect_url || "/";
    } catch (error) {
      status.textContent = "Could not connect to server.";
      status.style.color = "var(--red)";
    }
  });
}

document.addEventListener("DOMContentLoaded", initAuthPage);
