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

document.addEventListener("DOMContentLoaded", initAuthPage);
