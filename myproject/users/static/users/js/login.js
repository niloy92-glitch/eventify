async function loginRequest(email, password, remember, csrfToken) {
  const response = await fetch("/users/api/login/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    credentials: "same-origin",
    body: JSON.stringify({ email, password, remember }),
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

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const emailInput = document.getElementById("client-email");
    const passwordInput = document.getElementById("client-password");
    const rememberInput = document.getElementById("client-remember");
    const status = form.querySelector(".status-text");
    const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');

    if (!emailInput || !passwordInput || !status || !csrfInput) {
      return;
    }

    status.textContent = "Signing in...";

    try {
      const { data } = await loginRequest(
        emailInput.value.trim(),
        passwordInput.value,
        !!(rememberInput && rememberInput.checked),
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
