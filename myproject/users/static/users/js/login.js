async function loginRequest(email, password, remember, role, csrfToken) {
  const response = await fetch("/users/api/login/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    credentials: "same-origin",
    body: JSON.stringify({ email, password, remember, role }),
  });

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = { ok: false, message: "Unexpected server response." };
  }

  return { response, data };
}

function initLoginForms() {
  const form = document.getElementById("login-form");
  if (!form) return;

  const tabButtons = form.querySelectorAll(".auth-tab[data-role]");
  const roleInput = document.getElementById("login-role");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const selectedRole = button.getAttribute("data-role");
      if (!selectedRole || !roleInput) {
        return;
      }

      roleInput.value = selectedRole;
      tabButtons.forEach((tab) => {
        const isActive = tab === button;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
      });
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const emailInput = document.getElementById("client-email");
    const passwordInput = document.getElementById("client-password");
    const rememberInput = document.getElementById("client-remember");
    const status = form.querySelector(".status-text");
    const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
    const loginRoleInput = document.getElementById("login-role");

    if (!emailInput || !passwordInput || !status || !csrfInput || !loginRoleInput) {
      return;
    }

    status.textContent = "Signing in...";

    try {
      const { data } = await loginRequest(
        emailInput.value.trim(),
        passwordInput.value,
        !!(rememberInput && rememberInput.checked),
        loginRoleInput.value,
        csrfInput.value,
      );

      if (!data.ok) {
        status.textContent = data.message || "Login failed.";
        status.style.color = "var(--red)";
        return;
      }

      status.textContent = "Login successful. Redirecting...";
      status.style.color = "var(--teal)";
      window.location.href = data.redirect_url || "/";
    } catch (error) {
      status.textContent = "Could not connect to server.";
      status.style.color = "var(--red)";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginForms();
});
