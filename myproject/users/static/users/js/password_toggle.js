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

  const wrapper = document.createElement("div");
  wrapper.className = "password-toggle-wrap";

  const parent = input.parentElement;
  if (!parent) {
    return;
  }

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
  const inputs = document.querySelectorAll('input[type="password"]');
  inputs.forEach((input) => attachPasswordToggle(input));
}

document.addEventListener("DOMContentLoaded", initPasswordToggles);
