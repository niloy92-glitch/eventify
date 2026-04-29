function setActiveRole(authShell, role) {
  const roleInput = authShell.querySelector("#auth-role");
  const roleButtons = authShell.querySelectorAll(".auth-tab[data-role]");
  const rolePanels = authShell.querySelectorAll(".auth-role-panel[data-panel-role]");
  const roleLink = authShell.querySelector("#auth-role-link");
  const googleButtons = authShell.querySelectorAll("[data-google-auth]");
  const mode = authShell.dataset.authMode;
  const loginPageUrl = authShell.dataset.loginPageUrl || "/users/login/";
  const registerPageUrl = authShell.dataset.registerPageUrl || "/users/register/";
  const googleStartUrl = authShell.dataset.googleStartUrl || "/users/auth/google/start/";

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
      roleLink.href = `${registerPageUrl}?role=${encodeURIComponent(role)}`;
      const copyMap = {
        client: "Don't have an account? Register Now!",
        vendor: "Join as a vendor",
        admin: "Become an admin",
      };
      roleLink.textContent = copyMap[role] || copyMap.client;
    } else {
      roleLink.href = `${loginPageUrl}?role=${encodeURIComponent(role)}`;
      const copyMap = {
        client: "Already have a client account? Sign in now!",
        vendor: "Already have a vendor account? Sign in now!",
        admin: "Already have an admin account? Sign in now!",
      };
      roleLink.textContent = copyMap[role] || copyMap.client;
    }
  }

  googleButtons.forEach((button) => {
    button.onclick = () => {
      window.location.href = `${googleStartUrl}?mode=${encodeURIComponent(mode)}&role=${encodeURIComponent(role)}`;
    };
  });

  const nextUrl = new URL(window.location.href);
  nextUrl.searchParams.set("role", role);
  window.history.replaceState({}, "", nextUrl.toString());
}

function eyeOpenIcon() {
  return `
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
      <path d="M1.5 12S5 5.5 12 5.5 22.5 12 22.5 12 19 18.5 12 18.5 1.5 12 1.5 12Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/>
    </svg>
  `;
}

function eyeOffIcon() {
  return `
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
      <path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
      <path d="M10.6 6A10.3 10.3 0 0 1 12 5.5C19 5.5 22.5 12 22.5 12a19.1 19.1 0 0 1-3.2 4.2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M8.2 8.2A4.2 4.2 0 0 0 7.8 12a4.2 4.2 0 0 0 4.2 4.2c1 0 2-.3 2.8-1" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M6.2 6.2A18.6 18.6 0 0 0 1.5 12S5 18.5 12 18.5c1.7 0 3.2-.4 4.5-1" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
}

function attachPasswordToggle(input) {
  if (!input || input.type !== "password") {
    return;
  }

  if (input.parentElement && input.parentElement.classList.contains("password-toggle-wrap")) {
    return;
  }

  const parent = input.parentElement;
  if (!parent) {
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "password-toggle-wrap";

  parent.insertBefore(wrapper, input);
  wrapper.appendChild(input);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "password-toggle-btn";
  button.innerHTML = eyeOpenIcon();
  button.setAttribute("aria-label", "Show password");
  button.setAttribute("title", "Show password");

  button.addEventListener("click", () => {
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    button.innerHTML = isPassword ? eyeOffIcon() : eyeOpenIcon();
    button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    button.setAttribute("title", isPassword ? "Hide password" : "Show password");
  });

  wrapper.appendChild(button);
}

function initPasswordToggles() {
  document.querySelectorAll('input[type="password"]').forEach((input) => attachPasswordToggle(input));
}

function initAuthPage() {
  const authShell = document.querySelector(".auth-shell[data-auth-mode]");
  if (!authShell) {
    return;
  }

  const form = authShell.querySelector("#auth-form");
  const roleButtons = authShell.querySelectorAll(".auth-tab[data-role]");
  const selectedRole = authShell.dataset.activeRole || "client";

  setActiveRole(authShell, selectedRole);

  if (window.EventifyToast) {
    window.EventifyToast.fromQuery();
  }

  roleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const role = button.dataset.role;
      if (!role) {
        return;
      }
      setActiveRole(authShell, role);
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  initAuthPage();
  initPasswordToggles();
});
